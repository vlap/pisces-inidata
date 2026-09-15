"""
Tests for pisces_inidata.scoreboard module.
"""

import os
import tempfile
import netCDF4 as nc
import numpy as np
from pisces_inidata.scoreboard import compute_diagnostics, generate_scoreboard


def test_compute_diagnostics():
    with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_ref, \
         tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_test:
        path_ref = f_ref.name
        path_test = f_test.name

    try:
        ref_arr = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        # Test array with +2 bias
        test_arr = np.array([12.0, 22.0, 32.0, 42.0], dtype=np.float32)

        for path, arr in [(path_ref, ref_arr), (path_test, test_arr)]:
            with nc.Dataset(path, 'w') as ds:
                ds.createDimension('points', len(arr))
                v = ds.createVariable('NO3', 'f4', ('points',))
                v[:] = arr

        diag = compute_diagnostics(path_test, path_ref, 'NO3')

        assert diag['valid_count'] == 4
        assert np.isclose(diag['mbe'], 2.0)
        assert np.isclose(diag['rmse'], 2.0)
        assert np.isclose(diag['mae'], 2.0)
        assert np.isclose(diag['r'], 1.0)
        assert np.isclose(diag['spearman_rho'], 1.0)

        # Generate markdown
        md = generate_scoreboard([diag])
        assert "NO3" in md
        assert "RMSE" in md
    finally:
        for p in [path_ref, path_test]:
            if os.path.exists(p):
                os.remove(p)
