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

SRC_FILE="${RAW_DIR}/official_v5.0.0/river.orca.nc"
if [ "${GRID_NAME}" = "ORCA2" ] && [ -f "${SRC_FILE}" ]; then
    echo "Copying native ORCA2 SETTE river nutrient forcing..."
    cp "${SRC_FILE}" "${OUT_FILE}"
    ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/river_global_news_${GRID_NAME}.nc"
    stamp_provenance "${OUT_FILE}"
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
if [ -f "${RAW_DIR}/official_v5.0.0/bathy.orca.nc" ]; then
    ncks -A -v nav_lon,nav_lat "${RAW_DIR}/official_v5.0.0/bathy.orca.nc" "${TMP_DIR}/src_clean.nc"
elif [ -f "${RAW_DIR}/official_v5.0.0/dust.orca.nc" ]; then
    ncks -A -v nav_lon,nav_lat "${RAW_DIR}/official_v5.0.0/dust.orca.nc" "${TMP_DIR}/src_clean.nc"
fi

ncatted -O \
    -a coordinates,,c,c,"nav_lon nav_lat" \
    -a units,nav_lon,c,c,"degrees_east" \
    -a units,nav_lat,c,c,"degrees_north" \
    -a standard_name,nav_lon,c,c,"longitude" \
    -a standard_name,nav_lat,c,c,"latitude" \
    "${TMP_DIR}/src_clean.nc" 2>/dev/null || true

echo "Remapping river nutrient fluxes to ${GRID_NAME}..."
cdo ${CDO_OPTS} ${CDO_COMPRESS} remapdis,"${TARGET_GRID_NC}" "${TMP_DIR}/src_clean.nc" "${OUT_FILE}"

if [ -f "${MASKUTIL}" ]; then
    echo "Applying ocean mask to river mouth fluxes..."
    cdo ${CDO_OPTS} ${CDO_COMPRESS} -ifthen -selname,tmaskutil "${MASKUTIL}" "${OUT_FILE}" "${TMP_DIR}/masked.nc"
    mv "${TMP_DIR}/masked.nc" "${OUT_FILE}"
fi

ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/river_global_news_${GRID_NAME}.nc"
stamp_provenance "${OUT_FILE}"

echo "=== River forcings completed successfully: ${OUT_FILE} ==="

