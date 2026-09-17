"""
Stage 1 (Grid-Agnostic ETL): Source Dataset Standardization.
Pure Python module replacing scripts/prepare_standard_sources.sh using python-cdo and pynco.

Standardizes raw observational and reference datasets into uniform regular NetCDF source files:
  - Output: ${STANDARDIZED_DIR}/std_<VAR>.nc
  - Standard variable names (NO3, PO4, Alkalini, DIC, DOC, Fer, ...)
  - Continuous ocean coverage without gaps (fillmiss on source regular grid)
  - Standardized vertical coordinates extended to 6000m abyssal depth
  - CF-compliant coordinates (lon, lat, depth, time)

This stage has ZERO knowledge of target grids (eORCA1, eORCA025, ORCA2).
It runs once per dataset/preset and is cached across all target grids.
"""

import os
import shutil
import tempfile
from typing import Optional, List

import netCDF4 as nc
from pisces_inidata.nco_util import get_cdo
from pisces_inidata.catalog import resolve_source_field, resolve_package_dir
from pisces_inidata.padding import pad_abyssal_depth
from pisces_inidata.woa23 import process_tracer as process_woa23
from pisces_inidata.glodap import prepare_glodap_tracer
from pisces_inidata.doc import build_doc_climatology


TRACERS_3D = ["NO3", "PO4", "Si", "O2", "TALK", "TDIC", "PiDIC", "DOC", "Fer"]
FORCINGS_2D = ["dust", "ndep", "par", "bathy", "hydrofe", "river"]


def get_standardized_dir(
    out_dir: Optional[str] = None,
    pack: Optional[str] = None,
    preset: Optional[str] = None
) -> str:
    """Resolves output directory for standardized source NetCDFs."""
    if out_dir:
        return out_dir
    if os.environ.get("STANDARDIZED_DIR"):
        return os.environ["STANDARDIZED_DIR"]
    workspace = os.environ.get("PISCES_WORKSPACE")
    active_pack = pack or preset
    if workspace:
        sub = os.path.join("shared", "standardized", active_pack) if active_pack else "shared/standardized_sources"
        return os.path.join(workspace, sub)
    return os.path.join(os.getcwd(), "pisces_output", "standardized_sources")


def sanitize_source_coords(
    in_file: str,
    out_file: str,
    vars_list: List[str]
) -> str:
    """
    Sanitizes coordinate attributes for 2D/surface forcing files to ensure CF compliance.
    """
    if in_file != out_file:
        shutil.copyfile(in_file, out_file)

    with nc.Dataset(out_file, "r+") as ds:
        ds.setncattr("coordinates", "nav_lon nav_lat")
        for v in vars_list:
            if v in ds.variables:
                ds.variables[v].setncattr("coordinates", "nav_lon nav_lat")
        if "nav_lon" in ds.variables:
            ds.variables["nav_lon"].setncattr("units", "degrees_east")
            ds.variables["nav_lon"].setncattr("standard_name", "longitude")
        if "nav_lat" in ds.variables:
            ds.variables["nav_lat"].setncattr("units", "degrees_north")
            ds.variables["nav_lat"].setncattr("standard_name", "latitude")
        for c_depth in ("deptht", "depth", "nav_lev"):
            if c_depth in ds.variables:
                ds.variables[c_depth].setncattr("units", "m")
                ds.variables[c_depth].setncattr("positive", "down")
                ds.variables[c_depth].setncattr("axis", "Z")
                ds.variables[c_depth].setncattr("standard_name", "depth")
    return out_file


def standardize_source(
    var_name: str,
    pack: str = "ece4",
    preset: Optional[str] = None,
    force: bool = False,
    raw_dir: Optional[str] = None,
    out_dir: Optional[str] = None
) -> str:
    """
    Standardizes raw input dataset for var_name into a CF-compliant regular NetCDF file.
    Returns the absolute path to std_<VAR>.nc.
    """
    active_pack = preset if preset else pack
    std_dir = get_standardized_dir(out_dir, pack=active_pack)
    os.makedirs(std_dir, exist_ok=True)
    std_file = os.path.join(std_dir, f"std_{var_name}.nc")

    if not force and os.path.isfile(std_file) and os.path.getsize(std_file) > 0:
        print(f"[Stage 1 Cache] Standardized source for {var_name} already exists: {std_file}")
        return std_file

    print("========================================================================")
    print(f" Stage 1 [ETL]: Standardizing Source for: {var_name} (pack={active_pack})")
    print(f" Target Output: {std_file}")
    print("========================================================================")

    cdo = get_cdo()
    meta = resolve_source_field(var_name, pack=active_pack, raw_dir=raw_dir)

    handler = meta.get("handler")
    src_var = meta.get("src_var", var_name)
    std_var = meta.get("std_var", var_name)
    src_file = meta.get("src_file")
    pad_depth = meta.get("pad_depth")

    with tempfile.TemporaryDirectory(prefix=f"tmp_etl_{var_name}_") as tmp_dir:
        try:
            if handler == "woa23":
                woa_dir = src_file or (os.path.join(raw_dir, "woa23") if raw_dir else resolve_package_dir("woa23"))
                tmp_combined = os.path.join(tmp_dir, f"woa_combined_{var_name}.nc")
                print(f"Combining monthly WOA23 files for {var_name} from {woa_dir}...", flush=True)
                process_woa23(src_var, woa_dir, tmp_combined)
                print(f"Filling missing values (cdo fillmiss) for {var_name}...", flush=True)
                cdo.fillmiss(input=tmp_combined, output=std_file)

            elif handler == "glodap":
                if not src_file or not os.path.isfile(src_file):
                    raise FileNotFoundError(f"GLODAP source file not found: {src_file}")
                tmp_prep = os.path.join(tmp_dir, f"glodap_prep_{var_name}.nc")
                tmp_filled = os.path.join(tmp_dir, f"glodap_filled_{var_name}.nc")
                print(f"Standardizing GLODAP for {var_name} from {src_file}...")
                prepare_glodap_tracer(src_file, src_var, tmp_prep)
                print(f"Filling missing values (cdo fillmiss) for {var_name}...")
                cdo.fillmiss(input=tmp_prep, output=tmp_filled)
                if src_var != std_var:
                    with nc.Dataset(tmp_filled, "r+") as ds:
                        if src_var in ds.variables:
                            ds.renameVariable(src_var, std_var)
                shutil.copyfile(tmp_filled, std_file)

            elif handler == "doc":
                if not src_file or not os.path.isfile(src_file):
                    print("Building Panaïotis et al. (2024) DOC NetCDF from raw CSVs...")
                    raw_base = raw_dir or ""
                    doc_raw = os.path.dirname(src_file) if src_file else os.path.join(raw_base, "panaiotis2024_doc")
                    tmp_doc_prep = os.path.join(tmp_dir, "doc_prep.nc")
                    build_doc_climatology(doc_raw, tmp_doc_prep)
                    src_file = tmp_doc_prep

                tmp_doc_filled = os.path.join(tmp_dir, "doc_filled.nc")
                print("Filling missing values for DOC (cdo fillmiss)...")
                cdo.fillmiss(input=src_file, output=tmp_doc_filled)
                effective_pad = float(pad_depth or 6000.0)
                print(f"Extending abyssal depth to {effective_pad}m...")
                pad_abyssal_depth(tmp_doc_filled, std_file, target_bottom_depth=effective_pad)

            elif handler == "forcing":
                if not src_file or not os.path.isfile(src_file):
                    raise FileNotFoundError(f"Boundary forcing source file not found: {src_file}")
                tmp_work = os.path.join(tmp_dir, f"{var_name}_work.nc")
                shutil.copyfile(src_file, tmp_work)

                coords_file = meta.get("coords_source_file")
                if coords_file and os.path.isfile(coords_file):
                    print(f"Appending coordinates from donor: {coords_file}...")
                    with nc.Dataset(coords_file, "r") as src_ds, nc.Dataset(tmp_work, "r+") as dst_ds:
                        for cvar in ["nav_lon", "nav_lat"]:
                            if cvar in src_ds.variables and cvar not in dst_ds.variables:
                                svar = src_ds.variables[cvar]
                                for dname in svar.dimensions:
                                    if dname not in dst_ds.dimensions:
                                        dst_ds.createDimension(dname, src_ds.dimensions[dname].size)
                                dvar = dst_ds.createVariable(cvar, svar.dtype, svar.dimensions)
                                for attr in svar.ncattrs():
                                    dvar.setncattr(attr, svar.getncattr(attr))
                                dvar[:] = svar[:]

                vars_list = meta.get("vars_list", [src_var])
                sanitize_source_coords(tmp_work, std_file, vars_list)

            else:
                # Generic 3D tracer source (e.g. sette_nomask, woa2009, or custom)
                if not src_file or not os.path.isfile(src_file):
                    raise FileNotFoundError(f"Source file not found: {src_file}. Run download first.")
                tmp_sel = os.path.join(tmp_dir, f"src_sel_{var_name}.nc")
                tmp_padded = os.path.join(tmp_dir, f"padded_{var_name}.nc")
                print(f"Extracting {src_var} from {src_file}...")
                cdo.selname(src_var, input=src_file, output=tmp_sel)

                if pad_depth:
                    print(f"Padding abyssal depth to {pad_depth}m...")
                    pad_abyssal_depth(tmp_sel, tmp_padded, target_bottom_depth=float(pad_depth))
                else:
                    tmp_padded = tmp_sel

                if src_var != std_var:
                    with nc.Dataset(tmp_padded, "r+") as ds:
                        if src_var in ds.variables:
                            ds.renameVariable(src_var, std_var)

                shutil.copyfile(tmp_padded, std_file)

        except Exception as err:
            print(f"ERROR: Failed during Stage 1 standardization of '{var_name}': {err}")
            raise

    print(f"Successfully standardized: {std_file}")
    return std_file


def standardize_all_sources(
    pack: str = "ece4",
    preset: Optional[str] = None,
    force: bool = False,
    raw_dir: Optional[str] = None,
    out_dir: Optional[str] = None
) -> List[str]:
    """
    Standardizes all 3D tracers and 2D surface boundary forcings.
    Returns list of paths to standardized files.
    """
    active_pack = preset if preset else pack
    std_files = []
    for tracer in TRACERS_3D:
        std_files.append(standardize_source(tracer, pack=active_pack, force=force, raw_dir=raw_dir, out_dir=out_dir))
    for forcing in FORCINGS_2D:
        std_files.append(standardize_source(forcing, pack=active_pack, force=force, raw_dir=raw_dir, out_dir=out_dir))
    return std_files
