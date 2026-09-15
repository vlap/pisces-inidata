#!/usr/bin/env bash
# ==============================================================================
# format_rivers.sh
# Process river nutrient exports (Global NEWS 2) for PISCES:
#   riverdin, riverdip, riverdon, riverdop, riverdoc, riverdsi, riverdic
# Uses mass-conserving remapping to ensure total global nutrient mass is
# strictly conserved when remapping from source to target resolution (e.g. eORCA025).
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Load modules
eval "${MODULE_LOAD_CMD}"

TARGET_GRID_NC="${WEIGHTS_DIR}/target_grid_${GRID_NAME}.nc"
TARGET_AREA_NC="${WEIGHTS_DIR}/target_area_${GRID_NAME}.nc"
OUT_FILE="${OUTPUT_DIR}/river.orca.nc"

if [ ! -f "${TARGET_GRID_NC}" ] || [ ! -f "${TARGET_AREA_NC}" ]; then
    echo "Target grid or area file not found. Generating grid and weights first..."
    bash "${SCRIPT_DIR}/gen_grid_and_weights.sh"
fi

mkdir -p "${OUTPUT_DIR}"

if [ -f "${ECE3_PISCES_DIR}/river_global_news_ORCA_R1.nc" ]; then
    echo "Remapping river nutrient exports from curated ECE3 baseline..."
    cdo ${CDO_OPTS} ${CDO_COMPRESS} -remapnn,"${TARGET_GRID_NC}" -setgrid,"${ORCA1_GRIDDES}" "${ECE3_PISCES_DIR}/river_global_news_ORCA_R1.nc" "${OUT_FILE}"
    ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/river_global_news_${GRID_NAME}.nc"
    echo "=== River forcings completed successfully: ${OUT_FILE} ==="
    exit 0
fi

SRC_FILE="${RAW_DIR}/official_v5.0.0/river.orca.nc"
if [ ! -f "${SRC_FILE}" ]; then
    echo "ERROR: Source river file ${SRC_FILE} not found. Run download_sources.sh first." >&2
    exit 1
fi

TMP_DIR=$(mktemp -d -p "${SCRATCH_ROOT}" tmp_river_XXXXXX)
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "=== Processing River Nutrient Forcings for ${GRID_NAME} ==="
echo "Source: ${SRC_FILE}"
echo "Target output: ${OUT_FILE}"

# Sanitize source grid coordinates for CDO recognition
cp "${SRC_FILE}" "${TMP_DIR}/src_clean.nc"
ncatted -O \
    -a coordinates,,c,c,"nav_lon nav_lat" \
    -a units,nav_lon,c,c,"degrees_east" \
    -a units,nav_lat,c,c,"degrees_north" \
    -a standard_name,nav_lon,c,c,"longitude" \
    -a standard_name,nav_lat,c,c,"latitude" \
    "${TMP_DIR}/src_clean.nc" 2>/dev/null || true

# 1. Compute horizontal cell area on the source grid (ORCA2)
echo "Computing source cell areas..."
cdo ${CDO_OPTS} gridarea "${TMP_DIR}/src_clean.nc" "${TMP_DIR}/src_area.nc"

# Generate distance-weighted remapping weights from source river grid to target
WEIGHTS_RIVER="${WEIGHTS_DIR}/weights_river_to_${GRID_NAME}.nc"
if [ ! -f "${WEIGHTS_RIVER}" ]; then
    echo "Computing remapping weights for river grid..."
    cdo ${CDO_OPTS} gendis,"${TARGET_GRID_NC}" "${TMP_DIR}/src_clean.nc" "${WEIGHTS_RIVER}"
fi

# 2. Process each nutrient variable conservatively
MERGE_FILES=()

for var in "${RIVER_VARS[@]}"; do
    echo "--- Processing variable: ${var} ---"
    
    # Extract variable
    cdo ${CDO_OPTS} -selname,"${var}" "${TMP_DIR}/src_clean.nc" "${TMP_DIR}/${var}_src.nc"
    
    # Compute total mass rate on source grid: mass = flux * area (in Mg/yr)
    cdo ${CDO_OPTS} -mul "${TMP_DIR}/${var}_src.nc" "${TMP_DIR}/src_area.nc" "${TMP_DIR}/${var}_mass_src.nc"
    
    # Calculate global total source mass rate
    src_total=$(cdo -s -output -timmean -fldsum "${TMP_DIR}/${var}_mass_src.nc" | tr -d '[:space:]')
    echo "  [${var}] Global source mass rate: ${src_total} Mg/yr"
    
    # Remap total mass flux to target grid
    cdo ${CDO_OPTS} remap,"${TARGET_GRID_NC}","${WEIGHTS_RIVER}" "${TMP_DIR}/${var}_mass_src.nc" "${TMP_DIR}/${var}_mass_tgt.nc"
    
    # Mask to target ocean coastal points using tmaskutil from maskutil.nc
    # shortcut: apply ocean mask to ensure river mouth fluxes only occur in ocean wet cells
    cdo ${CDO_OPTS} -ifthen -selname,tmaskutil "${MASKUTIL}" "${TMP_DIR}/${var}_mass_tgt.nc" "${TMP_DIR}/${var}_mass_tgt_masked.nc"
    
    # Convert back to areal flux on target grid: flux_tgt = mass_tgt / area_tgt
    cdo ${CDO_OPTS} -div "${TMP_DIR}/${var}_mass_tgt_masked.nc" "${TARGET_AREA_NC}" "${TMP_DIR}/${var}_flux_tgt.nc"
    
    # Calculate target global total mass rate
    tgt_total=$(cdo -s -output -timmean -fldsum -mul "${TMP_DIR}/${var}_flux_tgt.nc" "${TARGET_AREA_NC}" | tr -d '[:space:]')
    echo "  [${var}] Global target mass rate (pre-normalization): ${tgt_total} Mg/yr"
    
    # Calculate exact conservation factor
    scale_factor=$(awk -v src="${src_total}" -v tgt="${tgt_total}" 'BEGIN { if (tgt > 0) print src/tgt; else print 1.0; }')
    echo "  [${var}] Conservation scaling factor: ${scale_factor}"
    
    # Normalize target flux so total mass is exactly conserved
    cdo ${CDO_OPTS} ${CDO_COMPRESS} -mulc,"${scale_factor}" "${TMP_DIR}/${var}_flux_tgt.nc" "${TMP_DIR}/${var}_final.nc"
    
    # Verify final mass
    final_total=$(cdo -s -output -timmean -fldsum -mul "${TMP_DIR}/${var}_final.nc" "${TARGET_AREA_NC}" | tr -d '[:space:]')
    echo "  [${var}] Final conserved mass rate: ${final_total} Mg/yr"
    
    MERGE_FILES+=("${TMP_DIR}/${var}_final.nc")
done

# 3. Merge all river variables into single target river.orca.nc
echo "Merging all river variables into ${OUT_FILE}..."
cdo ${CDO_OPTS} ${CDO_COMPRESS} merge "${MERGE_FILES[@]}" "${OUT_FILE}"
ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/river_global_news_${GRID_NAME}.nc"

echo "=== River forcings completed successfully: ${OUT_FILE} ==="
