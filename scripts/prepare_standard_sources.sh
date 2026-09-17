#!/usr/bin/env bash
# ==============================================================================
# prepare_standard_sources.sh
# Stage 1 (Grid-Agnostic ETL): Format, clean, sanitize, pad, and standardize
# raw observational datasets into uniform regular NetCDF source files.
#
# Output: ${STANDARDIZED_DIR}/std_<VAR>.nc
#   - Standard variable names (NO3, PO4, Alkalini, DIC, DOC, Fer, ...)
#   - Continuous ocean coverage without gaps (cdo fillmiss on source regular grid)
#   - Standardized vertical coordinates extended to 6000m abyssal depth
#   - CF-compliant coordinates (lon, lat, depth, time)
#
# This stage has ZERO knowledge of target grids (eORCA1, eORCA025, ORCA2).
# It runs once per dataset/preset and is cached across all target grids.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Load modules
eval "${MODULE_LOAD_CMD}"

TARGET_VAR="${1:-all}"
FORCE="${FORCE:-0}"

mkdir -p "${STANDARDIZED_DIR}" "${LOG_DIR}"

TMP_DIR=$(mktemp -d -p "${TMP_BASE}" tmp_prep_std_XXXXXX)
trap 'rm -rf "${TMP_DIR}"' EXIT


sanitize_source_coords() {
    local in_file="$1"
    local out_file="$2"
    shift 2
    local vars=("$@")
    cp "${in_file}" "${out_file}"
    for v in "${vars[@]}"; do
        ncatted -O -a coordinates,"${v}",c,c,"nav_lon nav_lat" "${out_file}" 2>/dev/null || true
    done
    ncatted -O \
        -a coordinates,,c,c,"nav_lon nav_lat" \
        -a units,nav_lon,c,c,"degrees_east" \
        -a units,nav_lat,c,c,"degrees_north" \
        -a standard_name,nav_lon,c,c,"longitude" \
        -a standard_name,nav_lat,c,c,"latitude" \
        "${out_file}" 2>/dev/null || true
}

# ------------------------------------------------------------------------------
# 1. 3D Tracers Standardization
# ------------------------------------------------------------------------------
prepare_tracer_3d() {
    local var="$1"
    local std_file="${STANDARDIZED_DIR}/std_${var}.nc"

    if [ "${FORCE}" -ne 1 ] && [ -f "${std_file}" ] && [ -s "${std_file}" ]; then
        echo "[Stage 1 Cache] Standardized source for ${var} already exists: ${std_file}"
        return 0
    fi

    echo "========================================================================"
    echo " Stage 1 [ETL]: Standardizing Source for 3D Tracer: ${var}"
    echo " Target Output: ${std_file}"
    echo "========================================================================"

    eval "$(pisces-inidata resolve-source "${var}" --preset "${PRESET}" --raw-dir "${RAW_DIR}" --export)"

    case "${HANDLER}" in
        woa23)
            echo "Standardizing WOA23 for ${var}..."
            pisces-inidata prepare-woa "${SRC_VAR}" "${WOA23_DIR}" "${TMP_DIR}/woa_combined_${var}.nc"
            cdo ${CDO_OPTS} fillmiss "${TMP_DIR}/woa_combined_${var}.nc" "${std_file}"
            ;;
        glodap)
            echo "Standardizing GLODAP for ${var} from ${SRC_FILE}..."
            pisces-inidata prepare-glodap "${SRC_VAR}" "${SRC_FILE}" "${TMP_DIR}/clean_${var}.nc"
            cdo ${CDO_OPTS} fillmiss "${TMP_DIR}/clean_${var}.nc" "${TMP_DIR}/filled_${var}.nc"
            if [ "${SRC_VAR}" != "${STD_VAR}" ]; then
                ncrename -O -v "${SRC_VAR},${STD_VAR}" "${TMP_DIR}/filled_${var}.nc" 2>/dev/null || true
            fi
            mv "${TMP_DIR}/filled_${var}.nc" "${std_file}"
            ;;
        doc)
            if [ ! -f "${SRC_FILE}" ]; then
                echo "Building Panaïotis et al. (2024) DOC NetCDF from CSVs..."
                pisces-inidata prepare-doc "${PANAIOTIS_DOC_DIR}" "${TMP_DIR}/doc_prep.nc"
                SRC_FILE="${TMP_DIR}/doc_prep.nc"
            fi
            echo "Extending and filling Panaïotis DOC to ${PAD_DEPTH:-6000.0}m..."
            cdo ${CDO_OPTS} fillmiss "${SRC_FILE}" "${TMP_DIR}/doc_filled.nc"
            pisces-inidata pad "${TMP_DIR}/doc_filled.nc" "${std_file}" --depth "${PAD_DEPTH:-6000.0}"
            ;;
        *)
            # Generic source (e.g. sette_nomask, woa2009, or custom)
            if [ ! -f "${SRC_FILE}" ]; then
                echo "ERROR: Source file ${SRC_FILE} not found. Run download first." >&2
                return 1
            fi
            echo "Extracting and standardizing ${var} from ${SRC_FILE}..."
            cdo ${CDO_OPTS} -selname,"${SRC_VAR}" "${SRC_FILE}" "${TMP_DIR}/src_sel_${var}.nc"
            if [ -n "${PAD_DEPTH:-}" ]; then
                pisces-inidata pad "${TMP_DIR}/src_sel_${var}.nc" "${TMP_DIR}/padded_${var}.nc" --depth "${PAD_DEPTH}"
            else
                cp "${TMP_DIR}/src_sel_${var}.nc" "${TMP_DIR}/padded_${var}.nc"
            fi
            if [ "${SRC_VAR}" != "${STD_VAR}" ]; then
                ncrename -O -v "${SRC_VAR},${STD_VAR}" "${TMP_DIR}/padded_${var}.nc" 2>/dev/null || true
            fi
            mv "${TMP_DIR}/padded_${var}.nc" "${std_file}"
            ;;
    esac

    echo "Successfully standardized: ${std_file}"
}

# ------------------------------------------------------------------------------
# 2. Surface & Boundary Forcings Standardization
# ------------------------------------------------------------------------------
prepare_boundary_forcing() {
    local comp="$1"
    local desc="$2"
    local std_file="${STANDARDIZED_DIR}/std_${comp}.nc"

    if [ "${FORCE}" -ne 1 ] && [ -f "${std_file}" ] && [ -s "${std_file}" ]; then
        echo "[Stage 1 Cache] Standardized source for ${comp} already exists: ${std_file}"
        return 0
    fi

    echo "=== Standardizing ${desc} (${comp}) ==="
    eval "$(pisces-inidata resolve-source "${comp}" --preset "${PRESET}" --raw-dir "${RAW_DIR}" --export)"

    if [ ! -f "${SRC_FILE}" ]; then
        echo "ERROR: Source ${comp} file not found at ${SRC_FILE}." >&2
        return 1
    fi

    local tmp_work="${TMP_DIR}/${comp}_prep.nc"
    cp "${SRC_FILE}" "${tmp_work}"

    # If coordinates need to be copied from a donor file (e.g. bathy for river)
    if [ -n "${COORDS_SOURCE_FILE:-}" ] && [ -f "${COORDS_SOURCE_FILE}" ]; then
        ncks -A -v nav_lon,nav_lat "${COORDS_SOURCE_FILE}" "${tmp_work}" 2>/dev/null || true
    fi

    read -r -a vars_array <<< "${VARS_LIST}"
    sanitize_source_coords "${tmp_work}" "${std_file}" "${vars_array[@]}"
    echo "Successfully standardized: ${std_file}"
}

prepare_dust()    { prepare_boundary_forcing "dust" "Atmospheric Dust Deposition"; }
prepare_ndep()    { prepare_boundary_forcing "ndep" "Atmospheric Nitrogen Deposition"; }
prepare_par()     { prepare_boundary_forcing "par" "PAR Daily Fraction"; }
prepare_bathy()   { prepare_boundary_forcing "bathy" "Bathymetric Shelf Fraction"; }
prepare_hydrofe() { prepare_boundary_forcing "hydrofe" "Hydrothermal Vent Fe"; }
prepare_river()   { prepare_boundary_forcing "river" "River Nutrient Forcings"; }

# ------------------------------------------------------------------------------
# Dispatcher
# ------------------------------------------------------------------------------
case "${TARGET_VAR}" in
    NO3|PO4|Si|O2|TALK|TDIC|PiDIC|DOC|Fer)
        prepare_tracer_3d "${TARGET_VAR}"
        ;;
    dust)     prepare_dust ;;
    ndep)     prepare_ndep ;;
    par)      prepare_par ;;
    bathy)    prepare_bathy ;;
    hydrofe)  prepare_hydrofe ;;
    river|rivers) prepare_river ;;
    all)
        for t in "${TRACERS_3D[@]}"; do
            prepare_tracer_3d "${t}"
        done
        prepare_dust
        prepare_ndep
        prepare_par
        prepare_bathy
        prepare_hydrofe
        prepare_river
        ;;
    *)
        echo "ERROR: Unknown variable or component: ${TARGET_VAR}" >&2
        echo "Options: ${TRACERS_3D[*]} dust ndep par bathy hydrofe river all" >&2
        exit 1
        ;;
esac

echo "=== Stage 1 Standardization complete for ${TARGET_VAR}! ==="
