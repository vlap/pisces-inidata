#!/usr/bin/env bash
# ==============================================================================
# scripts/remap_field.sh
# Decoupled Stage 2 (Target Remapping): Pure POSIX Shell + CDO + NCO
#
# Interpolates standardized NetCDF sources (std_<VAR>.nc) to target NEMO grid.
# Zero Python dependency: runs natively on HPC compute nodes with 'module load CDO NCO'.
#
# Usage:
#   scripts/remap_field.sh <GRID_NAME> <VAR_NAME|all>
# Example:
#   scripts/remap_field.sh eORCA025 NO3
#   scripts/remap_field.sh eORCA1 all
# ==============================================================================

set -euo pipefail

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <GRID_NAME> <VAR_NAME|all>" >&2
    echo "Example: $0 eORCA025 NO3" >&2
    exit 1
fi

GRID_NAME="$1"
VAR="$2"

# ------------------------------------------------------------------------------
# 1. Directory & Path Resolution
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

WORKSPACE="${PISCES_WORKSPACE:-${REPO_ROOT}}"
STANDARDIZED_DIR="${STANDARDIZED_DIR:-${WORKSPACE}/pisces_output/standardized_sources}"
if [ ! -d "${STANDARDIZED_DIR}" ] && [ -d "${REPO_ROOT}/pisces_output/standardized_sources" ]; then
    STANDARDIZED_DIR="${REPO_ROOT}/pisces_output/standardized_sources"
fi

OUTPUT_DIR="${OUTPUT_DIR:-${WORKSPACE}/pisces_output/${GRID_NAME}/inidata}"
WEIGHTS_DIR="${WEIGHTS_DIR:-${WORKSPACE}/grids/${GRID_NAME}/weights}"
if [ ! -d "${WEIGHTS_DIR}" ] && [ -d "${REPO_ROOT}/grids/${GRID_NAME}/weights" ]; then
    WEIGHTS_DIR="${REPO_ROOT}/grids/${GRID_NAME}/weights"
fi

DOMAIN_DIR="${DOMAIN_DIR:-${REPO_ROOT}/domain/${GRID_NAME}}"
DOMAIN_CFG="${DOMAIN_CFG:-${DOMAIN_DIR}/domain_cfg.nc}"
if [ ! -f "${DOMAIN_CFG}" ]; then
    # Standard BSC EC-Earth / NEMO domain locations on Nord4 / MN5
    for cand in \
        "/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain/${GRID_NAME}/domain_cfg.nc" \
        "/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain/${GRID_NAME}/${GRID_NAME}_domain_cfg.nc" \
        "${REPO_ROOT}/domain/domain_cfg_${GRID_NAME}.nc"; do
        if [ -f "${cand}" ]; then
            DOMAIN_CFG="${cand}"
            break
        fi
    done
fi

TARGET_GRID_NC="${WEIGHTS_DIR}/target_grid_${GRID_NAME}.nc"
WEIGHTS_BILIN="${WEIGHTS_DIR}/weights_r360x180_to_${GRID_NAME}_bilin.nc"

CDO_THREADS="${CDO_THREADS:-4}"
CDO_OPTS="-s -L -P ${CDO_THREADS}"
CDO_COMPRESS="-f nc4c -z zip_4"

mkdir -p "${OUTPUT_DIR}" "${WEIGHTS_DIR}"

# ------------------------------------------------------------------------------
# 2. Batch "all" Dispatcher
# ------------------------------------------------------------------------------
if [ "${VAR}" = "all" ]; then
    VARS=(NO3 PO4 Si O2 TALK TDIC PiDIC DOC Fer dust ndep par bathy hydrofe river)
    for v in "${VARS[@]}"; do
        bash "${BASH_SOURCE[0]}" "${GRID_NAME}" "${v}"
    done
    echo "=== All 15 fields successfully remapped to ${GRID_NAME}! ==="
    exit 0
fi

# ------------------------------------------------------------------------------
# 3. Variable Metadata & Conventions Lookup
# ------------------------------------------------------------------------------
OUT_FILE=""
FIELD_TYPE=""
SYMLINKS=()

case "${VAR}" in
    NO3)
        OUT_FILE="data_NO3_${GRID_NAME}.nc"
        FIELD_TYPE="3d"
        SYMLINKS=("NO3_WOA23_monthly_${GRID_NAME}.nc" "data_NO3_nomask.nc")
        ;;
    PO4)
        OUT_FILE="data_PO4_${GRID_NAME}.nc"
        FIELD_TYPE="3d"
        SYMLINKS=("PO4_WOA23_monthly_${GRID_NAME}.nc" "data_PO4_nomask.nc")
        ;;
    Si)
        OUT_FILE="data_Si_${GRID_NAME}.nc"
        FIELD_TYPE="3d"
        SYMLINKS=("Si_WOA23_monthly_${GRID_NAME}.nc" "data_SIL_nomask.nc")
        ;;
    O2)
        OUT_FILE="data_O2_${GRID_NAME}.nc"
        FIELD_TYPE="3d"
        SYMLINKS=("O2_WOA23_monthly_${GRID_NAME}.nc" "data_OXY_nomask.nc")
        ;;
    TALK)
        OUT_FILE="data_TALK_${GRID_NAME}.nc"
        FIELD_TYPE="3d"
        SYMLINKS=("Alkalini_GLODAP_annual_${GRID_NAME}.nc" "data_ALK_nomask.nc")
        ;;
    TDIC)
        OUT_FILE="data_TDIC_${GRID_NAME}.nc"
        FIELD_TYPE="3d"
        SYMLINKS=("DIC_GLODAP_annual_${GRID_NAME}.nc" "data_DIC_nomask.nc")
        ;;
    PiDIC)
        OUT_FILE="data_PiDIC_${GRID_NAME}.nc"
        FIELD_TYPE="3d"
        SYMLINKS=("PiDIC_GLODAP_annual_${GRID_NAME}.nc")
        ;;
    DOC)
        OUT_FILE="data_DOC_${GRID_NAME}.nc"
        FIELD_TYPE="3d"
        SYMLINKS=("DOC_PISCES_monthly_${GRID_NAME}.nc")
        ;;
    Fer)
        OUT_FILE="data_Fer_${GRID_NAME}.nc"
        FIELD_TYPE="3d"
        SYMLINKS=("data_FER_nomask.nc")
        ;;
    dust)
        OUT_FILE="dust.orca.nc"
        FIELD_TYPE="2d"
        SYMLINKS=("dust_INCA_${GRID_NAME}.nc" "dust_INCA_Mahowald_monthly_${GRID_NAME}.nc")
        ;;
    ndep)
        OUT_FILE="ndeposition.orca.nc"
        FIELD_TYPE="2d"
        SYMLINKS=("ndeposition_Duce_${GRID_NAME}.nc" "ndeposition_Duce_monthly_${GRID_NAME}.nc")
        ;;
    par)
        OUT_FILE="par.orca.nc"
        FIELD_TYPE="2d"
        SYMLINKS=("par_GEWEX_${GRID_NAME}.nc" "par_fraction_daily_${GRID_NAME}.nc")
        ;;
    bathy)
        OUT_FILE="bathy.orca.nc"
        FIELD_TYPE="bathy"
        SYMLINKS=("pmarge_etopo_${GRID_NAME}.nc")
        ;;
    hydrofe)
        OUT_FILE="hydrofe.orca.nc"
        FIELD_TYPE="hydrofe"
        SYMLINKS=("hydrothermal_fe_forcing_${GRID_NAME}.nc")
        ;;
    river|rivers)
        OUT_FILE="river.orca.nc"
        FIELD_TYPE="river"
        SYMLINKS=("river_global_news_${GRID_NAME}.nc")
        ;;
    *)
        echo "ERROR: Unknown variable '${VAR}'. Supported: NO3, PO4, Si, O2, TALK, TDIC, PiDIC, DOC, Fer, dust, ndep, par, bathy, hydrofe, river" >&2
        exit 1
        ;;
esac

FINAL_OUT="${OUTPUT_DIR}/${OUT_FILE}"
STD_FILE="${STANDARDIZED_DIR}/std_${VAR}.nc"

# Fallback alias for river
if [ ! -f "${STD_FILE}" ] && [ "${VAR}" = "river" ] && [ -f "${STANDARDIZED_DIR}/std_rivers.nc" ]; then
    STD_FILE="${STANDARDIZED_DIR}/std_rivers.nc"
fi

if [ ! -f "${STD_FILE}" ]; then
    echo "ERROR: Standardized source file not found: ${STD_FILE}" >&2
    echo "Run Stage 1 preparation first (e.g. 'pisces-inidata download --pack ece4 --prepare')" >&2
    exit 1
fi

if [ ! -f "${TARGET_GRID_NC}" ] || [ ! -f "${WEIGHTS_BILIN}" ]; then
    echo "ERROR: Target grid description or weights missing:" >&2
    echo "  Grid NC:    ${TARGET_GRID_NC}" >&2
    echo "  Weights NC: ${WEIGHTS_BILIN}" >&2
    echo "Generate grid weights first using 'pisces-inidata produce --grid ${GRID_NAME}'" >&2
    exit 1
fi

echo "========================================================================"
echo " Stage 2 [Remap]: Mapping ${VAR} (${FIELD_TYPE}) to ${GRID_NAME}"
echo " Source:  ${STD_FILE}"
echo " Target:  ${FINAL_OUT}"
echo "========================================================================"

TMP_DIR="$(mktemp -d -p "${TMPDIR:-/tmp}" "pisces_remap_${VAR}_XXXXXX")"
trap 'rm -rf "${TMP_DIR}"' EXIT

# ------------------------------------------------------------------------------
# 4. Core CDO Remapping Operations
# ------------------------------------------------------------------------------
case "${FIELD_TYPE}" in
    3d)
        target_levels=""
        if [ -f "${DOMAIN_CFG}" ]; then
            if command -v ncks >/dev/null 2>&1; then
                target_levels="$(ncks -s '%f,' -H -C -v nav_lev "${DOMAIN_CFG}" 2>/dev/null | sed 's/,$//' | tr -d ' \n' || true)"
            fi
            if [ -z "${target_levels:-}" ] && command -v ncdump >/dev/null 2>&1; then
                target_levels="$(ncdump -v nav_lev "${DOMAIN_CFG}" 2>/dev/null | sed -e '1,/data:/d' -e 's/.*nav_lev =//' -e 's/}.*//' -e 's/;//' | tr '\n\t ' ',' | sed -e 's/,,*/,/g' -e 's/^,//' -e 's/,$//' || true)"
            fi
        fi

        if [ -n "${target_levels:-}" ]; then
            echo "Vertical level interpolation (-intlevel) + horizontal remap to ${GRID_NAME}..."
            cdo ${CDO_OPTS} ${CDO_COMPRESS} -maxc,0 \
                -remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" \
                -intlevel,"${target_levels}" "${STD_FILE}" "${FINAL_OUT}"
        else
            echo "Horizontal remap to ${GRID_NAME} (preserving existing levels)..."
            cdo ${CDO_OPTS} ${CDO_COMPRESS} -maxc,0 \
                -remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${STD_FILE}" "${FINAL_OUT}"
        fi
        ;;

    2d)
        # Check if source grid dimensions already match target
        weights_2d="${WEIGHTS_DIR}/weights_${VAR}_to_${GRID_NAME}.nc"
        if [ ! -f "${weights_2d}" ]; then
            echo "Precomputing 2D weights for ${VAR}..."
            cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${STD_FILE}" "${weights_2d}"
        fi
        echo "Remapping 2D surface forcing ${VAR} to ${GRID_NAME}..."
        cdo ${CDO_OPTS} ${CDO_COMPRESS} -maxc,0 \
            -remap,"${TARGET_GRID_NC}","${weights_2d}" "${STD_FILE}" "${FINAL_OUT}"
        ;;

    bathy)
        echo "Remapping bathymetric shelf fraction using nearest-neighbor (remapnn)..."
        cdo ${CDO_OPTS} ${CDO_COMPRESS} \
            remapnn,"${TARGET_GRID_NC}" "${STD_FILE}" "${FINAL_OUT}"
        ;;

    hydrofe)
        echo "Remapping hydrothermal iron ridge vents using nearest-neighbor (remapnn)..."
        cdo ${CDO_OPTS} ${CDO_COMPRESS} \
            remapnn,"${TARGET_GRID_NC}" "${STD_FILE}" "${FINAL_OUT}"
        ;;

    river)
        echo "Remapping river nutrient discharge using distance-weighted (remapdis)..."
        cdo ${CDO_OPTS} ${CDO_COMPRESS} -maxc,0 \
            -remapdis,"${TARGET_GRID_NC}" "${STD_FILE}" "${FINAL_OUT}"
        ;;
esac

# ------------------------------------------------------------------------------
# 5. Namelist Compatibility Symlinks & CF Provenance Metadata
# ------------------------------------------------------------------------------
for sym in "${SYMLINKS[@]}"; do
    ln -sfn "${OUT_FILE}" "${OUTPUT_DIR}/${sym}"
done

ncatted -O -h \
    -a history,global,a,c," ; $(date -u +'%Y-%m-%dT%H:%M:%SZ') - Remapped to ${GRID_NAME} via scripts/remap_field.sh" \
    -a institution,global,m,c,"EC-Earth Consortium" \
    "${FINAL_OUT}" 2>/dev/null || true

echo "✓ Successfully remapped ${VAR} -> ${FINAL_OUT}"
