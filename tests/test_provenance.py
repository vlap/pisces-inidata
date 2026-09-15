"""
Tests for scientific provenance stamping in pisces_inidata.utils.
"""

import os
import tempfile
import netCDF4 as nc
from pisces_inidata.utils import stamp_provenance_metadata


def test_stamp_provenance_metadata():
    with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as tmp:
        path = tmp.name

    try:
        # Create minimal test dataset
        with nc.Dataset(path, 'w') as ds:
            ds.createDimension('dim1', 2)
            v = ds.createVariable('var1', 'f4', ('dim1',))
            v[:] = [1.0, 2.0]

        # Apply provenance stamping
        stamp_provenance_metadata(
            path,
            grid_name="eORCA1",
            product_summary="NO3:woa23, TALK:glodap_v2_2016b",
            git_commit="test_commit_123"
        )

        with nc.Dataset(path, 'r') as ds:
            assert "PISCES Biogeochemical Initial Conditions for NEMO/EC-Earth4 (eORCA1)" in ds.title
            assert ds.institution == "Barcelona Supercomputing Center (BSC), EC-Earth Consortium"
            assert "pisces-inidata" in ds.source_pipeline
            assert ds.source_products == "NO3:woa23, TALK:glodap_v2_2016b"
            assert ds.git_commit == "test_commit_123"
            assert ds.license == "Apache-2.0"
            assert hasattr(ds, "generation_timestamp")
    finally:
        if os.path.exists(path):
            os.remove(path)
