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

# ------------------------------------------------------------------------------
# 1. Atmospheric Dust Deposition
# ------------------------------------------------------------------------------
process_dust() {
    echo "=== Processing Dust Deposition (dust.orca.nc) ==="
    local src_file="${RAW_DIR}/official_v5.0.0/dust.orca.new.nc"
    [ -f "${src_file}" ] || src_file="${RAW_DIR}/official_v5.0.0/dust.orca.nc"
    local out_file="${OUTPUT_DIR}/dust.orca.nc"

    if [ ! -f "${src_file}" ]; then
        echo "ERROR: Source dust file not found at ${src_file}" >&2
        return 1
    fi

    echo "Generating weights for dust grid..."
    local weights_dust="${WEIGHTS_DIR}/weights_dust_to_${GRID_NAME}.nc"
    if [ ! -f "${weights_dust}" ]; then
        cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${src_file}" "${weights_dust}"
    fi

    echo "Remapping dust variables to ${GRID_NAME}..."
    cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${weights_dust}" "${src_file}" "${out_file}"
    echo "Created: ${out_file}"
}

# ------------------------------------------------------------------------------
# 2. Atmospheric Nitrogen Deposition
# ------------------------------------------------------------------------------
process_ndep() {
    echo "=== Processing Atmospheric N Deposition (ndeposition.orca.nc) ==="
    local src_file="${RAW_DIR}/official_v5.0.0/ndeposition.orca.nc"
    local out_file="${OUTPUT_DIR}/ndeposition.orca.nc"

    if [ ! -f "${src_file}" ]; then
        echo "ERROR: Source ndep file not found at ${src_file}" >&2
        return 1
    fi

    local weights_ndep="${WEIGHTS_DIR}/weights_ndep_to_${GRID_NAME}.nc"
    if [ ! -f "${weights_ndep}" ]; then
        cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${src_file}" "${weights_ndep}"
    fi

    echo "Remapping N-deposition variables to ${GRID_NAME}..."
    cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${weights_ndep}" "${src_file}" "${out_file}"
    echo "Created: ${out_file}"
}

# ------------------------------------------------------------------------------
# 3. Photosynthetically Available Radiation (PAR)
# ------------------------------------------------------------------------------
process_par() {
    echo "=== Processing PAR Fraction (par.orca.nc, 365 daily timesteps) ==="
    local src_file="${RAW_DIR}/official_v5.0.0/par.orca.nc"
    local out_file="${OUTPUT_DIR}/par.orca.nc"

    if [ ! -f "${src_file}" ]; then
        echo "ERROR: Source PAR file not found at ${src_file}" >&2
        return 1
    fi

    local weights_par="${WEIGHTS_DIR}/weights_par_to_${GRID_NAME}.nc"
    if [ ! -f "${weights_par}" ]; then
        cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${src_file}" "${weights_par}"
    fi

    echo "Remapping PAR daily climatology to ${GRID_NAME}..."
    cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${weights_par}" "${src_file}" "${out_file}"
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
