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
