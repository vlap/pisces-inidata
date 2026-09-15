#!/usr/bin/env bash
# ==============================================================================
# format_surface_forcings.sh
# Process atmospheric and surface forcings for PISCES:
#   1) dust.orca.nc: Dust, Dust-Fe, Dust-PO4, Dust-Si, and Fe solubility
#   2) ndeposition.orca.nc: Atmospheric Nitrogen deposition (ndep, ndep2)
#   3) par.orca.nc: Daily Photosynthetically Available Radiation fraction (fr_par)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Load modules
eval "${MODULE_LOAD_CMD}"

COMPONENT="${1:-all}"

TARGET_GRID_NC="${WEIGHTS_DIR}/target_grid_${GRID_NAME}.nc"
if [ ! -f "${TARGET_GRID_NC}" ]; then
    echo "Target grid not found. Generating grid and weights first..."
    bash "${SCRIPT_DIR}/gen_grid_and_weights.sh"
fi

mkdir -p "${OUTPUT_DIR}"

TMP_DIR=$(mktemp -d -p "${SCRATCH_ROOT}" tmp_surf_${COMPONENT}_XXXXXX)
trap 'rm -rf "${TMP_DIR}"' EXIT

sanitize_source_grid() {
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
# 1. Atmospheric Dust Deposition
# ------------------------------------------------------------------------------
process_dust() {
    echo "=== Processing Dust Deposition (dust.orca.nc) ==="
    local out_file="${OUTPUT_DIR}/dust.orca.nc"
    local chosen_dust="${PRODUCT_DUST:-ece3}"

    if [ "${chosen_dust}" = "sette_orca2" ]; then
        local src_file="${RAW_DIR}/official_v5.0.0/dust.orca.new.nc"
        [ -f "${src_file}" ] || src_file="${RAW_DIR}/official_v5.0.0/dust.orca.nc"
        if [ "${GRID_NAME}" = "ORCA2" ]; then
            echo "Copying native ORCA2 SETTE dust forcing..."
            cp "${src_file}" "${out_file}"
        else
            local clean_dust="${TMP_DIR}/clean_dust.nc"
            sanitize_source_grid "${src_file}" "${clean_dust}" "${DUST_VARS[@]}"
            local weights_dust="${WEIGHTS_DIR}/weights_dust_to_${GRID_NAME}.nc"
            if [ ! -f "${weights_dust}" ]; then
                cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${clean_dust}" "${weights_dust}"
            fi
            echo "Remapping dust variables to ${GRID_NAME}..."
            cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${weights_dust}" "${clean_dust}" "${out_file}"
        fi
    elif [ -f "${ECE3_PISCES_DIR}/dust_INCA_ORCA_R1.nc" ]; then
        echo "Remapping dust variables from curated ECE3 baseline..."
        cdo ${CDO_OPTS} ${CDO_COMPRESS} -remapnn,"${TARGET_GRID_NC}" -setgrid,"${ORCA1_GRIDDES}" "${ECE3_PISCES_DIR}/dust_INCA_ORCA_R1.nc" "${out_file}"
    else
        local src_file="${RAW_DIR}/official_v5.0.0/dust.orca.new.nc"
        [ -f "${src_file}" ] || src_file="${RAW_DIR}/official_v5.0.0/dust.orca.nc"
        if [ ! -f "${src_file}" ]; then
            echo "ERROR: Source dust file not found at ${src_file}" >&2
            return 1
        fi
        if [ "${GRID_NAME}" = "ORCA2" ]; then
            cp "${src_file}" "${out_file}"
        else
            local clean_dust="${TMP_DIR}/clean_dust.nc"
            sanitize_source_grid "${src_file}" "${clean_dust}" "${DUST_VARS[@]}"
            local weights_dust="${WEIGHTS_DIR}/weights_dust_to_${GRID_NAME}.nc"
            if [ ! -f "${weights_dust}" ]; then
                cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${clean_dust}" "${weights_dust}"
            fi
            echo "Remapping dust variables to ${GRID_NAME}..."
            cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${weights_dust}" "${clean_dust}" "${out_file}"
        fi
    fi

    ln -sfn "$(basename "${out_file}")" "${OUTPUT_DIR}/dust_INCA_${GRID_NAME}.nc"
    ln -sfn "$(basename "${out_file}")" "${OUTPUT_DIR}/dust_INCA_Mahowald_monthly_${GRID_NAME}.nc"
    stamp_provenance "${out_file}"
    echo "Created: ${out_file}"
}

# ------------------------------------------------------------------------------
# 2. Atmospheric Nitrogen Deposition
# ------------------------------------------------------------------------------
process_ndep() {
    echo "=== Processing Atmospheric N Deposition (ndeposition.orca.nc) ==="
    local out_file="${OUTPUT_DIR}/ndeposition.orca.nc"
    local chosen_ndep="${PRODUCT_NDEP:-ece3}"

    if [ "${chosen_ndep}" = "sette_orca2" ]; then
        local src_file="${RAW_DIR}/official_v5.0.0/ndeposition.orca.nc"
        if [ "${GRID_NAME}" = "ORCA2" ]; then
            echo "Copying native ORCA2 SETTE N-deposition forcing..."
            cp "${src_file}" "${out_file}"
        else
            local clean_ndep="${TMP_DIR}/clean_ndep.nc"
            sanitize_source_grid "${src_file}" "${clean_ndep}" "${NDEP_VARS[@]}"
            local weights_ndep="${WEIGHTS_DIR}/weights_ndep_to_${GRID_NAME}.nc"
            if [ ! -f "${weights_ndep}" ]; then
                cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${clean_ndep}" "${weights_ndep}"
            fi
            echo "Remapping N-deposition variables to ${GRID_NAME}..."
            cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${weights_ndep}" "${clean_ndep}" "${out_file}"
        fi
    elif [ -f "${ECE3_PISCES_DIR}/ndeposition_Duce_ORCA_R1.nc" ]; then
        echo "Remapping N-deposition variables from curated ECE3 baseline..."
        cdo ${CDO_OPTS} ${CDO_COMPRESS} -remapnn,"${TARGET_GRID_NC}" -setgrid,"${ORCA1_GRIDDES}" "${ECE3_PISCES_DIR}/ndeposition_Duce_ORCA_R1.nc" "${out_file}"
    else
        local src_file="${RAW_DIR}/official_v5.0.0/ndeposition.orca.nc"
        if [ ! -f "${src_file}" ]; then
            echo "ERROR: Source ndep file not found at ${src_file}" >&2
            return 1
        fi
        if [ "${GRID_NAME}" = "ORCA2" ]; then
            cp "${src_file}" "${out_file}"
        else
            local clean_ndep="${TMP_DIR}/clean_ndep.nc"
            sanitize_source_grid "${src_file}" "${clean_ndep}" "${NDEP_VARS[@]}"
            local weights_ndep="${WEIGHTS_DIR}/weights_ndep_to_${GRID_NAME}.nc"
            if [ ! -f "${weights_ndep}" ]; then
                cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${clean_ndep}" "${weights_ndep}"
            fi
            echo "Remapping N-deposition variables to ${GRID_NAME}..."
            cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${weights_ndep}" "${clean_ndep}" "${out_file}"
        fi
    fi

    ln -sfn "$(basename "${out_file}")" "${OUTPUT_DIR}/ndeposition_Duce_${GRID_NAME}.nc"
    ln -sfn "$(basename "${out_file}")" "${OUTPUT_DIR}/ndeposition_Duce_monthly_${GRID_NAME}.nc"
    stamp_provenance "${out_file}"
    echo "Created: ${out_file}"
}

# ------------------------------------------------------------------------------
# 3. Photosynthetically Available Radiation (PAR)
# ------------------------------------------------------------------------------
process_par() {
    echo "=== Processing PAR Fraction (par.orca.nc, 365 daily timesteps) ==="
    local out_file="${OUTPUT_DIR}/par.orca.nc"
    local chosen_par="${PRODUCT_PAR:-ece3}"

    if [ "${chosen_par}" = "sette_orca2" ]; then
        local src_file="${RAW_DIR}/official_v5.0.0/par.orca.nc"
        if [ "${GRID_NAME}" = "ORCA2" ]; then
            echo "Copying native ORCA2 SETTE PAR forcing..."
            cp "${src_file}" "${out_file}"
        else
            local clean_par="${TMP_DIR}/clean_par.nc"
            sanitize_source_grid "${src_file}" "${clean_par}" "fr_par"
            local weights_par="${WEIGHTS_DIR}/weights_par_to_${GRID_NAME}.nc"
            if [ ! -f "${weights_par}" ]; then
                cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${clean_par}" "${weights_par}"
            fi
            echo "Remapping PAR daily climatology to ${GRID_NAME}..."
            cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${weights_par}" "${clean_par}" "${out_file}"
        fi
    elif [ -f "${ECE3_PISCES_DIR}/par_fraction_gewex_clim90s00s_ORCA_R1.nc" ]; then
        echo "Remapping PAR daily climatology from curated ECE3 baseline..."
        cdo ${CDO_OPTS} ${CDO_COMPRESS} -remapnn,"${TARGET_GRID_NC}" -setgrid,"${ORCA1_GRIDDES}" "${ECE3_PISCES_DIR}/par_fraction_gewex_clim90s00s_ORCA_R1.nc" "${out_file}"
    else
        local src_file="${RAW_DIR}/official_v5.0.0/par.orca.nc"
        if [ ! -f "${src_file}" ]; then
            echo "ERROR: Source PAR file not found at ${src_file}" >&2
            return 1
        fi
        if [ "${GRID_NAME}" = "ORCA2" ]; then
            cp "${src_file}" "${out_file}"
        else
            local clean_par="${TMP_DIR}/clean_par.nc"
            sanitize_source_grid "${src_file}" "${clean_par}" "fr_par"
            local weights_par="${WEIGHTS_DIR}/weights_par_to_${GRID_NAME}.nc"
            if [ ! -f "${weights_par}" ]; then
                cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${clean_par}" "${weights_par}"
            fi
            echo "Remapping PAR daily climatology to ${GRID_NAME}..."
            cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${weights_par}" "${clean_par}" "${out_file}"
        fi
    fi

    ln -sfn "$(basename "${out_file}")" "${OUTPUT_DIR}/par_fraction_gewex_clim90s00s_${GRID_NAME}.nc"
    stamp_provenance "${out_file}"
    echo "Created: ${out_file}"
}

# Execution switcher
case "${COMPONENT}" in
    dust) process_dust ;;
    ndep) process_ndep ;;
    par)  process_par ;;
    all)
        process_dust
        process_ndep
        process_par
        ;;
    *)
        echo "ERROR: Unknown component: ${COMPONENT} (Choose: dust | ndep | par | all)" >&2
        exit 1
        ;;
esac

echo "=== Surface forcings step finished successfully ==="
