"""
Tests for pisces_inidata.scoreboard module.
"""

import os
import tempfile
import netCDF4 as nc
import numpy as np
from pisces_inidata.scoreboard import (
    compute_diagnostics,
    generate_scoreboard,
    run_validation_suite
)


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
        assert diag['status'] == 'PASS'

        # Generate markdown
        md = generate_scoreboard([diag])
        assert "NO3" in md
        assert "Rel RMSE" in md
        assert "PASS" in md
    finally:
        for p in [path_ref, path_test]:
            if os.path.exists(p):
                os.remove(p)


def test_scale_error_detection():
    """Verify that a 1000x factor unit error is caught and flagged as FAIL."""
    with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_ref, \
         tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_test:
        path_ref = f_ref.name
        path_test = f_test.name

    try:
        ref_arr = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        # 1000x unit scale mismatch (e.g. mol/L instead of nmol/L)
        test_arr = ref_arr * 1000.0

        for path, arr in [(path_ref, ref_arr), (path_test, test_arr)]:
            with nc.Dataset(path, 'w') as ds:
                ds.createDimension('points', len(arr))
                v = ds.createVariable('Fer', 'f4', ('points',))
                v[:] = arr

        diag = compute_diagnostics(path_test, path_ref, 'Fer')
        assert diag['status'] == 'FAIL'
        assert 'Unit scale error' in diag['issue']
    finally:
        for p in [path_ref, path_test]:
            if os.path.exists(p):
                os.remove(p)


def test_negative_values_detection():
    """Verify that negative concentrations are flagged as FAIL."""
    with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_ref, \
         tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_test:
        path_ref = f_ref.name
        path_test = f_test.name

    try:
        ref_arr = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        # Unphysical negative concentration
        test_arr = np.array([-5.0, 20.0, 30.0, 40.0], dtype=np.float32)

        for path, arr in [(path_ref, ref_arr), (path_test, test_arr)]:
            with nc.Dataset(path, 'w') as ds:
                ds.createDimension('points', len(arr))
                v = ds.createVariable('PO4', 'f4', ('points',))
                v[:] = arr

        diag = compute_diagnostics(path_test, path_ref, 'PO4')
        assert diag['status'] == 'FAIL'
        assert 'negative concentration' in diag['issue'].lower()
    finally:
        for p in [path_ref, path_test]:
            if os.path.exists(p):
                os.remove(p)


def test_inverted_pattern_detection():
    """Verify that inverted spatial patterns (r < 0) are flagged as FAIL."""
    with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_ref, \
         tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_test:
        path_ref = f_ref.name
        path_test = f_test.name

    try:
        ref_arr = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        # Inverted pattern (e.g. flipped latitude axis)
        test_arr = np.array([40.0, 30.0, 20.0, 10.0], dtype=np.float32)

        for path, arr in [(path_ref, ref_arr), (path_test, test_arr)]:
            with nc.Dataset(path, 'w') as ds:
                ds.createDimension('points', len(arr))
                v = ds.createVariable('O2', 'f4', ('points',))
                v[:] = arr

        diag = compute_diagnostics(path_test, path_ref, 'O2')
        assert diag['status'] == 'FAIL'
        assert 'Inverted pattern' in diag['issue']
    finally:
        for p in [path_ref, path_test]:
            if os.path.exists(p):
                os.remove(p)


def test_run_validation_suite():
    with tempfile.TemporaryDirectory() as tmp_test, tempfile.TemporaryDirectory() as tmp_ref:
        out_md = os.path.join(tmp_test, "scorecard.md")

        # Create matching NO3 file
        arr = np.array([10.0, 20.0, 30.0], dtype=np.float32)
        for d in [tmp_test, tmp_ref]:
            f = os.path.join(d, "data_NO3_ORCA2.nc")
            with nc.Dataset(f, 'w') as ds:
                ds.createDimension('points', len(arr))
                v = ds.createVariable('NO3', 'f4', ('points',))
                v[:] = arr

        code = run_validation_suite(test_dir=tmp_test, ref_dir=tmp_ref, output_md=out_md, pack="official_sette")
        assert code == 0
        assert os.path.exists(out_md)
        with open(out_md, 'r') as f:
            content = f.read()
            assert "SETTE nomask" in content
            assert "Configuration Pack" in content
            assert "official_sette" in content
            assert "PASS" in content

        out_md_ece4 = os.path.join(tmp_test, "scorecard_ece4.md")
        code_ece4 = run_validation_suite(test_dir=tmp_test, ref_dir=tmp_ref, output_md=out_md_ece4, pack="ece4")
        assert code_ece4 == 0
        with open(out_md_ece4, 'r') as f:
            content_ece4 = f.read()
            assert "WOA23" in content_ece4
            assert "Configuration Pack" in content_ece4
            assert "ece4" in content_ece4


def test_compute_river_conservation():
    from pisces_inidata.scoreboard import compute_river_conservation

    with tempfile.TemporaryDirectory() as td:
        f_test = os.path.join(td, "river_test.nc")
        f_ref = os.path.join(td, "river_ref.nc")

        arr_ref = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        # Test array with exact conservation
        arr_test = arr_ref.copy()

        for f, arr in [(f_ref, arr_ref), (f_test, arr_test)]:
            with nc.Dataset(f, 'w') as ds:
                ds.createDimension('x', 2)
                ds.createDimension('y', 2)
                v = ds.createVariable('riverdin', 'f4', ('y', 'x'))
                v[:] = arr

        res = compute_river_conservation(f_test, f_ref)
        assert len(res) == 1
        assert res[0]['var'] == 'riverdin'
        assert np.isclose(res[0]['ratio'], 1.0)
        assert np.isclose(res[0]['r'], 1.0)
        assert res[0]['status'] == 'PASS'
        assert 'Conserved' in res[0]['issue']
