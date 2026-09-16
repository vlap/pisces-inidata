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

# 1. Remap 3D Tracers to ORCA2
# Format: "source_file:output_file:var_name[:alias_symlink]"
TRACER_MAP=(
    "data_NO3_nomask.nc:data_NO3_ORCA2.nc:NO3:"
    "data_PO4_nomask.nc:data_PO4_ORCA2.nc:PO4:"
    "data_SIL_nomask.nc:data_Si_ORCA2.nc:Si:data_SIL_ORCA2.nc"
    "data_OXY_nomask.nc:data_O2_ORCA2.nc:O2:data_OXY_ORCA2.nc"
    "data_ALK_nomask.nc:data_TALK_ORCA2.nc:TALK:data_ALK_ORCA2.nc"
    "data_DIC_nomask.nc:data_TDIC_ORCA2.nc:TDIC:data_DIC_ORCA2.nc"
    "data_DIC_nomask.nc:data_PiDIC_ORCA2.nc:PiDIC:"
    "data_DOC_nomask.nc:data_DOC_ORCA2.nc:DOC:"
    "data_FER_nomask.nc:data_Fer_ORCA2.nc:Fer:"
)

for entry in "${TRACER_MAP[@]}"; do
    IFS=':' read -r src_file out_file var_name symlink <<< "${entry}"
    remap_tracer "${RAW_DIR}/official_v5.0.0/${src_file}" "${SETTE_REF_DIR}/${out_file}" "${var_name}"
    if [ -n "${symlink}" ]; then
        ln -sfn "${out_file}" "${SETTE_REF_DIR}/${symlink}"
    fi
done

# 2. Copy/link native 2D and boundary forcings
echo "Linking native ORCA2 surface and boundary forcings..."
NATIVE_FORCINGS=(
    "dust.orca.new.nc:dust.orca.nc"
    "ndeposition.orca.nc:ndeposition.orca.nc"
    "par.orca.nc:par.orca.nc"
    "bathy.orca.nc:bathy.orca.nc"
    "hydrofe.orca.nc:hydrofe.orca.nc"
    "river.orca.nc:river.orca.nc"
)
for entry in "${NATIVE_FORCINGS[@]}"; do
    IFS=':' read -r src dst <<< "${entry}"
    cp -f "${RAW_DIR}/official_v5.0.0/${src}" "${SETTE_REF_DIR}/${dst}"
done

echo "========================================================================"
echo " SETTE Ground-Truth Reference Assembly on ORCA2 COMPLETE!"
echo " Total files in ${SETTE_REF_DIR}:"
ls -lh "${SETTE_REF_DIR}"
echo "========================================================================"
