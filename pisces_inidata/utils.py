"""
Utilities for NetCDF inspection, coordinate checking, and CDO execution.
"""

import os
import subprocess
from typing import List, Optional
import netCDF4 as nc
import numpy as np


def run_cmd(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Runs a system command with error checking."""
    print(f"[CMD] {' '.join(cmd)}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit code {res.returncode}):\n"
            f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}"
        )
    return res


def inspect_netcdf(nc_file: str) -> dict:
    """
    Returns summary metadata for a NetCDF file: dimensions, variables, shapes, coordinates.
    """
    if not os.path.exists(nc_file):
        raise FileNotFoundError(f"File not found: {nc_file}")

    info = {'dimensions': {}, 'variables': {}}
    with nc.Dataset(nc_file, 'r') as ds:
        for dname, dim in ds.dimensions.items():
            info['dimensions'][dname] = len(dim)
        for vname, var in ds.variables.items():
            info['variables'][vname] = {
                'dtype': str(var.dtype),
                'dimensions': var.dimensions,
                'shape': var.shape,
                'attrs': {k: str(var.getncattr(k)) for k in var.ncattrs()}
            }
    return info


def check_missing_in_ocean(nc_file: str, var_name: str, mask_file: Optional[str] = None) -> float:
    """
    Computes percentage of missing values in valid ocean cells.
    """
    with nc.Dataset(nc_file, 'r') as ds:
        if var_name not in ds.variables:
            raise KeyError(f"Variable {var_name} not found in {nc_file}")
        data = ds.variables[var_name][:]
        mask = np.ma.getmaskarray(data) if np.ma.is_masked(data) else np.isnan(data)
        missing_count = np.sum(mask)
        total_cells = data.size
        return (missing_count / total_cells) * 100.0 if total_cells > 0 else 0.0
