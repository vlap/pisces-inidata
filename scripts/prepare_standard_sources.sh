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

resolve_glodap_source() {
    local param="$1" # TAlk, TCO2, PI_TCO2
    local ver="${PRODUCT_TALK:-v2.2016b}"
    pisces-inidata resolve-glodap "${param}" --raw-dir "${RAW_DIR}" --version "${ver}"
}


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

    case "${var}" in
        NO3|PO4|Si|O2)
            local prod_var="PRODUCT_${var}"
            local chosen="${!prod_var:-woa23}"
            local file_var="${var}"
            [ "${var}" = "Si" ] && file_var="SIL"
            [ "${var}" = "O2" ] && file_var="OXY"

            if [ "${chosen}" = "woa23" ]; then
                echo "Standardizing WOA23 for ${var}..."
                local src_var="n_an"
                [ "${var}" = "PO4" ] && src_var="p_an"
                [ "${var}" = "Si" ] && src_var="i_an"
                [ "${var}" = "O2" ] && src_var="o_an"

                pisces-inidata prepare-woa "${src_var}" "${WOA23_DIR}" "${TMP_DIR}/woa_combined_${var}.nc"
                cdo ${CDO_OPTS} fillmiss "${TMP_DIR}/woa_combined_${var}.nc" "${std_file}"
            else
                local src_file="${RAW_DIR}/official_v5.0.0/data_${file_var}_nomask.nc"
                if [ ! -f "${src_file}" ]; then
                    echo "ERROR: Source file ${src_file} not found. Run download first." >&2
                    return 1
                fi
                echo "Extracting and padding ${var} from ${src_file}..."
                cdo ${CDO_OPTS} -selname,"${var}" "${src_file}" "${TMP_DIR}/src_sel_${var}.nc"
                pisces-inidata pad "${TMP_DIR}/src_sel_${var}.nc" "${std_file}" --depth 6000.0
            fi
            ;;

        TALK|TDIC|PiDIC)
            local prod_var="PRODUCT_${var}"
            local chosen="${!prod_var:-glodap_v2_2016b}"
            local src_param src_var out_var_name nomask_var nomask_file
            case "${var}" in
                TALK)
                    src_param="TAlk"; src_var="TAlk"; out_var_name="Alkalini"
                    nomask_var="TALK"; nomask_file="data_ALK_nomask.nc"
                    ;;
                TDIC)
                    src_param="TCO2"; src_var="TCO2"; out_var_name="DIC"
                    nomask_var="TDIC"; nomask_file="data_DIC_nomask.nc"
                    ;;
                PiDIC)
                    src_param="PI_TCO2"; src_var="PI_TCO2"; out_var_name="DIC"
                    nomask_var="PiDIC"; nomask_file="data_DIC_nomask.nc"
                    ;;
            esac

            if [ "${chosen}" = "sette_nomask" ]; then
                local src_file="${RAW_DIR}/official_v5.0.0/${nomask_file}"
                echo "Standardizing SETTE nomask for ${var} from ${src_file}..."
                cdo ${CDO_OPTS} -selname,"${nomask_var}" "${src_file}" "${TMP_DIR}/src_sel_${var}.nc"
                pisces-inidata pad "${TMP_DIR}/src_sel_${var}.nc" "${TMP_DIR}/padded_${var}.nc" --depth 6000.0
                if [ "${nomask_var}" != "${out_var_name}" ]; then
                    ncrename -O -v "${nomask_var},${out_var_name}" "${TMP_DIR}/padded_${var}.nc" 2>/dev/null || true
                fi
                mv "${TMP_DIR}/padded_${var}.nc" "${std_file}"
            else
                local src_file
                src_file="$(resolve_glodap_source "${src_param}")"
                echo "Standardizing GLODAP for ${var} from ${src_file}..."
                pisces-inidata prepare-glodap "${src_var}" "${src_file}" "${TMP_DIR}/clean_${var}.nc"
                cdo ${CDO_OPTS} fillmiss "${TMP_DIR}/clean_${var}.nc" "${TMP_DIR}/filled_${var}.nc"
                if [ "${src_var}" != "${out_var_name}" ]; then
                    ncrename -O -v "${src_var},${out_var_name}" "${TMP_DIR}/filled_${var}.nc" 2>/dev/null || true
                fi
                mv "${TMP_DIR}/filled_${var}.nc" "${std_file}"
            fi
            ;;

        DOC)
            local chosen="${PRODUCT_DOC:-panaiotis2024}"
            if [ "${chosen}" = "panaiotis2024" ]; then
                local src_file="${PANAIOTIS_DOC_DIR}/panaiotis2024_doc_1deg.nc"
                if [ ! -f "${src_file}" ]; then
                    echo "Building Panaïotis et al. (2024) DOC NetCDF from CSVs..."
                    pisces-inidata prepare-doc "${PANAIOTIS_DOC_DIR}" "${TMP_DIR}/doc_prep.nc"
                    src_file="${TMP_DIR}/doc_prep.nc"
                fi
                echo "Extending and filling Panaïotis DOC to 6000m..."
                cdo ${CDO_OPTS} fillmiss "${src_file}" "${TMP_DIR}/doc_filled.nc"
                pisces-inidata pad "${TMP_DIR}/doc_filled.nc" "${std_file}" --depth 6000.0
            else
                local src_file="${RAW_DIR}/official_v5.0.0/data_DOC_nomask.nc"
                echo "Standardizing SETTE nomask DOC from ${src_file}..."
                cdo ${CDO_OPTS} -selname,DOC "${src_file}" "${TMP_DIR}/src_sel_doc.nc"
                pisces-inidata pad "${TMP_DIR}/src_sel_doc.nc" "${std_file}" --depth 6000.0
            fi
            ;;

        Fer)
            local src_file="${RAW_DIR}/official_v5.0.0/data_FER_nomask.nc"
            echo "Standardizing Tagliabue Fe from ${src_file}..."
            cdo ${CDO_OPTS} -selname,Fer "${src_file}" "${TMP_DIR}/src_sel_fer.nc"
            pisces-inidata pad "${TMP_DIR}/src_sel_fer.nc" "${std_file}" --depth 6000.0
            ;;

        *)
            echo "ERROR: Unknown 3D tracer: ${var}" >&2
            return 1
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
    local src_file="$3"
    shift 3
    local vars=("$@")
    local std_file="${STANDARDIZED_DIR}/std_${comp}.nc"

    if [ "${FORCE}" -ne 1 ] && [ -f "${std_file}" ] && [ -s "${std_file}" ]; then
        echo "[Stage 1 Cache] Standardized source for ${comp} already exists: ${std_file}"
        return 0
    fi

    echo "=== Standardizing ${desc} ==="
    if [ ! -f "${src_file}" ]; then
        echo "ERROR: Source ${comp} file not found at ${src_file}." >&2
        return 1
    fi
    sanitize_source_coords "${src_file}" "${std_file}" "${vars[@]}"
    echo "Successfully standardized: ${std_file}"
}

prepare_dust() {
    local src_file="${RAW_DIR}/official_v5.0.0/dust.orca.new.nc"
    [ -f "${src_file}" ] || src_file="${RAW_DIR}/official_v5.0.0/dust.orca.nc"
    prepare_boundary_forcing "dust" "Atmospheric Dust Deposition" "${src_file}" "${DUST_VARS[@]}"
}

prepare_ndep() {
    prepare_boundary_forcing "ndep" "Atmospheric Nitrogen Deposition" "${RAW_DIR}/official_v5.0.0/ndeposition.orca.nc" "${NDEP_VARS[@]}"
}

prepare_par() {
    prepare_boundary_forcing "par" "PAR Daily Fraction" "${RAW_DIR}/official_v5.0.0/par.orca.nc" "fr_par"
}

prepare_bathy() {
    prepare_boundary_forcing "bathy" "Bathymetric Shelf Fraction" "${RAW_DIR}/official_v5.0.0/bathy.orca.nc" "bathy"
}

prepare_hydrofe() {
    prepare_boundary_forcing "hydrofe" "Hydrothermal Vent Fe" "${RAW_DIR}/official_v5.0.0/hydrofe.orca.nc" "epsdb"
}

prepare_river() {
    local std_file="${STANDARDIZED_DIR}/std_river.nc"
    if [ "${FORCE}" -ne 1 ] && [ -f "${std_file}" ] && [ -s "${std_file}" ]; then
        echo "[Stage 1 Cache] Standardized source for river already exists: ${std_file}"
        return 0
    fi
    echo "=== Standardizing River Nutrient Forcings ==="
    local src_file="${RAW_DIR}/official_v5.0.0/river.orca.nc"
    if [ ! -f "${src_file}" ]; then
        echo "ERROR: Source river file not found at ${src_file}." >&2
        return 1
    fi
    cp "${src_file}" "${TMP_DIR}/river_clean.nc"
    if [ -f "${RAW_DIR}/official_v5.0.0/bathy.orca.nc" ]; then
        ncks -A -v nav_lon,nav_lat "${RAW_DIR}/official_v5.0.0/bathy.orca.nc" "${TMP_DIR}/river_clean.nc" 2>/dev/null || true
    fi
    sanitize_source_coords "${TMP_DIR}/river_clean.nc" "${std_file}" "${RIVER_VARS[@]}"
    echo "Successfully standardized: ${std_file}"
}

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
