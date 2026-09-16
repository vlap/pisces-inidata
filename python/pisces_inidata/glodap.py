"""
GLODAPv2 Climatology Preparation Module.
Sanitizes raw GLODAP NetCDF files by aligning the unstandardized 'depth_surface'
dimension and 'Depth' variable into a CF-compliant 'depth' coordinate with abyssal
padding to 6000m for seamless CDO vertical interpolation.
"""

import os
from pathlib import Path
from typing import Optional, Union
import netCDF4 as nc
import numpy as np


def resolve_glodap_source(
    param: str,
    raw_dir: Union[str, Path],
    version_hint: Optional[str] = None
) -> Path:
    """
    Locates the GLODAP NetCDF source file for a given parameter (e.g. TAlk, TCO2, PI_TCO2)
    using pathlib. Searches version-specific subdirectories first, then globs raw_dir.
    """
    raw_path = Path(raw_dir)
    ver = (version_hint or "v2.2016b").lower()

    # Preferred direct candidate paths based on requested version
    candidates = []
    if "2023" in ver:
        candidates.append(raw_path / "glodap_v2_2023" / f"GLODAPv2.2023.{param}.nc")
    elif "v1" in ver:
        candidates.append(raw_path / "glodap_v1" / f"glodap_v1.{param}.nc")
    else:
        candidates.append(raw_path / "glodap_v2" / f"GLODAPv2.2016b.{param}.nc")
        candidates.append(raw_path / "glodap_v2" / "GLODAPv2.2016b_MappedClimatologies" / f"GLODAPv2.2016b.{param}.nc")

    for cand in candidates:
        if cand.is_file():
            return cand

    # Fallback to directory scan
    search_dirs = [
        raw_path / "glodap_v2_2023",
        raw_path / "glodap_v2",
        raw_path / "glodap_v1",
        raw_path,
    ]
    for d in search_dirs:
        if d.is_dir():
            for f in sorted(d.rglob("*.nc")):
                if param.lower() in f.name.lower():
                    return f

    raise FileNotFoundError(f"Unable to find GLODAP source file for parameter '{param}' in {raw_dir}")


def prepare_glodap_tracer(src_path: str, var_name: str, out_path: str) -> None:
    """
    Reads raw GLODAP 3D variable, standardizes depth coordinate, and applies abyssal padding.
    """
    if not os.path.isfile(src_path):
        raise FileNotFoundError(f"GLODAP source file not found: {src_path}")

    with nc.Dataset(src_path, 'r') as src, nc.Dataset(out_path, 'w', format='NETCDF4') as dst:
        if var_name not in src.variables:
            raise KeyError(f"Variable '{var_name}' not found in {src_path}. Available: {list(src.variables.keys())}")

        depth_var_name = 'Depth' if 'Depth' in src.variables else 'depth'
        depths = np.array(src.variables[depth_var_name][:], dtype=np.float32)

        # Pad abyss to 6000m if required
        pad_bottom = False
        if depths[-1] < 6000.0:
            depths = np.append(depths, np.float32(6000.0))
            pad_bottom = True

        # Create dimensions
        dst.createDimension('depth', len(depths))
        dst.createDimension('lat', len(src.dimensions['lat']))
        dst.createDimension('lon', len(src.dimensions['lon']))

        # Create CF-compliant coordinate variables
        v_depth = dst.createVariable('depth', 'f4', ('depth',))
        v_depth.units = 'm'
        v_depth.positive = 'down'
        v_depth.axis = 'Z'
        v_depth.standard_name = 'depth'
        v_depth[:] = depths

        v_lat = dst.createVariable('lat', 'f4', ('lat',))
        v_lat.units = 'degrees_north'
        v_lat.standard_name = 'latitude'
        v_lat[:] = src.variables['lat'][:]

        v_lon = dst.createVariable('lon', 'f4', ('lon',))
        v_lon.units = 'degrees_east'
        v_lon.standard_name = 'longitude'
        v_lon[:] = src.variables['lon'][:]

        # Extract and copy data variable
        fill_val = getattr(src.variables[var_name], '_FillValue', -999.0)
        v_data = dst.createVariable(
            var_name, 'f4', ('depth', 'lat', 'lon'),
            fill_value=fill_val, zlib=True, complevel=4
        )
        for attr in ['long_name', 'units']:
            if hasattr(src.variables[var_name], attr):
                setattr(v_data, attr, getattr(src.variables[var_name], attr))

        data = src.variables[var_name][:]
        if pad_bottom:
            data = np.concatenate([data, data[-1:, :, :]], axis=0)
        v_data[:] = data

    print(f"Standardized GLODAP {var_name} saved to: {out_path}")
