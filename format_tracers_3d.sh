#!/usr/bin/env bash
# ==============================================================================
# format_tracers_3d.sh
# Process and interpolate 3D biogeochemical tracers for PISCES:
#   NO3, PO4, Si, O2, TALK, TDIC, PiDIC, DOC, Fer
# Supports:
#   1) modern:           WOA23 (NO3, PO4, Si, O2) & GLODAPv2 (TALK, TDIC, PiDIC)
#   2) official_regular: Official 1x1 regular unmasked NOMASK fields
#   3) ece3_baseline:    Direct remap from ECE3 baseline
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

TARGET_GRID_NC="${WEIGHTS_DIR}/target_grid_${GRID_NAME}.nc"
WEIGHTS_BILIN="${WEIGHTS_DIR}/weights_r360x180_to_${GRID_NAME}_bilin.nc"

mkdir -p "${OUTPUT_DIR}" "${WEIGHTS_DIR}" "${LOG_DIR}"

if [ ! -f "${WEIGHTS_BILIN}" ]; then
    echo "Weights not found. Generating grid and weights first..."
    bash "${SCRIPT_DIR}/gen_grid_and_weights.sh"
fi

# Extract target vertical levels from domain_cfg (L75 depths)
TARGET_LEVELS=$(ncks -s '%f,' -H -C -v nav_lev "${DOMAIN_CFG}" 2>/dev/null | sed 's/,$//')

TMP_DIR=$(mktemp -d -p "${SCRATCH_ROOT}" tmp_tracer_${VAR}_XXXXXX)
trap 'rm -rf "${TMP_DIR}"' EXIT

OUT_FILE="${OUTPUT_DIR}/data_${VAR}_${GRID_NAME}.nc"

echo "========================================================================"
echo " Processing 3D Tracer: ${VAR}"
echo " Source Mode:          ${SOURCE_MODE}"
echo " Target Grid:          ${GRID_NAME}"
echo " Output File:          ${OUT_FILE}"
echo "========================================================================"

if [ "${SOURCE_MODE}" = "modern" ]; then
    case "${VAR}" in
        NO3|PO4|Si|O2)
            case "${VAR}" in
                NO3) CODE="n" ;;
                PO4) CODE="p" ;;
                Si)  CODE="i" ;;
                O2)  CODE="o" ;;
            esac
            SRC_12M="${RAW_DIR}/woa23/woa23_12m_${CODE}.nc"
            if [ ! -f "${SRC_12M}" ]; then
                echo "Assembling WOA23 12-month profile for ${VAR}..."
                python3 "${SCRIPT_DIR}/prepare_woa23_tracer.py" "${CODE}" "${WOA23_DIR}" "${SRC_12M}"
            fi
            echo "[Step 1/3] Filling missing land values with cdo fillmiss..."
            cdo ${CDO_OPTS} fillmiss "${SRC_12M}" "${TMP_DIR}/filled.nc"

            echo "[Step 2/3] Horizontal remapping to ${GRID_NAME}..."
            cdo ${CDO_OPTS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/filled.nc" "${TMP_DIR}/hremap.nc"

            echo "[Step 3/3] Vertical interpolation to target L75 levels..."
            cdo ${CDO_OPTS} ${CDO_COMPRESS} -intlevel,"${TARGET_LEVELS}" "${TMP_DIR}/hremap.nc" "${OUT_FILE}"

            # Create symlink matching observational product
            ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/${VAR}_WOA23_monthly_${GRID_NAME}.nc"
            ;;

        TALK|TDIC|PiDIC)
            case "${VAR}" in
                TALK)
                    SRC_FILE="${GLODAP_V2_DIR}/GLODAPv2.2016b.TAlk.nc"
                    SRC_VAR="TAlk"
                    OUT_VAR_NAME="Alkalini"
                    LINK_NAME="Alkalini_GLODAP_annual_${GRID_NAME}.nc"
                    ;;
                TDIC)
                    SRC_FILE="${GLODAP_V2_DIR}/GLODAPv2.2016b.TCO2.nc"
                    SRC_VAR="TCO2"
                    OUT_VAR_NAME="DIC"
                    LINK_NAME="DIC_GLODAP_annual_${GRID_NAME}.nc"
                    ;;
                PiDIC)
                    SRC_FILE="${GLODAP_V2_DIR}/GLODAPv2.2016b.PI_TCO2.nc"
                    SRC_VAR="PI_TCO2"
                    OUT_VAR_NAME="DIC"
                    LINK_NAME="PiDIC_GLODAP_annual_${GRID_NAME}.nc"
                    ;;
            esac

            echo "[Step 1/4] Setting missing values to -999. and selecting ${SRC_VAR}..."
            cdo ${CDO_OPTS} setmissval,-999. -selname,"${SRC_VAR}" "${SRC_FILE}" "${TMP_DIR}/sel.nc"

            echo "[Step 2/4] Filling missing values with cdo fillmiss..."
            cdo ${CDO_OPTS} fillmiss "${TMP_DIR}/sel.nc" "${TMP_DIR}/filled.nc"

            echo "[Step 3/5] Horizontal remapping to ${GRID_NAME}..."
            cdo ${CDO_OPTS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/filled.nc" "${TMP_DIR}/hremap.nc"

            echo "[Step 4/5] Extending abyssal depth to 6000m..."
            python3 "${SCRIPT_DIR}/pad_abyssal_depth.py" "${TMP_DIR}/hremap.nc" "${TMP_DIR}/hremap_padded.nc" 6000.0

            echo "[Step 5/5] Vertical interpolation to target L75 levels..."
            cdo ${CDO_OPTS} ${CDO_COMPRESS} -intlevel,"${TARGET_LEVELS}" "${TMP_DIR}/hremap_padded.nc" "${OUT_FILE}"

            if [ "${SRC_VAR}" != "${OUT_VAR_NAME}" ]; then
                ncrename -O -v "${SRC_VAR},${OUT_VAR_NAME}" "${OUT_FILE}"
            fi

            ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/${LINK_NAME}"
            ;;

        DOC|Fer)
            case "${VAR}" in
                DOC) FILE_VAR="DOC"; LINK_NAME="DOC_PISCES_monthly_${GRID_NAME}.nc" ;;
                Fer) FILE_VAR="FER"; LINK_NAME="Fer_PISCES_monthly_${GRID_NAME}.nc" ;;
            esac
            SRC_FILE="${RAW_DIR}/official_v5.0.0/data_${FILE_VAR}_nomask.nc"

            echo "[Step 1/3] Horizontal remapping to ${GRID_NAME}..."
            cdo ${CDO_OPTS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" -selname,"${VAR}" "${SRC_FILE}" "${TMP_DIR}/hremap.nc"

            echo "[Step 2/3] Extending abyssal depth to 6000m..."
            python3 "${SCRIPT_DIR}/pad_abyssal_depth.py" "${TMP_DIR}/hremap.nc" "${TMP_DIR}/hremap_padded.nc" 6000.0

            echo "[Step 3/3] Vertical interpolation to target L75 levels..."
            cdo ${CDO_OPTS} ${CDO_COMPRESS} -intlevel,"${TARGET_LEVELS}" "${TMP_DIR}/hremap_padded.nc" "${OUT_FILE}"

            ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/${LINK_NAME}"
            ;;

        *)
            echo "ERROR: Unknown tracer variable: ${VAR}" >&2
            exit 1
            ;;
    esac

elif [ "${SOURCE_MODE}" = "official_regular" ]; then
    case "${VAR}" in
        TALK) FILE_VAR="ALK"; INTERNAL_VAR="TALK" ;;
        TDIC|PiDIC) FILE_VAR="DIC"; INTERNAL_VAR="${VAR}" ;;
        SIL|Si) FILE_VAR="SIL"; INTERNAL_VAR="Si" ;;
        OXY|O2) FILE_VAR="OXY"; INTERNAL_VAR="O2" ;;
        FER|Fer) FILE_VAR="FER"; INTERNAL_VAR="Fer" ;;
        *) FILE_VAR="${VAR}"; INTERNAL_VAR="${VAR}" ;;
    esac
    SRC_FILE="${RAW_DIR}/official_v5.0.0/data_${FILE_VAR}_nomask.nc"

    cdo ${CDO_OPTS} -selname,"${INTERNAL_VAR}" "${SRC_FILE}" "${TMP_DIR}/src_sel.nc"
    cdo ${CDO_OPTS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/src_sel.nc" "${TMP_DIR}/hremap.nc"
    python3 "${SCRIPT_DIR}/pad_abyssal_depth.py" "${TMP_DIR}/hremap.nc" "${TMP_DIR}/hremap_padded.nc" 6000.0
    cdo ${CDO_OPTS} ${CDO_COMPRESS} -intlevel,"${TARGET_LEVELS}" "${TMP_DIR}/hremap_padded.nc" "${OUT_FILE}"

elif [ "${SOURCE_MODE}" = "ece3_baseline" ]; then
    case "${VAR}" in
        NO3) BASE_NAME="data_NO3_orca1.nc" ;;
        PO4) BASE_NAME="data_PO4_orca1.nc" ;;
        Si)  BASE_NAME="data_SIL_orca1.nc" ;;
        O2)  BASE_NAME="data_OXY_orca1.nc" ;;
        TALK) BASE_NAME="data_ALK_orca1.nc" ;;
        TDIC) BASE_NAME="data_DIC_orca1.nc" ;;
        DOC) BASE_NAME="data_DOC_orca1.nc" ;;
        Fer) BASE_NAME="data_FER_orca1.nc" ;;
        *)   BASE_NAME="data_${VAR}_orca1.nc" ;;
    esac
    SRC_FILE="${ECE3_PISCES_DIR}/${BASE_NAME}"

    cdo ${CDO_OPTS} -setgrid,"${ORCA1_GRIDDES}" "${SRC_FILE}" "${TMP_DIR}/src_grid.nc"
    cdo ${CDO_OPTS} ${CDO_COMPRESS} -remapnn,"${TARGET_GRID_NC}" "${TMP_DIR}/src_grid.nc" "${OUT_FILE}"
fi

if [ "${SOURCE_MODE}" != "modern" ]; then
    case "${VAR}" in
        NO3|PO4|Si|O2) LINK_NAME="${VAR}_WOA2009_monthly_${GRID_NAME}.nc" ;;
        TALK) LINK_NAME="Alkalini_GLODAP_annual_${GRID_NAME}.nc" ;;
        TDIC) LINK_NAME="DIC_GLODAP_annual_${GRID_NAME}.nc" ;;
        PiDIC) LINK_NAME="PiDIC_GLODAP_annual_${GRID_NAME}.nc" ;;
        DOC) LINK_NAME="DOC_PISCES_monthly_${GRID_NAME}.nc" ;;
        Fer) LINK_NAME="Fer_PISCES_monthly_${GRID_NAME}.nc" ;;
        *) LINK_NAME="" ;;
    esac
    if [ -n "${LINK_NAME}" ]; then
        ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/${LINK_NAME}"
    fi
fi

echo "Successfully generated: ${OUT_FILE}"
