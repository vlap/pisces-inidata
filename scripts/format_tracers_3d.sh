#!/usr/bin/env bash
# ==============================================================================
# format_tracers_3d.sh
# Process and interpolate 3D biogeochemical tracers for PISCES:
#   NO3, PO4, Si, O2, TALK, TDIC, PiDIC, DOC, Fer
# Dynamic source selection driven by presets (ece4, ece3, sette) and sources.yaml
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

# Extract target vertical levels from domain_cfg (e.g. L75 depths) or official nomask (e.g. ORCA2 L31 depths)
TARGET_LEVELS=""
if [ -f "${DOMAIN_CFG}" ]; then
    TARGET_LEVELS=$(ncks -s '%f,' -H -C -v nav_lev "${DOMAIN_CFG}" 2>/dev/null | sed 's/,$//')
fi
if [ -z "${TARGET_LEVELS:-}" ] && [ -f "${RAW_DIR}/official_v5.0.0/data_DOC_nomask.nc" ]; then
    echo "Extracting ORCA2 vertical levels from official data_DOC_nomask.nc..."
    TARGET_LEVELS=$(cdo -s showlevel "${RAW_DIR}/official_v5.0.0/data_DOC_nomask.nc" 2>/dev/null | tr -s ' ' ',' | sed 's/^,//; s/,$//')
fi

TMP_DIR=$(mktemp -d -p "${SCRATCH_ROOT}" tmp_tracer_${VAR}_XXXXXX)
trap 'rm -rf "${TMP_DIR}"' EXIT

OUT_FILE="${OUTPUT_DIR}/data_${VAR}_${GRID_NAME}.nc"

echo "========================================================================"
echo " Processing 3D Tracer: ${VAR}"
echo " Active Preset:        ${INIDATA_PRESET:-custom}"
echo " Target Grid:          ${GRID_NAME}"
echo " Output File:          ${OUT_FILE}"
echo "========================================================================"

resolve_glodap_source() {
    local param="$1" # TAlk, TCO2, PI_TCO2
    local ver="${PRODUCT_TALK:-v2.2016b}"

    case "${ver}" in
        *2023*)
            candidate="${GLODAP_V2_2023_DIR}/GLODAPv2.2023.${param}.nc"
            if [ -f "${candidate}" ]; then echo "${candidate}"; return 0; fi
            ;;
        *v1*)
            candidate="${GLODAP_V1_DIR}/glodap_v1.${param}.nc"
            if [ -f "${candidate}" ]; then echo "${candidate}"; return 0; fi
            ;;
        *)
            candidate="${GLODAP_V2_DIR}/GLODAPv2.2016b.${param}.nc"
            if [ -f "${candidate}" ]; then echo "${candidate}"; return 0; fi
            candidate="${GLODAP_V2_DIR}/GLODAPv2.2016b_MappedClimatologies/GLODAPv2.2016b.${param}.nc"
            if [ -f "${candidate}" ]; then echo "${candidate}"; return 0; fi
            ;;
    esac

    for dir in "${GLODAP_V2_2023_DIR}" "${GLODAP_V2_DIR}" "${GLODAP_V1_DIR}"; do
        if [ -d "${dir}" ]; then
            for f in "${dir}"/*"${param}"*.nc; do
                if [ -f "${f}" ]; then echo "${f}"; return 0; fi
            done
        fi
    done

    echo "${GLODAP_V2_DIR}/GLODAPv2.2016b.${param}.nc"
}

case "${VAR}" in
    NO3|PO4|Si|O2)
        case "${VAR}" in
            NO3) CODE="n"; FILE_VAR="NO3" ;;
            PO4) CODE="p"; FILE_VAR="PO4" ;;
            Si)  CODE="i"; FILE_VAR="SIL" ;;
            O2)  CODE="o"; FILE_VAR="OXY" ;;
        esac
        prod_var="PRODUCT_${VAR}"
        chosen_prod="${!prod_var:-woa23}"

        if [ "${chosen_prod}" = "woa23" ]; then
            SRC_12M="${RAW_DIR}/woa23/woa23_12m_${CODE}.nc"
            if [ ! -f "${SRC_12M}" ]; then
                echo "Assembling WOA23 12-month profile for ${VAR}..."
                pisces-inidata prepare-woa "${CODE}" "${WOA23_DIR}" "${SRC_12M}"
            fi
            echo "[Step 1/3] Filling missing land values on source 1x1 grid..."
            cdo ${CDO_OPTS} fillmiss "${SRC_12M}" "${TMP_DIR}/filled.nc"

            if [ -n "${TARGET_LEVELS:-}" ]; then
                echo "[Step 2/3] Vertical interpolation to target levels on source grid..."
                cdo ${CDO_OPTS} -intlevel,"${TARGET_LEVELS}" "${TMP_DIR}/filled.nc" "${TMP_DIR}/vint.nc"
                echo "[Step 3/3] Horizontal remapping to ${GRID_NAME}..."
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/vint.nc" "${OUT_FILE}"
            else
                echo "[Step 2/2] Horizontal remapping to ${GRID_NAME}..."
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/filled.nc" "${OUT_FILE}"
            fi

            ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/${VAR}_WOA23_monthly_${GRID_NAME}.nc"
            ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/${VAR}_WOA2009_monthly_${GRID_NAME}.nc"
        else
            # woa2009 or sette_nomask
            SRC_FILE="${RAW_DIR}/official_v5.0.0/data_${FILE_VAR}_nomask.nc"
            echo "[Step 1/3] Selecting ${VAR} from ${SRC_FILE}..."
            cdo ${CDO_OPTS} -selname,"${VAR}" "${SRC_FILE}" "${TMP_DIR}/src_sel.nc"
            echo "[Step 2/3] Extending abyssal depth to 6000m on source grid..."
            pisces-inidata pad "${TMP_DIR}/src_sel.nc" "${TMP_DIR}/padded.nc" --depth 6000.0

            if [ -n "${TARGET_LEVELS:-}" ] && [ "${GRID_NAME}" != "ORCA2" ]; then
                echo "[Step 3/4] Vertical interpolation to target levels on source grid..."
                cdo ${CDO_OPTS} -intlevel,"${TARGET_LEVELS}" "${TMP_DIR}/padded.nc" "${TMP_DIR}/vint.nc"
                echo "[Step 4/4] Horizontal remapping to ${GRID_NAME}..."
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/vint.nc" "${OUT_FILE}"
            else
                echo "[Step 3/3] Horizontal remapping to ${GRID_NAME}..."
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/padded.nc" "${OUT_FILE}"
            fi

            ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/${VAR}_WOA2009_monthly_${GRID_NAME}.nc"
        fi
        ;;

    TALK|TDIC|PiDIC)
        prod_var="PRODUCT_${VAR}"
        chosen_prod="${!prod_var:-glodap_v2_2016b}"
        case "${VAR}" in
            TALK)
                SRC_PARAM="TAlk"
                SRC_VAR="TAlk"
                OUT_VAR_NAME="Alkalini"
                NOMASK_VAR="TALK"
                NOMASK_FILE="${RAW_DIR}/official_v5.0.0/data_ALK_nomask.nc"
                LINK_NAME="Alkalini_GLODAP_annual_${GRID_NAME}.nc"
                ;;
            TDIC)
                SRC_PARAM="TCO2"
                SRC_VAR="TCO2"
                OUT_VAR_NAME="DIC"
                NOMASK_VAR="TDIC"
                NOMASK_FILE="${RAW_DIR}/official_v5.0.0/data_DIC_nomask.nc"
                LINK_NAME="DIC_GLODAP_annual_${GRID_NAME}.nc"
                ;;
            PiDIC)
                SRC_PARAM="PI_TCO2"
                SRC_VAR="PI_TCO2"
                OUT_VAR_NAME="DIC"
                NOMASK_VAR="PiDIC"
                NOMASK_FILE="${RAW_DIR}/official_v5.0.0/data_DIC_nomask.nc"
                LINK_NAME="PiDIC_GLODAP_annual_${GRID_NAME}.nc"
                ;;
        esac

        if [ "${chosen_prod}" = "sette_nomask" ]; then
            echo "Using SETTE regular reference: ${NOMASK_FILE}"
            cdo ${CDO_OPTS} -selname,"${NOMASK_VAR}" "${NOMASK_FILE}" "${TMP_DIR}/src_sel.nc"
            pisces-inidata pad "${TMP_DIR}/src_sel.nc" "${TMP_DIR}/padded.nc" --depth 6000.0
            if [ -n "${TARGET_LEVELS:-}" ] && [ "${GRID_NAME}" != "ORCA2" ]; then
                cdo ${CDO_OPTS} -intlevel,"${TARGET_LEVELS}" "${TMP_DIR}/padded.nc" "${TMP_DIR}/vint.nc"
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/vint.nc" "${OUT_FILE}"
            else
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/padded.nc" "${OUT_FILE}"
            fi
            if [ "${NOMASK_VAR}" != "${OUT_VAR_NAME}" ]; then
                ncrename -O -v "${NOMASK_VAR},${OUT_VAR_NAME}" "${OUT_FILE}" 2>/dev/null || true
            fi
        else
            SRC_FILE="$(resolve_glodap_source "${SRC_PARAM}")"
            echo "Using GLODAP source file: ${SRC_FILE}"
            echo "[Step 1/4] Standardizing GLODAP vertical coordinate and abyssal padding..."
            pisces-inidata prepare-glodap "${SRC_VAR}" "${SRC_FILE}" "${TMP_DIR}/clean.nc"

            echo "[Step 2/4] Filling missing values with cdo fillmiss..."
            cdo ${CDO_OPTS} fillmiss "${TMP_DIR}/clean.nc" "${TMP_DIR}/filled.nc"

            if [ -n "${TARGET_LEVELS:-}" ]; then
                echo "[Step 3/4] Vertical interpolation to target levels on source grid..."
                cdo ${CDO_OPTS} -intlevel,"${TARGET_LEVELS}" "${TMP_DIR}/filled.nc" "${TMP_DIR}/vint.nc"
                echo "[Step 4/4] Horizontal remapping to ${GRID_NAME}..."
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/vint.nc" "${OUT_FILE}"
            else
                echo "[Step 3/3] Horizontal remapping to ${GRID_NAME}..."
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/filled.nc" "${OUT_FILE}"
            fi

            if [ "${SRC_VAR}" != "${OUT_VAR_NAME}" ]; then
                ncrename -O -v "${SRC_VAR},${OUT_VAR_NAME}" "${OUT_FILE}"
            fi
        fi

        ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/${LINK_NAME}"
        ;;

    DOC)
        LINK_NAME="DOC_PISCES_monthly_${GRID_NAME}.nc"
        chosen_doc="${PRODUCT_DOC:-panaiotis2024}"
        echo "Chosen product for DOC: ${chosen_doc}"

        if [ "${chosen_doc}" = "panaiotis2024" ]; then
            SRC_FILE="${PANAIOTIS_DOC_DIR}/panaiotis2024_doc_1deg.nc"
            if [ ! -f "${SRC_FILE}" ]; then
                echo "Panaïotis DOC NetCDF not found. Generating with pisces-inidata prepare-doc..."
                pisces-inidata prepare-doc "${PANAIOTIS_DOC_DIR}" "${SRC_FILE}"
            fi

            echo "[Step 1/4] Filling missing values with cdo fillmiss..."
            cdo ${CDO_OPTS} fillmiss "${SRC_FILE}" "${TMP_DIR}/filled.nc"

            echo "[Step 2/4] Extending abyssal depth to 6000m on source grid..."
            pisces-inidata pad "${TMP_DIR}/filled.nc" "${TMP_DIR}/padded.nc" --depth 6000.0

            if [ -n "${TARGET_LEVELS:-}" ]; then
                echo "[Step 3/4] Vertical interpolation to target levels on source grid..."
                cdo ${CDO_OPTS} -intlevel,"${TARGET_LEVELS}" "${TMP_DIR}/padded.nc" "${TMP_DIR}/vint.nc"
                echo "[Step 4/4] Horizontal remapping to ${GRID_NAME}..."
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/vint.nc" "${OUT_FILE}"
            else
                echo "[Step 3/3] Horizontal remapping to ${GRID_NAME}..."
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/padded.nc" "${OUT_FILE}"
            fi
            ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/DOC_Panaiotis2024_monthly_${GRID_NAME}.nc"

        else
            # sette_nomask (Hansell 2009)
            SRC_FILE="${RAW_DIR}/official_v5.0.0/data_DOC_nomask.nc"
            echo "[Step 1/3] Selecting DOC variable..."
            cdo ${CDO_OPTS} -selname,DOC "${SRC_FILE}" "${TMP_DIR}/src_sel.nc"
            echo "[Step 2/3] Extending abyssal depth to 6000m on source grid..."
            pisces-inidata pad "${TMP_DIR}/src_sel.nc" "${TMP_DIR}/padded.nc" --depth 6000.0

            if [ -n "${TARGET_LEVELS:-}" ] && [ "${GRID_NAME}" != "ORCA2" ]; then
                echo "[Step 3/4] Vertical interpolation to target levels on source grid..."
                cdo ${CDO_OPTS} -intlevel,"${TARGET_LEVELS}" "${TMP_DIR}/padded.nc" "${TMP_DIR}/vint.nc"
                echo "[Step 4/4] Horizontal remapping to ${GRID_NAME}..."
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/vint.nc" "${OUT_FILE}"
            else
                echo "[Step 3/3] Horizontal remapping to ${GRID_NAME}..."
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/padded.nc" "${OUT_FILE}"
            fi
        fi

        ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/${LINK_NAME}"
        ;;

    Fer)
        LINK_NAME="Fer_PISCES_annual_${GRID_NAME}.nc"
        SRC_FILE="${RAW_DIR}/official_v5.0.0/data_FER_nomask.nc"
        if [ "${GRID_NAME}" = "ORCA2" ]; then
            echo "Remapping Fer to ORCA2 (native vertical levels match)..."
            cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" -selname,Fer "${SRC_FILE}" "${OUT_FILE}"
        else
            echo "[Step 1/3] Selecting Fer variable..."
            cdo ${CDO_OPTS} -selname,Fer "${SRC_FILE}" "${TMP_DIR}/src_sel.nc"
            echo "[Step 2/3] Extending abyssal depth to 6000m on source grid..."
            pisces-inidata pad "${TMP_DIR}/src_sel.nc" "${TMP_DIR}/padded.nc" --depth 6000.0
            if [ -n "${TARGET_LEVELS:-}" ]; then
                echo "[Step 3/4] Vertical interpolation to target levels on source grid..."
                cdo ${CDO_OPTS} -intlevel,"${TARGET_LEVELS}" "${TMP_DIR}/padded.nc" "${TMP_DIR}/vint.nc"
                echo "[Step 4/4] Horizontal remapping to ${GRID_NAME}..."
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/vint.nc" "${OUT_FILE}"
            else
                echo "[Step 3/3] Horizontal remapping to ${GRID_NAME}..."
                cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${TMP_DIR}/padded.nc" "${OUT_FILE}"
            fi
        fi

        ln -sfn "$(basename "${OUT_FILE}")" "${OUTPUT_DIR}/${LINK_NAME}"
        ;;

    *)
        echo "ERROR: Unknown tracer variable: ${VAR}" >&2
        exit 1
        ;;
esac

stamp_provenance "${OUT_FILE}"
echo "Successfully generated: ${OUT_FILE}"
