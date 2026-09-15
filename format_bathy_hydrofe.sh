#!/usr/bin/env bash
# ==============================================================================
# format_bathy_hydrofe.sh
# Process bathymetric shelf fraction (sediment Fe) and hydrothermal vent Fe
# sources for PISCES:
#   1) bathy.orca.nc: Shelf/slope fraction for sediment iron release
#   2) hydrofe.orca.nc: Hydrothermal vent iron injection along ridges
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

TMP_DIR=$(mktemp -d -p "${SCRATCH_ROOT}" tmp_bathy_${COMPONENT}_XXXXXX)
trap 'rm -rf "${TMP_DIR}"' EXIT

sanitize_source_grid() {
    local in_file="$1"
    local out_file="$2"
    cp "${in_file}" "${out_file}"
    ncatted -O \
        -a coordinates,,c,c,"nav_lon nav_lat" \
        -a units,nav_lon,c,c,"degrees_east" \
        -a units,nav_lat,c,c,"degrees_north" \
        -a standard_name,nav_lon,c,c,"longitude" \
        -a standard_name,nav_lat,c,c,"latitude" \
        "${out_file}" 2>/dev/null || true
}

process_bathy() {
    echo "=== Processing Bathymetric Shelf Fraction (bathy.orca.nc) ==="
    local src_file="${RAW_DIR}/official_v5.0.0/bathy.orca.nc"
    local out_file="${OUTPUT_DIR}/bathy.orca.nc"

    if [ ! -f "${src_file}" ]; then
        echo "ERROR: Source bathy file not found at ${src_file}" >&2
        return 1
    fi

    local clean_bathy="${TMP_DIR}/clean_bathy.nc"
    sanitize_source_grid "${src_file}" "${clean_bathy}"

    local weights_bathy="${WEIGHTS_DIR}/weights_bathy_to_${GRID_NAME}.nc"
    if [ ! -f "${weights_bathy}" ]; then
        cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${clean_bathy}" "${weights_bathy}"
    fi

    echo "Remapping bathy shelf fraction to ${GRID_NAME}..."
    cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${weights_bathy}" "${clean_bathy}" "${out_file}"
    ln -sfn "$(basename "${out_file}")" "${OUTPUT_DIR}/pmarge_etopo_${GRID_NAME}.nc"
    echo "Created: ${out_file}"
}

process_hydrofe() {
    echo "=== Processing Hydrothermal Iron Source (hydrofe.orca.nc) ==="
    local src_file="${RAW_DIR}/official_v5.0.0/hydrofe.orca.nc"
    local out_file="${OUTPUT_DIR}/hydrofe.orca.nc"

    if [ ! -f "${src_file}" ]; then
        echo "ERROR: Source hydrofe file not found at ${src_file}" >&2
        return 1
    fi

    local clean_hydro="${TMP_DIR}/clean_hydro.nc"
    sanitize_source_grid "${src_file}" "${clean_hydro}"

    local weights_hydro="${WEIGHTS_DIR}/weights_hydrofe_to_${GRID_NAME}.nc"
    if [ ! -f "${weights_hydro}" ]; then
        cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" "${clean_hydro}" "${weights_hydro}"
    fi

    echo "Remapping hydrothermal Fe source to ${GRID_NAME}..."
    cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${weights_hydro}" "${clean_hydro}" "${out_file}"
    echo "Created: ${out_file}"
}

case "${COMPONENT}" in
    bathy)   process_bathy ;;
    hydrofe) process_hydrofe ;;
    all)
        process_bathy
        process_hydrofe
        ;;
    *)
        echo "ERROR: Unknown component: ${COMPONENT} (Choose: bathy | hydrofe | all)" >&2
        exit 1
        ;;
esac

echo "=== Bathy & Hydrothermal step finished successfully ==="
