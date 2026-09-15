#!/usr/bin/env bash
# ==============================================================================
# gen_grid_and_weights.sh
# Generate target grid netCDF and precompute CDO remapping weights.
# Uses domain_cfg.nc and maskutil.nc to define the curvilinear ocean grid.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Load modules
eval "${MODULE_LOAD_CMD}"

mkdir -p "${WEIGHTS_DIR}" "${LOG_DIR}"

TARGET_GRID_NC="${WEIGHTS_DIR}/target_grid_${GRID_NAME}.nc"
TARGET_AREA_NC="${WEIGHTS_DIR}/target_area_${GRID_NAME}.nc"
GRIDDES_TXT="${WEIGHTS_DIR}/griddes_${GRID_NAME}.txt"

echo "=== [1/3] Creating target grid NetCDF from domain_cfg and maskutil ==="
echo "Target grid: ${GRID_NAME}"
echo "Domain config: ${DOMAIN_CFG}"
echo "Mask utility: ${MASKUTIL}"

TMP_DIR=$(mktemp -d -p "${SCRATCH_ROOT}" tmp_grid_XXXXXX)
trap 'rm -rf "${TMP_DIR}"' EXIT

if [ -f "${DOMAIN_CFG}" ] && [ -f "${MASKUTIL}" ]; then
    echo "Extracting grid coordinates from ${DOMAIN_CFG} and ${MASKUTIL}..."
    ncks -O -4 -v glamt,gphit "${DOMAIN_CFG}" "${TMP_DIR}/grid_coords.nc"
    ncks -A -4 -v tmaskutil "${MASKUTIL}" "${TMP_DIR}/grid_coords.nc"
    ncrename -v glamt,lon -v gphit,lat "${TMP_DIR}/grid_coords.nc"
    ncwa -O -a time_counter "${TMP_DIR}/grid_coords.nc" "${TMP_DIR}/grid_coords.nc" 2>/dev/null || true
    ncwa -O -a t "${TMP_DIR}/grid_coords.nc" "${TMP_DIR}/grid_coords.nc" 2>/dev/null || true
    ncatted -O \
        -a coordinates,tmaskutil,c,c,"lon lat" \
        -a units,lon,c,c,"degrees_east" \
        -a units,lat,c,c,"degrees_north" \
        -a standard_name,lon,c,c,"longitude" \
        -a standard_name,lat,c,c,"latitude" \
        "${TMP_DIR}/grid_coords.nc"
    mv "${TMP_DIR}/grid_coords.nc" "${TARGET_GRID_NC}"
elif [ "${GRID_NAME}" = "ORCA2" ] && [ -f "${RAW_DIR}/official_v5.0.0/bathy.orca.nc" ]; then
    echo "Domain config not found; constructing ORCA2 target grid from official SETTE bathy.orca.nc..."
    ncks -O -4 -v nav_lon,nav_lat,bathy "${RAW_DIR}/official_v5.0.0/bathy.orca.nc" "${TMP_DIR}/grid_coords.nc"
    ncrename -v nav_lon,lon -v nav_lat,lat -v bathy,tmaskutil "${TMP_DIR}/grid_coords.nc"
    ncwa -O -a time_counter "${TMP_DIR}/grid_coords.nc" "${TMP_DIR}/grid_coords.nc" 2>/dev/null || true
    ncwa -O -a deptht "${TMP_DIR}/grid_coords.nc" "${TMP_DIR}/grid_coords.nc" 2>/dev/null || true
    ncatted -O \
        -a coordinates,tmaskutil,c,c,"lon lat" \
        -a units,lon,c,c,"degrees_east" \
        -a units,lat,c,c,"degrees_north" \
        -a standard_name,lon,c,c,"longitude" \
        -a standard_name,lat,c,c,"latitude" \
        "${TMP_DIR}/grid_coords.nc"
    mv "${TMP_DIR}/grid_coords.nc" "${TARGET_GRID_NC}"
else
    echo "================================================================================" >&2
    echo "ERROR: Target domain files not found:" >&2
    echo "       DOMAIN_CFG: ${DOMAIN_CFG}" >&2
    echo "       MASKUTIL:   ${MASKUTIL}" >&2
    echo "" >&2
    echo "To generate initial conditions for target grid '${GRID_NAME}', please download" >&2
    echo "the official EC-Earth4 inidata package and set DOMAIN_BASE_DIR (or --domain-dir)" >&2
    echo "to your local directory containing ${GRID_NAME}/domain_cfg.nc." >&2
    echo "" >&2
    echo "For instructions on obtaining official EC-Earth4 inidata, refer to:" >&2
    echo "👉 https://ec-earth-4-docs.readthedocs.io/" >&2
    echo "================================================================================" >&2
    exit 1
fi

echo "Created target grid description NetCDF: ${TARGET_GRID_NC}"

# Extract text griddes for CDO
cdo griddes "${TARGET_GRID_NC}" > "${GRIDDES_TXT}"
echo "Dumped CDO griddes: ${GRIDDES_TXT}"

# Compute horizontal cell area
if [ -f "${DOMAIN_CFG}" ]; then
    echo "=== [2/3] Computing target horizontal cell areas (e1t * e2t) ==="
    cdo ${CDO_OPTS} ${CDO_COMPRESS} -expr,'area = e1t * e2t' -selname,e1t,e2t "${DOMAIN_CFG}" "${TARGET_AREA_NC}"
else
    echo "=== [2/3] Computing target horizontal cell areas via spherical gridarea ==="
    cdo ${CDO_OPTS} ${CDO_COMPRESS} gridarea "${TARGET_GRID_NC}" "${TARGET_AREA_NC}" 2>/dev/null || \
    cdo ${CDO_OPTS} ${CDO_COMPRESS} -setgrid,"${TARGET_GRID_NC}" -gridarea -topo,r360x180 "${TARGET_AREA_NC}"
fi
echo "Created target area file: ${TARGET_AREA_NC}"

# Precompute horizontal remapping weights
echo "=== [3/3] Precomputing CDO horizontal remapping weights ==="

# 1. Bilinear weights from regular 1x1 (r360x180) to target grid
WEIGHTS_BILIN_1DEG="${WEIGHTS_DIR}/weights_r360x180_to_${GRID_NAME}_bilin.nc"
if [ ! -f "${WEIGHTS_BILIN_1DEG}" ]; then
    echo "Generating bilinear weights (r360x180 -> ${GRID_NAME})..."
    cdo ${CDO_OPTS} genbil,"${TARGET_GRID_NC}" -topo,r360x180 "${WEIGHTS_BILIN_1DEG}"
    echo "Saved: ${WEIGHTS_BILIN_1DEG}"
else
    echo "Existing weights found: ${WEIGHTS_BILIN_1DEG}"
fi

# 2. Nearest-neighbor / distance-weighted weights (useful for masking or point sources)
WEIGHTS_DIS_1DEG="${WEIGHTS_DIR}/weights_r360x180_to_${GRID_NAME}_dis.nc"
if [ ! -f "${WEIGHTS_DIS_1DEG}" ]; then
    echo "Generating distance-weighted weights (r360x180 -> ${GRID_NAME})..."
    cdo ${CDO_OPTS} gendis,"${TARGET_GRID_NC}" -topo,r360x180 "${WEIGHTS_DIS_1DEG}"
    echo "Saved: ${WEIGHTS_DIS_1DEG}"
else
    echo "Existing weights found: ${WEIGHTS_DIS_1DEG}"
fi

# 3. SCRIP online weights file for NEMO runtime interpolation (if needed)
WEIGHTS_NEMO_ONLINE="${OUTPUT_DIR}/weights_3D_r360x180_bilin.nc"
if [ ! -f "${WEIGHTS_NEMO_ONLINE}" ]; then
    echo "Copying bilinear weights for NEMO online interpolation..."
    mkdir -p "${OUTPUT_DIR}"
    cp "${WEIGHTS_BILIN_1DEG}" "${WEIGHTS_NEMO_ONLINE}"
fi

echo "=== Grid and weights generation complete! ==="
