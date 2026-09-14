#!/usr/bin/env bash
# ==============================================================================
# format_tracers_3d.sh
# Process and interpolate 3D biogeochemical tracers for PISCES:
#   NO3, PO4, Si, O2, TALK, TDIC, PiDIC, DOC, Fer
# Supports:
#   1) Offline remapping directly to target curvilinear grid (${GRID_NAME})
#   2) Online mode preparation (regular unmasked nomask files + SCRIP weights)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Load modules
eval "${MODULE_LOAD_CMD}"

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <TRACER_VAR> [MODE: offline|online]"
    echo "Tracer options: ${TRACERS_3D[*]}"
    exit 1
fi

VAR="$1"
MODE="${2:-offline}" # default is offline remapping to target grid

# Verify source file
SRC_BASELINE_DIR="${RAW_DIR}/official_v5.0.0"
SRC_FILE=""

case "${VAR}" in
    TALK)
        SRC_FILE="${SRC_BASELINE_DIR}/data_ALK_nomask.nc"
        INTERNAL_VAR="TALK"
        ;;
    TDIC)
        SRC_FILE="${SRC_BASELINE_DIR}/data_DIC_nomask.nc"
        INTERNAL_VAR="TDIC"
        ;;
    PiDIC)
        SRC_FILE="${SRC_BASELINE_DIR}/data_DIC_nomask.nc"
        INTERNAL_VAR="PiDIC"
        ;;
    NO3|PO4|SIL|Si|OXY|O2|DOC|FER|Fer)
        # Normalize naming
        case "${VAR}" in
            SIL|Si) FILE_VAR="SIL"; INTERNAL_VAR="Si" ;;
            OXY|O2) FILE_VAR="OXY"; INTERNAL_VAR="O2" ;;
            FER|Fer) FILE_VAR="FER"; INTERNAL_VAR="Fer" ;;
            *) FILE_VAR="${VAR}"; INTERNAL_VAR="${VAR}" ;;
        esac
        SRC_FILE="${SRC_BASELINE_DIR}/data_${FILE_VAR}_nomask.nc"
        ;;
    *)
        echo "ERROR: Unknown tracer variable: ${VAR}" >&2
        exit 1
        ;;
esac

if [ ! -f "${SRC_FILE}" ]; then
    echo "ERROR: Source file ${SRC_FILE} not found." >&2
    echo "Please run ./download_sources.sh first." >&2
    exit 1
fi

TARGET_GRID_NC="${WEIGHTS_DIR}/target_grid_${GRID_NAME}.nc"
WEIGHTS_BILIN="${WEIGHTS_DIR}/weights_r360x180_to_${GRID_NAME}_bilin.nc"

mkdir -p "${OUTPUT_DIR}"

if [ "${MODE}" = "offline" ]; then
    OUT_FILE="${OUTPUT_DIR}/data_${INTERNAL_VAR}_${GRID_NAME}.nc"
    echo "=== Processing 3D tracer: ${INTERNAL_VAR} (Offline Remap to ${GRID_NAME}) ==="
    echo "Source file: ${SRC_FILE}"
    echo "Target output: ${OUT_FILE}"

    if [ ! -f "${WEIGHTS_BILIN}" ]; then
        echo "Weights not found. Generating grid and weights first..."
        bash "${SCRIPT_DIR}/gen_grid_and_weights.sh"
    fi

    TMP_DIR=$(mktemp -d -p "${SCRATCH_ROOT}" tmp_tracer_${VAR}_XXXXXX)
    trap 'rm -rf "${TMP_DIR}"' EXIT

    # Extract target variable if multiple exist in file
    cdo ${CDO_OPTS} -selname,"${INTERNAL_VAR}" "${SRC_FILE}" "${TMP_DIR}/src_sel.nc"

    # Extract target vertical levels from domain_cfg if 3D
    echo "Extracting target vertical levels from ${DOMAIN_CFG}..."
    TARGET_LEVELS=$(cdo -s showlevel -selname,nav_lev "${DOMAIN_CFG}" 2>/dev/null | tr -s ' ' ',' | sed 's/^,//;s/,$//' || true)

    # Remap horizontally to target grid using precomputed bilinear weights
    cdo ${CDO_OPTS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/src_sel.nc" "${TMP_DIR}/hremap.nc"

    # Vertical interpolation to target levels if levels exist and vertical dimension present
    if [ -n "${TARGET_LEVELS}" ]; then
        echo "Interpolating vertically to target ${GRID_NAME} depth levels..."
        cdo ${CDO_OPTS} ${CDO_COMPRESS} -intlevel,"${TARGET_LEVELS}" "${TMP_DIR}/hremap.nc" "${OUT_FILE}"
    else
        cdo ${CDO_OPTS} ${CDO_COMPRESS} copy "${TMP_DIR}/hremap.nc" "${OUT_FILE}"
    fi

    echo "Successfully generated: ${OUT_FILE}"

else
    # Online mode: stage unmasked regular grid file for runtime remapping
    OUT_FILE="${OUTPUT_DIR}/data_${FILE_VAR:-${VAR}}_nomask.nc"
    echo "=== Staging 3D tracer for online remapping: ${OUT_FILE} ==="
    cp -u "${SRC_FILE}" "${OUT_FILE}"
    echo "Ready with online weights: ${OUTPUT_DIR}/weights_3D_r360x180_bilin.nc"
fi
