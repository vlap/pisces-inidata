#!/usr/bin/env bash
# ==============================================================================
# remap_field.sh
# Stage 2 (Target-Centric Remapping): Universal, format-agnostic interpolation
# driver mapping standardized regular source files to target NEMO grid.
#
# Takes clean NetCDF from ${STANDARDIZED_DIR}/std_<VAR>.nc and executes:
#   - 3D: Vertical level interpolation (cdo intlevel) + Horizontal remapping (cdo remap)
#   - 2D: Horizontal remapping (cdo remap)
#   - Bathy: Nearest-neighbor remapping (cdo remapnn)
#   - Rivers: Conservative remapping (cdo remapcon)
#
# This script has ZERO dataset-specific branching (e.g. no WOA vs GLODAP logic).
# It operates strictly on standardized NetCDF files.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Load modules
eval "${MODULE_LOAD_CMD}"

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <VAR_NAME|all> [TYPE: auto|3d|2d|bathy|hydrofe|river]"
    exit 1
fi

VAR="$1"
FIELD_TYPE="${2:-auto}"

if [ "${VAR}" = "all" ]; then
    for t in "${TRACERS_3D[@]}"; do
        bash "${SCRIPT_DIR}/remap_field.sh" "${t}" 3d
    done
    for f in dust ndep par; do
        bash "${SCRIPT_DIR}/remap_field.sh" "${f}" 2d
    done
    bash "${SCRIPT_DIR}/remap_field.sh" bathy bathy
    bash "${SCRIPT_DIR}/remap_field.sh" hydrofe hydrofe
    bash "${SCRIPT_DIR}/remap_field.sh" river river
    echo "=== All fields remapped successfully to ${GRID_NAME}! ==="
    exit 0
fi

if [ "${FIELD_TYPE}" = "auto" ]; then
    case "${VAR}" in
        NO3|PO4|Si|O2|TALK|TDIC|PiDIC|DOC|Fer) FIELD_TYPE="3d" ;;
        dust|ndep|par) FIELD_TYPE="2d" ;;
        bathy) FIELD_TYPE="bathy" ;;
        hydrofe) FIELD_TYPE="hydrofe" ;;
        river|rivers) FIELD_TYPE="river" ;;
        *) FIELD_TYPE="3d" ;;
    esac
fi

TARGET_GRID_NC="${WEIGHTS_DIR}/target_grid_${GRID_NAME}.nc"
WEIGHTS_BILIN="${WEIGHTS_DIR}/weights_r360x180_to_${GRID_NAME}_bilin.nc"

mkdir -p "${OUTPUT_DIR}" "${WEIGHTS_DIR}" "${LOG_DIR}"

if [ ! -f "${TARGET_GRID_NC}" ] || ([ ! -f "${WEIGHTS_BILIN}" ] && [ "${FIELD_TYPE}" != "bathy" ]); then
    echo "Target grid or weights not found. Generating grid and weights first..."
    bash "${SCRIPT_DIR}/gen_grid_and_weights.sh"
fi

STD_FILE="${STANDARDIZED_DIR}/std_${VAR}.nc"
if [ ! -f "${STD_FILE}" ]; then
    echo "Standardized source file not found: ${STD_FILE}. Invoking Stage 1 preparation..."
    bash "${SCRIPT_DIR}/prepare_standard_sources.sh" "${VAR}"
fi

TMP_DIR=$(mktemp -d -p "${TMP_BASE}" tmp_remap_${VAR}_XXXXXX)
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "========================================================================"
echo " Stage 2 [Remap]: Mapping ${VAR} (${FIELD_TYPE}) to ${GRID_NAME}"
echo " Standard Source: ${STD_FILE}"
echo " Target Grid:     ${GRID_NAME}"
echo "========================================================================"

# ------------------------------------------------------------------------------
# 1. 3D Tracers Remapping
# ------------------------------------------------------------------------------
remap_3d_tracer() {
    eval "$(pisces-inidata resolve-target "${VAR}" --grid "${GRID_NAME}" --export)"
    local out_file="${OUTPUT_DIR}/${OUT_FILE}"

    # Extract target vertical levels from domain_cfg (e.g. L75) or catalog fallback
    local target_levels=""
    if [ -f "${DOMAIN_CFG}" ]; then
        target_levels=$(ncks -s '%f,' -H -C -v nav_lev "${DOMAIN_CFG}" 2>/dev/null | sed 's/,$//')
    fi
    if [ -z "${target_levels:-}" ]; then
        target_levels=$(pisces-inidata get-vertical-levels --grid "${GRID_NAME}" --raw-dir "${RAW_DIR}" 2>/dev/null || true)
    fi

    if [ -n "${target_levels:-}" ]; then
        echo "[Step 1/2] Vertical level interpolation to target levels on source grid..."
        cdo ${CDO_OPTS} -intlevel,"${target_levels}" "${STD_FILE}" "${TMP_DIR}/vint.nc"
        echo "[Step 2/2] Horizontal remapping to ${GRID_NAME}..."
        cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/vint.nc" "${out_file}"
    else
        echo "[Step 1/1] Horizontal remapping to ${GRID_NAME}..."
        cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${STD_FILE}" "${out_file}"
    fi

    # Standard target symlinks from catalog
    for s in ${TARGET_SYMLINKS}; do
        ln -sfn "$(basename "${out_file}")" "${OUTPUT_DIR}/${s}"
    done

    stamp_provenance "${out_file}"
    echo "Created 3D tracer: ${out_file}"
}

# ------------------------------------------------------------------------------
# 2. 2D Surface Forcings Remapping (Dust, N-dep, PAR)
# ------------------------------------------------------------------------------
remap_2d_forcing() {
    eval "$(pisces-inidata resolve-target "${VAR}" --grid "${GRID_NAME}" --export)"
    local out_file="${OUTPUT_DIR}/${OUT_FILE}"

    local weights_file="${WEIGHTS_DIR}/weights_${VAR}_to_${GRID_NAME}.nc"
    if [ ! -f "${weights_file}" ]; then
        cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${STD_FILE}" "${weights_file}"
    fi
    echo "Remapping ${VAR} to ${GRID_NAME}..."
    cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${weights_file}" "${STD_FILE}" "${out_file}"

    for s in ${TARGET_SYMLINKS}; do
        ln -sfn "$(basename "${out_file}")" "${OUTPUT_DIR}/${s}"
    done
    stamp_provenance "${out_file}"
    echo "Created 2D forcing: ${out_file}"
}

# ------------------------------------------------------------------------------
# 3. Bathymetric Shelf Fraction Remapping (Nearest-Neighbor)
# ------------------------------------------------------------------------------
remap_bathy() {
    eval "$(pisces-inidata resolve-target "bathy" --grid "${GRID_NAME}" --export)"
    local out_file="${OUTPUT_DIR}/${OUT_FILE}"
    echo "Remapping bathy shelf fraction to ${GRID_NAME} using nearest-neighbor..."
    cdo ${CDO_OPTS} ${CDO_COMPRESS} remapnn,"${TARGET_GRID_NC}" "${STD_FILE}" "${out_file}"
    for s in ${TARGET_SYMLINKS}; do
        ln -sfn "$(basename "${out_file}")" "${OUTPUT_DIR}/${s}"
    done
    stamp_provenance "${out_file}"
    echo "Created bathy: ${out_file}"
}

# ------------------------------------------------------------------------------
# 4. Hydrothermal Iron Remapping
# ------------------------------------------------------------------------------
remap_hydrofe() {
    eval "$(pisces-inidata resolve-target "hydrofe" --grid "${GRID_NAME}" --export)"
    local out_file="${OUTPUT_DIR}/${OUT_FILE}"
    echo "Remapping hydrothermal vent Fe to ${GRID_NAME}..."
    cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${STD_FILE}" "${out_file}"
    for s in ${TARGET_SYMLINKS}; do
        ln -sfn "$(basename "${out_file}")" "${OUTPUT_DIR}/${s}"
    done
    stamp_provenance "${out_file}"
    echo "Created hydrofe: ${out_file}"
}

# ------------------------------------------------------------------------------
# 5. River Nutrient Forcings Remapping (Conservative)
# ------------------------------------------------------------------------------
remap_river() {
    eval "$(pisces-inidata resolve-target "rivers" --grid "${GRID_NAME}" --export)"
    local out_file="${OUTPUT_DIR}/${OUT_FILE}"
    echo "Remapping river nutrient discharge to ${GRID_NAME}..."
    cdo ${CDO_OPTS} ${CDO_COMPRESS} remapdis,"${TARGET_GRID_NC}" "${STD_FILE}" "${out_file}"
    for s in ${TARGET_SYMLINKS}; do
        ln -sfn "$(basename "${out_file}")" "${OUTPUT_DIR}/${s}"
    done
    stamp_provenance "${out_file}"
    echo "Created river: ${out_file}"
}

# ------------------------------------------------------------------------------
# Dispatcher
# ------------------------------------------------------------------------------
case "${FIELD_TYPE}" in
    3d)       remap_3d_tracer ;;
    2d)       remap_2d_forcing ;;
    bathy)    remap_bathy ;;
    hydrofe)  remap_hydrofe ;;
    river|rivers) remap_river ;;
    *)
        echo "ERROR: Unknown field type: ${FIELD_TYPE} (Choose: 3d | 2d | bathy | hydrofe | river)" >&2
        exit 1
        ;;
esac

echo "=== Stage 2 Remapping completed successfully for ${VAR}! ==="
