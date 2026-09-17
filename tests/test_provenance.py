"""
Tests for provenance stamping module.
"""

import os
import tempfile
import netCDF4 as nc
import numpy as np
from pisces_inidata.provenance import stamp_netcdf_provenance


def test_stamp_provenance():
    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as f:
        tmp_path = f.name

    try:
        with nc.Dataset(tmp_path, "w") as ds:
            ds.createDimension("x", 2)
            v = ds.createVariable("data", "f4", ("x",))
            v[:] = np.array([1.0, 2.0], dtype=np.float32)

        stamp_netcdf_provenance(
            tmp_path,
            grid_name="eORCA025",
            institution="BSC",
            pack="ece4",
            git_rev="test1234",
        )

        with nc.Dataset(tmp_path, "r") as ds:
            assert ds.title == "PISCES Initial Conditions (eORCA025)"
            assert ds.institution == "BSC"
            assert ds.source_pipeline == "pisces-inidata (git:test1234)"
            assert ds.inidata_pack == "ece4"
            assert ds.inidata_preset == "ece4"
            assert hasattr(ds, "generation_date")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_create_cf_coordinates():
    from pisces_inidata.provenance import create_cf_coordinates

    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as f:
        tmp_path = f.name

    try:
        with nc.Dataset(tmp_path, "w") as ds:
            lons = np.array([-180.0, 0.0, 180.0], dtype=np.float32)
            lats = np.array([-90.0, 0.0, 90.0], dtype=np.float32)
            depths = np.array([0.0, 100.0, 5000.0], dtype=np.float32)
            times = np.array([1.0, 2.0], dtype=np.float32)

            create_cf_coordinates(ds, lons, lats, depths, times)

            assert "lon" in ds.variables
            assert "lat" in ds.variables
            assert "depth" in ds.variables
            assert "time_counter" in ds.variables

            assert ds.variables["lon"].axis == "X"
            assert ds.variables["lat"].axis == "Y"
            assert ds.variables["depth"].axis == "Z"
            assert ds.variables["depth"].positive == "down"
            assert ds.variables["time_counter"].axis == "T"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
