"""
Tests for pisces_inidata.padding module.
"""

import os
import tempfile
import netCDF4 as nc
import numpy as np
from pisces_inidata.padding import pad_abyssal_depth


def test_pad_abyssal_depth():
    with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as in_f, \
         tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as out_f:
        in_path = in_f.name
        out_path = out_f.name

    try:
        # Create a small synthetic 3D netcdf file (depth, lat, lon)
        with nc.Dataset(in_path, 'w') as ds:
            ds.createDimension('depth', 3)
            ds.createDimension('lat', 2)
            ds.createDimension('lon', 2)

            d_var = ds.createVariable('depth', 'f4', ('depth',))
            d_var[:] = [10.0, 100.0, 5000.0]

            v_var = ds.createVariable('NO3', 'f4', ('depth', 'lat', 'lon'))
            v_var[:] = np.arange(12, dtype=np.float32).reshape((3, 2, 2))

        # Pad depth
        pad_abyssal_depth(in_path, out_path, target_bottom_depth=6000.0)

        with nc.Dataset(out_path, 'r') as ds_out:
            assert 'depth' in ds_out.variables
            depths = ds_out.variables['depth'][:]
            # Since input depths were [10, 100, 5000], it should have padded both top (0.0) and bottom (6000.0)
            assert len(depths) == 5
            assert np.isclose(depths[0], 0.0)
            assert np.isclose(depths[-1], 6000.0)

            no3_padded = ds_out.variables['NO3'][:]
            assert no3_padded.shape == (5, 2, 2)
            # Check top layer duplicated
            np.testing.assert_array_equal(no3_padded[0], no3_padded[1])
            # Check bottom layer duplicated
            np.testing.assert_array_equal(no3_padded[4], no3_padded[3])
    finally:
        for p in [in_path, out_path]:
            if os.path.exists(p):
                os.remove(p)
