"""
Tests for mass conservation verification in pisces_inidata.scoreboard.
"""

import os
import tempfile
import netCDF4 as nc
import numpy as np
from pisces_inidata.scoreboard import compute_mass_conservation


def test_mass_conservation_pass():
    with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_test, \
         tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_ref:
        test_path = f_test.name
        ref_path = f_ref.name

    try:
        # Both datasets have identical sum
        data = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)

        for p in [test_path, ref_path]:
            with nc.Dataset(p, 'w') as ds:
                ds.createDimension('y', 2)
                ds.createDimension('x', 2)
                v = ds.createVariable('riverdin', 'f4', ('y', 'x'))
                v[:] = data

        res = compute_mass_conservation(test_path, ref_path, 'riverdin', tolerance_pct=0.1)

        assert res['passed'] is True
        assert res['status'] == "PASS"
        assert np.isclose(res['rel_diff_pct'], 0.0)
        assert np.isclose(res['integral_test'], 100.0)
        assert np.isclose(res['integral_ref'], 100.0)
    finally:
        for p in [test_path, ref_path]:
            if os.path.exists(p):
                os.remove(p)


def test_mass_conservation_fail():
    with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_test, \
         tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_ref:
        test_path = f_test.name
        ref_path = f_ref.name

    try:
        # Test has 5% divergence
        data_ref = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
        data_test = data_ref * 1.05

        with nc.Dataset(ref_path, 'w') as ds:
            ds.createDimension('y', 2)
            ds.createDimension('x', 2)
            v = ds.createVariable('dust', 'f4', ('y', 'x'))
            v[:] = data_ref

        with nc.Dataset(test_path, 'w') as ds:
            ds.createDimension('y', 2)
            ds.createDimension('x', 2)
            v = ds.createVariable('dust', 'f4', ('y', 'x'))
            v[:] = data_test

        res = compute_mass_conservation(test_path, ref_path, 'dust', tolerance_pct=0.5)

        assert res['passed'] is False
        assert res['status'] == "FAIL"
        assert np.isclose(res['rel_diff_pct'], 5.0, atol=1e-3)
    finally:
        for p in [test_path, ref_path]:
            if os.path.exists(p):
                os.remove(p)
