"""
SETTE Ground-Truth Reference Assembly on ORCA2.
Pure Python module replacing scripts/prepare_sette_reference_orca2.sh using python-cdo and pynco.

Assembles the ground-truth SETTE reference datasets on the ORCA2 curvilinear grid:
  - Remaps 3D unmasked tracers (data_*_nomask.nc) to ORCA2 using bilinear weights
  - Copies native 2D and boundary forcing files directly
"""

import os
import shutil
from typing import Optional, List, Tuple

from pisces_inidata.nco_util import get_cdo
from pisces_inidata.catalog import resolve_package_dir
from pisces_inidata.weights import ensure_grid_and_weights
from pisces_inidata.remap import get_weights_dir


TRACER_MAP: List[Tuple[str, str, str, Optional[str]]] = [
    ("data_NO3_nomask.nc", "data_NO3_ORCA2.nc", "NO3", None),
    ("data_PO4_nomask.nc", "data_PO4_ORCA2.nc", "PO4", None),
    ("data_SIL_nomask.nc", "data_Si_ORCA2.nc", "Si", "data_SIL_ORCA2.nc"),
    ("data_OXY_nomask.nc", "data_O2_ORCA2.nc", "O2", "data_OXY_ORCA2.nc"),
    ("data_ALK_nomask.nc", "data_TALK_ORCA2.nc", "TALK", "data_ALK_ORCA2.nc"),
    ("data_DIC_nomask.nc", "data_TDIC_ORCA2.nc", "TDIC", "data_DIC_ORCA2.nc"),
    ("data_DIC_nomask.nc", "data_PiDIC_ORCA2.nc", "PiDIC", None),
    ("data_DOC_nomask.nc", "data_DOC_ORCA2.nc", "DOC", None),
    ("data_FER_nomask.nc", "data_Fer_ORCA2.nc", "Fer", None),
]

NATIVE_FORCINGS: List[Tuple[str, str]] = [
    ("dust.orca.new.nc", "dust.orca.nc"),
    ("ndeposition.orca.nc", "ndeposition.orca.nc"),
    ("par.orca.nc", "par.orca.nc"),
    ("bathy.orca.nc", "bathy.orca.nc"),
    ("hydrofe.orca.nc", "hydrofe.orca.nc"),
    ("river.orca.nc", "river.orca.nc"),
]


def assemble_sette_reference_orca2(
    raw_dir: Optional[str] = None,
    out_dir: Optional[str] = None,
    weights_dir: Optional[str] = None,
    force: bool = False,
) -> str:
    """
    Assembles SETTE reference dataset in out_dir.
    Returns path to reference directory.
    """
    workspace = os.environ.get("PISCES_WORKSPACE")
    effective_out_dir = out_dir or (
        os.path.join(workspace, "shared", "production", "ORCA2", "sette_reference")
        if workspace
        else os.path.join(os.getcwd(), "pisces_output", "ORCA2", "sette_reference")
    )
    os.makedirs(effective_out_dir, exist_ok=True)

    official_dir = resolve_package_dir("official_nemo_inputs", raw_dir=raw_dir)
    if not os.path.isdir(official_dir):
        raise FileNotFoundError(
            f"Official NEMO inputs directory not found at: {official_dir}\n"
            f"Please run 'pisces-inidata download official' or set RAW_DIR."
        )

    effective_weights_dir = get_weights_dir(weights_dir)
    print("========================================================================")
    print(" Assembling SETTE Ground-Truth Reference on ORCA2")
    print(f" Source Inputs: {official_dir}")
    print(f" Destination:   {effective_out_dir}")
    print("========================================================================")

    # 1. Ensure ORCA2 grid coordinates and bilinear weights exist
    w_info = ensure_grid_and_weights(
        grid_name="ORCA2",
        weights_dir=effective_weights_dir,
        raw_dir=raw_dir,
        force=False,
    )
    target_grid_nc = w_info["target_grid_nc"]
    weights_bilin = w_info["weights_bilin_nc"]

    cdo = get_cdo()
    cdo_opts = "-s -f nc4c -z zip_4"

    # 2. Remap 3D tracers to ORCA2
    for src_file, out_file, var_name, alias_sym in TRACER_MAP:
        src_path = os.path.join(official_dir, src_file)
        dst_path = os.path.join(effective_out_dir, out_file)

        if not os.path.isfile(src_path):
            print(f"Warning: Reference file {src_file} not found in {official_dir}. Skipping.")
            continue

        if not force and os.path.isfile(dst_path) and os.path.getsize(dst_path) > 0:
            print(f"Reference tracer already exists: {out_file}")
        else:
            print(f"Remapping {src_file} ({var_name}) -> {out_file}...")
            cdo.remap(
                f"{target_grid_nc},{weights_bilin}",
                input=f"-selname,{var_name} {src_path}",
                output=dst_path,
                options=cdo_opts,
            )

        if alias_sym:
            sym_path = os.path.join(effective_out_dir, alias_sym)
            if os.path.lexists(sym_path):
                os.remove(sym_path)
            os.symlink(os.path.basename(dst_path), sym_path)

    # 3. Copy native 2D and boundary forcings
    print("Copying native ORCA2 surface and boundary forcings...")
    for src_cand, dst_name in NATIVE_FORCINGS:
        dst_path = os.path.join(effective_out_dir, dst_name)
        cand_path = os.path.join(official_dir, src_cand)
        if not os.path.isfile(cand_path):
            cand_path = os.path.join(official_dir, dst_name)

        if os.path.isfile(cand_path):
            shutil.copyfile(cand_path, dst_path)
            print(f"Copied native forcing: {dst_name}")
        else:
            print(f"Warning: Native forcing {src_cand} not found in {official_dir}.")

    print("========================================================================")
    print(" SETTE Ground-Truth Reference Assembly on ORCA2 COMPLETE!")
    print(f" Files written to: {effective_out_dir}")
    print("========================================================================")
    return effective_out_dir
