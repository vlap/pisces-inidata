"""
Stage 2 (Target-Centric Remapping): Universal, format-agnostic interpolation driver.
Pure Python module replacing scripts/remap_field.sh using python-cdo and pynco.

Takes clean NetCDF from ${STANDARDIZED_DIR}/std_<VAR>.nc and executes:
  - 3D: Streamed vertical level interpolation (-intlevel) + Horizontal remapping (remap)
  - 2D: Horizontal remapping (genbil + remap)
  - Bathy: Nearest-neighbor remapping (remapnn)
  - Hydrofe: Horizontal remapping (remap)
  - Rivers: Distance-weighted conservative remapping (remapdis)

This module has ZERO dataset-specific branching (e.g. no WOA vs GLODAP logic).
It operates strictly on standardized NetCDF files.
"""

import os
import shutil
from typing import Optional, List
import numpy as np
import netCDF4 as nc

from pisces_inidata.nco_util import get_cdo
from pisces_inidata.catalog import (
    resolve_target_field,
    get_target_vertical_levels,
)
from pisces_inidata.weights import ensure_grid_and_weights
from pisces_inidata.etl import standardize_source, get_standardized_dir, TRACERS_3D, FORCINGS_2D
from pisces_inidata.provenance import stamp_netcdf_provenance


def get_output_dir(grid_name: str, out_dir: Optional[str] = None) -> str:
    """Resolves output directory for target grid NetCDFs."""
    if out_dir:
        return out_dir
    if os.environ.get("OUTPUT_DIR"):
        return os.environ["OUTPUT_DIR"]
    workspace = os.environ.get("PISCES_WORKSPACE")
    if workspace:
        return os.path.join(workspace, "grids", grid_name, "inidata")
    return os.path.join(os.getcwd(), "pisces_output", grid_name, "inidata")


def get_weights_dir(grid_name: Optional[str] = None, weights_dir: Optional[str] = None) -> str:
    """Resolves directory for grid coordinates and remapping weights."""
    if weights_dir:
        return weights_dir
    if os.environ.get("WEIGHTS_DIR"):
        return os.environ["WEIGHTS_DIR"]
    workspace = os.environ.get("PISCES_WORKSPACE")
    if workspace:
        if grid_name:
            return os.path.join(workspace, "grids", grid_name, "weights")
        return os.path.join(workspace, "shared", "weights")
    return os.path.join(os.getcwd(), "pisces_output", "weights")


def resolve_field_type(var_name: str, field_type: str = "auto") -> str:
    """Classifies variable into interpolation category."""
    if field_type != "auto":
        return field_type

    if var_name in ("NO3", "PO4", "Si", "O2", "TALK", "TDIC", "PiDIC", "DOC", "Fer"):
        return "3d"
    elif var_name in ("dust", "ndep", "par"):
        return "2d"
    elif var_name == "bathy":
        return "bathy"
    elif var_name == "hydrofe":
        return "hydrofe"
    elif var_name in ("river", "rivers"):
        return "river"
    return "3d"


def is_same_grid(src_nc: str, tgt_nc: str) -> bool:
    """
    Checks whether the source NetCDF horizontal grid dimensions match target grid.
    Uses CDO griddes to parse xsize and ysize across any grid format.
    """
    try:
        cdo = get_cdo()
        src_grid = cdo.griddes(input=src_nc)
        tgt_grid = cdo.griddes(input=tgt_nc)

        def parse_xy(lines):
            x, y = None, None
            for line in lines:
                if "xsize" in line:
                    parts = line.split("=")
                    if len(parts) > 1:
                        x = parts[1].strip()
                elif "ysize" in line:
                    parts = line.split("=")
                    if len(parts) > 1:
                        y = parts[1].strip()
            return x, y

        sx, sy = parse_xy(src_grid)
        tx, ty = parse_xy(tgt_grid)
        return bool(sx and sy and sx == tx and sy == ty)
    except Exception:
        return False


def clamp_file_non_negative(file_path: str, var_names: Optional[List[str]] = None) -> None:
    """
    Enforces physical non-negativity (C >= 0.0) on data arrays while strictly
    preserving NetCDF masks and _FillValue attributes.
    """
    if not os.path.isfile(file_path):
        return

    with nc.Dataset(file_path, "r+") as ds:
        targets = var_names if var_names else list(ds.variables.keys())
        for v in targets:
            if v in ds.variables:
                # Skip spatial coordinates and dimensions
                if v in ("nav_lon", "nav_lat", "lon", "lat", "depth", "nav_lev", "time_counter", "time", "x", "y"):
                    continue
                var_obj = ds.variables[v]
                data = var_obj[:]
                if np.ma.is_masked(data):
                    mask = np.ma.getmaskarray(data)
                    raw_data = data.data
                    neg = (raw_data < 0.0) & (~mask)
                    if np.any(neg):
                        raw_data[neg] = 0.0
                        var_obj[:] = np.ma.masked_array(raw_data, mask=mask)
                else:
                    neg = (data < 0.0) & (~np.isnan(data))
                    if np.any(neg):
                        data[neg] = 0.0
                        var_obj[:] = data


def remap_field(
    var_name: str,
    grid_name: str,
    pack: str = "ece4",
    preset: Optional[str] = None,
    convention: str = "nemo4_ece4",
    field_type: str = "auto",
    force: bool = False,
    domain_dir: Optional[str] = None,
    weights_dir: Optional[str] = None,
    std_dir: Optional[str] = None,
    out_dir: Optional[str] = None,
    raw_dir: Optional[str] = None,
    threads: Optional[int] = None,
) -> str:
    """
    Interpolates standardized source variable to target grid coordinates.
    Creates namelist compatibility symlinks and stamps CF provenance metadata.
    Returns path to the produced NetCDF file.
    """
    active_pack = preset if preset else pack
    effective_weights_dir = get_weights_dir(grid_name=grid_name, weights_dir=weights_dir)
    effective_out_dir = get_output_dir(grid_name, out_dir)
    effective_std_dir = get_standardized_dir(std_dir)
    os.makedirs(effective_out_dir, exist_ok=True)
    os.makedirs(effective_weights_dir, exist_ok=True)

    ftype = resolve_field_type(var_name, field_type)
    target_meta = resolve_target_field(var_name, grid_name, convention=convention)
    out_filename = target_meta["out_file"]
    final_out_file = os.path.join(effective_out_dir, out_filename)

    if not force and os.path.isfile(final_out_file) and os.path.getsize(final_out_file) > 0:
        print(f"[Stage 2 Cache] Remapped target file already exists: {final_out_file}")
        return final_out_file

    print("========================================================================")
    print(f" Stage 2 [Remap]: Mapping {var_name} ({ftype}) to {grid_name}")
    print(f" Target Output: {final_out_file}")
    print("========================================================================")

    # 1. Ensure target grid coordinates and default bilinear weights exist
    weights_info = ensure_grid_and_weights(
        grid_name=grid_name,
        domain_dir=domain_dir,
        weights_dir=effective_weights_dir,
        raw_dir=raw_dir,
        force=False,
    )
    target_grid_nc = weights_info.get("target_grid_nc") or weights_info["target_grid"]
    weights_bilin = weights_info.get("weights_bilin_nc") or weights_info["weights_bilin"]

    # 2. Ensure standardized source file exists (invoke Stage 1 ETL on-demand if missing)
    std_file = os.path.join(effective_std_dir, f"std_{var_name}.nc")
    if not os.path.isfile(std_file) or os.path.getsize(std_file) == 0:
        print(f"Standardized source not found: {std_file}. Invoking Stage 1 ETL on demand...")
        std_file = standardize_source(
            var_name=var_name,
            pack=active_pack,
            raw_dir=raw_dir,
            out_dir=effective_std_dir,
            force=False,
        )

    # 3. Configure CDO
    cdo = get_cdo(threads=threads)
    cdo_opts = "-s -f nc4c -z zip_4"

    try:
        if ftype == "3d":
            # Extract target vertical levels from domain_cfg or catalog fallback
            target_levels = get_target_vertical_levels(
                grid_name=grid_name,
                domain_dir=domain_dir,
                raw_dir=raw_dir,
            )

            if target_levels:
                print(f"Streamed vertical interpolation (intlevel) + horizontal remap to {grid_name}...")
                cdo.remap(
                    f"{target_grid_nc},{weights_bilin}",
                    input=f"-intlevel,{target_levels} {std_file}",
                    output=final_out_file,
                    options=cdo_opts,
                )
            else:
                print(f"Horizontal remapping 3D field to {grid_name} (no vertical levels specified)...")
                cdo.remap(
                    f"{target_grid_nc},{weights_bilin}",
                    input=std_file,
                    output=final_out_file,
                    options=cdo_opts,
                )

        elif ftype == "2d":
            # 2D Surface Forcings (dust, ndep, par)
            if is_same_grid(std_file, target_grid_nc):
                print(f"Source {var_name} grid matches target {grid_name}; copying directly...")
                shutil.copyfile(std_file, final_out_file)
            else:
                weights_file = os.path.join(effective_weights_dir, f"weights_{var_name}_to_{grid_name}.nc")
                if not os.path.isfile(weights_file) or os.path.getsize(weights_file) == 0:
                    print(f"Generating field-specific weights for {var_name}...")
                    cdo.genbil(target_grid_nc, input=std_file, output=weights_file, options=cdo_opts)

                print(f"Remapping 2D surface forcing {var_name} to {grid_name}...")
                cdo.remap(
                    f"{target_grid_nc},{weights_file}",
                    input=std_file,
                    output=final_out_file,
                    options=cdo_opts,
                )

        elif ftype == "bathy":
            if is_same_grid(std_file, target_grid_nc):
                print(f"Source bathy grid matches target {grid_name}; copying directly without re-interpolation...")
                shutil.copyfile(std_file, final_out_file)
            else:
                print("Remapping bathymetric shelf fraction using nearest-neighbor (remapnn)...")
                cdo.remapnn(
                    target_grid_nc,
                    input=std_file,
                    output=final_out_file,
                    options=cdo_opts,
                )

        elif ftype == "hydrofe":
            if is_same_grid(std_file, target_grid_nc):
                print(f"Source hydrofe grid matches target {grid_name}; copying directly without re-interpolation...")
                shutil.copyfile(std_file, final_out_file)
            else:
                src_grid = cdo.griddes(input=std_file)
                sx, sy = None, None
                for line in src_grid:
                    if "xsize" in line:
                        sx = line.split("=")[1].strip()
                    elif "ysize" in line:
                        sy = line.split("=")[1].strip()
                if sx == "360" and sy == "180":
                    use_weights = weights_bilin
                else:
                    use_weights = os.path.join(effective_weights_dir, f"weights_hydrofe_to_{grid_name}.nc")
                    if not os.path.isfile(use_weights) or os.path.getsize(use_weights) == 0:
                        cdo.genbil(target_grid_nc, input=std_file, output=use_weights, options=cdo_opts)
                print(f"Remapping hydrothermal iron to {grid_name}...")
                cdo.remap(
                    f"{target_grid_nc},{use_weights}",
                    input=std_file,
                    output=final_out_file,
                    options=cdo_opts,
                )

        elif ftype in ("river", "rivers"):
            if is_same_grid(std_file, target_grid_nc):
                print(f"Source river grid matches target {grid_name}; copying directly without re-interpolation...")
                shutil.copyfile(std_file, final_out_file)
            else:
                print("Remapping river nutrient discharge using distance-weighted (remapdis)...")
                cdo.remapdis(
                    target_grid_nc,
                    input=std_file,
                    output=final_out_file,
                    options=cdo_opts,
                )

        else:
            raise ValueError(f"Unknown field type: '{ftype}'. Choose: 3d | 2d | bathy | hydrofe | river")

    except Exception as err:
        print(f"ERROR: Remapping failed for variable '{var_name}' on grid '{grid_name}': {err}")
        raise

    # 4. Enforce physical non-negativity constraint (C >= 0.0)
    clamp_file_non_negative(final_out_file)

    # 5. Create namelist symlinks defined in catalog
    symlinks = target_meta.get("symlinks", [])
    for sym in symlinks:
        sym_path = os.path.join(effective_out_dir, sym)
        if os.path.lexists(sym_path):
            try:
                os.remove(sym_path)
            except OSError:
                pass
        rel_target = os.path.basename(final_out_file)
        os.symlink(rel_target, sym_path)
        print(f"Created namelist symlink: {sym} -> {rel_target}")

    # 5. Stamp provenance metadata
    stamp_netcdf_provenance(final_out_file, grid_name=grid_name, pack=active_pack)
    print(f"Successfully remapped: {final_out_file}")
    return final_out_file


def remap_all_fields(
    grid_name: str,
    pack: str = "ece4",
    preset: Optional[str] = None,
    convention: str = "nemo4_ece4",
    force: bool = False,
    domain_dir: Optional[str] = None,
    weights_dir: Optional[str] = None,
    std_dir: Optional[str] = None,
    out_dir: Optional[str] = None,
    raw_dir: Optional[str] = None,
    threads: Optional[int] = None,
) -> List[str]:
    """
    Sequentially remaps all 3D tracers and 2D surface boundary forcings.
    Returns list of paths to produced target NetCDFs.
    """
    active_pack = preset if preset else pack
    remapped = []
    for tracer in TRACERS_3D:
        remapped.append(
            remap_field(
                var_name=tracer,
                grid_name=grid_name,
                pack=active_pack,
                convention=convention,
                field_type="3d",
                force=force,
                domain_dir=domain_dir,
                weights_dir=weights_dir,
                std_dir=std_dir,
                out_dir=out_dir,
                raw_dir=raw_dir,
                threads=threads,
            )
        )

    for forcing in FORCINGS_2D:
        remapped.append(
            remap_field(
                var_name=forcing,
                grid_name=grid_name,
                pack=active_pack,
                convention=convention,
                field_type="auto",
                force=force,
                domain_dir=domain_dir,
                weights_dir=weights_dir,
                std_dir=std_dir,
                out_dir=out_dir,
                raw_dir=raw_dir,
                threads=threads,
            )
        )

    return remapped
