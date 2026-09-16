#!/usr/bin/env bash
# ==============================================================================
# prepare_sette_reference_orca2.sh
# Assembles the ground-truth SETTE reference datasets on the ORCA2 curvilinear grid.
# - Remaps 3D unmasked tracers (data_*_nomask.nc) to ORCA2 using bilinear weights
# - Symlinks/copies the native 2D and boundary forcing files directly
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export GRID_NAME="ORCA2"
source "${SCRIPT_DIR}/config.sh"

eval "${MODULE_LOAD_CMD}"

SETTE_REF_DIR="${SETTE_REF_DIR:-${GRID_DIR}/sette_reference}"
TARGET_GRID_NC="${WEIGHTS_DIR}/target_grid_ORCA2.nc"
WEIGHTS_BILIN="${WEIGHTS_DIR}/weights_r360x180_to_ORCA2_bilin.nc"

mkdir -p "${SETTE_REF_DIR}"

if [ ! -f "${TARGET_GRID_NC}" ] || [ ! -f "${WEIGHTS_BILIN}" ]; then
    echo "Target grid or weights missing. Running gen_grid_and_weights.sh first..."
    bash "${SCRIPT_DIR}/gen_grid_and_weights.sh"
fi

echo "========================================================================"
echo " Assembling SETTE Ground-Truth Reference on ORCA2"
echo " Destination: ${SETTE_REF_DIR}"
echo "========================================================================"

# 1. Remap 3D Tracers to ORCA2
remap_tracer() {
    local src="$1"
    local dst="$2"
    local var="${3:-}"
    if [ ! -f "${dst}" ]; then
        echo "Remapping ${src} -> $(basename "${dst}")..."
        if [ -n "${var}" ]; then
            cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" -selname,"${var}" "${src}" "${dst}"
        else
            cdo ${CDO_OPTS} ${CDO_COMPRESS} remap,"${TARGET_GRID_NC}","${WEIGHTS_BILIN}" "${src}" "${dst}"
        fi
    else
        echo "Already exists: $(basename "${dst}")"
    fi
}

remap_tracer "${RAW_DIR}/official_v5.0.0/data_NO3_nomask.nc" "${SETTE_REF_DIR}/data_NO3_ORCA2.nc" "NO3"
remap_tracer "${RAW_DIR}/official_v5.0.0/data_PO4_nomask.nc" "${SETTE_REF_DIR}/data_PO4_ORCA2.nc" "PO4"
remap_tracer "${RAW_DIR}/official_v5.0.0/data_SIL_nomask.nc" "${SETTE_REF_DIR}/data_Si_ORCA2.nc" "Si"
ln -sfn data_Si_ORCA2.nc "${SETTE_REF_DIR}/data_SIL_ORCA2.nc"

remap_tracer "${RAW_DIR}/official_v5.0.0/data_OXY_nomask.nc" "${SETTE_REF_DIR}/data_O2_ORCA2.nc" "O2"
ln -sfn data_O2_ORCA2.nc "${SETTE_REF_DIR}/data_OXY_ORCA2.nc"

remap_tracer "${RAW_DIR}/official_v5.0.0/data_ALK_nomask.nc" "${SETTE_REF_DIR}/data_TALK_ORCA2.nc" "TALK"
ln -sfn data_TALK_ORCA2.nc "${SETTE_REF_DIR}/data_ALK_ORCA2.nc"

remap_tracer "${RAW_DIR}/official_v5.0.0/data_DIC_nomask.nc" "${SETTE_REF_DIR}/data_TDIC_ORCA2.nc" "TDIC"
ln -sfn data_TDIC_ORCA2.nc "${SETTE_REF_DIR}/data_DIC_ORCA2.nc"

remap_tracer "${RAW_DIR}/official_v5.0.0/data_DIC_nomask.nc" "${SETTE_REF_DIR}/data_PiDIC_ORCA2.nc" "PiDIC"

remap_tracer "${RAW_DIR}/official_v5.0.0/data_DOC_nomask.nc" "${SETTE_REF_DIR}/data_DOC_ORCA2.nc" "DOC"
remap_tracer "${RAW_DIR}/official_v5.0.0/data_FER_nomask.nc" "${SETTE_REF_DIR}/data_Fer_ORCA2.nc" "Fer"

# 2. Copy/link native 2D and boundary forcings
echo "Linking native ORCA2 surface and boundary forcings..."
cp -f "${RAW_DIR}/official_v5.0.0/dust.orca.new.nc" "${SETTE_REF_DIR}/dust.orca.nc"
cp -f "${RAW_DIR}/official_v5.0.0/ndeposition.orca.nc" "${SETTE_REF_DIR}/ndeposition.orca.nc"
cp -f "${RAW_DIR}/official_v5.0.0/par.orca.nc" "${SETTE_REF_DIR}/par.orca.nc"
cp -f "${RAW_DIR}/official_v5.0.0/bathy.orca.nc" "${SETTE_REF_DIR}/bathy.orca.nc"
cp -f "${RAW_DIR}/official_v5.0.0/hydrofe.orca.nc" "${SETTE_REF_DIR}/hydrofe.orca.nc"
cp -f "${RAW_DIR}/official_v5.0.0/river.orca.nc" "${SETTE_REF_DIR}/river.orca.nc"

echo "========================================================================"
echo " SETTE Ground-Truth Reference Assembly on ORCA2 COMPLETE!"
echo " Total files in ${SETTE_REF_DIR}:"
ls -lh "${SETTE_REF_DIR}"
echo "========================================================================"
