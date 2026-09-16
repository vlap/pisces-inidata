"""
Scientific Provenance & CF Metadata Stamping Module for PISCES Inidata.
Applies CF-compliant global attributes to generated NetCDF initial conditions.
Uses netCDF4 directly in-place without requiring external binary tools.
"""

import os
import subprocess
from datetime import datetime, timezone
from typing import Optional
import netCDF4 as nc
import numpy as np


def create_cf_coordinates(
    ds: nc.Dataset,
    lons: np.ndarray,
    lats: np.ndarray,
    depths: Optional[np.ndarray] = None,
    times: Optional[np.ndarray] = None,
    time_units: str = "months since 0001-01-01 00:00:00",
    calendar: str = "noleap",
) -> None:
    """
    Creates standard CF-compliant lon, lat, depth, and time_counter coordinate dimensions
    and variables with appropriate CF attributes on a NetCDF dataset.
    """
    if 'lon' not in ds.dimensions:
        ds.createDimension('lon', len(lons))
    if 'lat' not in ds.dimensions:
        ds.createDimension('lat', len(lats))

    v_lon = ds.createVariable('lon', 'f4', ('lon',))
    v_lon.units = "degrees_east"
    v_lon.long_name = "Longitude"
    v_lon.standard_name = "longitude"
    v_lon.axis = "X"
    v_lon[:] = lons

    v_lat = ds.createVariable('lat', 'f4', ('lat',))
    v_lat.units = "degrees_north"
    v_lat.long_name = "Latitude"
    v_lat.standard_name = "latitude"
    v_lat.axis = "Y"
    v_lat[:] = lats

    if depths is not None:
        if 'depth' not in ds.dimensions:
            ds.createDimension('depth', len(depths))
        v_depth = ds.createVariable('depth', 'f4', ('depth',))
        v_depth.units = "m"
        v_depth.long_name = "Depth"
        v_depth.standard_name = "depth"
        v_depth.positive = "down"
        v_depth.axis = "Z"
        v_depth[:] = depths

    if times is not None:
        if 'time_counter' not in ds.dimensions:
            ds.createDimension('time_counter', len(times))
        v_time = ds.createVariable('time_counter', 'f8', ('time_counter',))
        v_time.units = time_units
        v_time.long_name = "Time"
        v_time.calendar = calendar
        v_time.axis = "T"
        v_time[:] = times


def stamp_netcdf_provenance(
    target_file: str,
    grid_name: Optional[str] = None,
    institution: Optional[str] = None,
    preset: Optional[str] = None,
    git_rev: Optional[str] = None,
) -> None:
    """
    Applies standardized CF global attributes directly to a NetCDF file.
    """
    if not os.path.isfile(target_file):
        raise FileNotFoundError(f"File to stamp not found: {target_file}")

    grid = grid_name or os.environ.get("GRID_NAME", "eORCA1")
    inst = institution or os.environ.get("PISCES_INSTITUTION", "EC-Earth Consortium")
    p_name = preset or os.environ.get("INIDATA_PRESET", os.environ.get("PRESET", "custom"))
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not git_rev:
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            res = subprocess.run(
                ["git", "-C", repo_root, "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            git_rev = res.stdout.strip() if res.returncode == 0 and res.stdout.strip() else "release"
        except Exception:
            git_rev = "release"

    with nc.Dataset(target_file, "r+") as ds:
        ds.title = f"PISCES Initial Conditions ({grid})"
        ds.institution = inst
        ds.source_pipeline = f"pisces-inidata (git:{git_rev})"
        ds.inidata_preset = p_name
        ds.generation_date = timestamp
