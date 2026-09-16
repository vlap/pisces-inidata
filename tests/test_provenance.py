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
            preset="ece4",
            git_rev="test1234",
        )

        with nc.Dataset(tmp_path, "r") as ds:
            assert ds.title == "PISCES Initial Conditions (eORCA025)"
            assert ds.institution == "BSC"
            assert ds.source_pipeline == "pisces-inidata (git:test1234)"
            assert ds.inidata_preset == "ece4"
            assert hasattr(ds, "generation_date")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
