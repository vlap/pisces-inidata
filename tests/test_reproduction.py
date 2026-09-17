"""
Unit tests for pisces_inidata.reproduction module (EC-Earth3 baseline pipeline reproduction).
"""

import os
import tempfile
import netCDF4 as nc
import numpy as np
from pisces_inidata.reproduction import (
    evaluate_reproduction_closeness,
    format_reproduction_report,
    run_pipeline_reproduction_test
)


def test_evaluate_reproduction_closeness_pass():
    with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_ref, \
         tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f_test:
        path_ref = f_ref.name
        path_test = f_test.name

    try:
        ref_arr = np.array([20.0, 25.0, 30.0, 35.0, 40.0], dtype=np.float32)
        # 1% difference, high correlation
        test_arr = ref_arr * 1.01

        for p, arr in [(path_ref, ref_arr), (path_test, test_arr)]:
            with nc.Dataset(p, 'w') as ds:
                ds.createDimension('points', len(arr))
                v = ds.createVariable('NO3', 'f4', ('points',))
                v[:] = arr

        res = evaluate_reproduction_closeness(path_test, path_ref, 'NO3')

        assert res['valid_points'] == 5
        assert np.isclose(res['pearson_r'], 1.0)
        assert np.isclose(res['rel_rmse_pct'], 1.0, atol=0.05)
        assert np.isclose(res['inventory_diff_pct'], 1.0, atol=1e-2)

        md = format_reproduction_report([res])
        assert "NO3" in md
        assert "EC-Earth3" in md
    finally:
        for p in [path_ref, path_test]:
            if os.path.exists(p):
                os.remove(p)


def test_run_pipeline_reproduction_test():
    with tempfile.TemporaryDirectory() as tmp_test, tempfile.TemporaryDirectory() as tmp_ref:
        out_md = os.path.join(tmp_test, "reproduction_report.md")

        # Create matching NO3 files
        arr = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        test_f = os.path.join(tmp_test, "reg_NO3_WOA2009_monthly_eORCA1.nc")
        ref_f = os.path.join(tmp_ref, "NO3_WOA2009_monthly_eORCA1.nc")

        for f in [test_f, ref_f]:
            with nc.Dataset(f, 'w') as ds:
                ds.createDimension('points', len(arr))
                v = ds.createVariable('NO3', 'f4', ('points',))
                v[:] = arr

        code = run_pipeline_reproduction_test(
            test_dir=tmp_test,
            ref_dir=tmp_ref,
            output_md=out_md,
            pack="official_sette"
        )
        assert code == 0
        assert os.path.exists(out_md)
        with open(out_md, 'r') as f:
            content = f.read()
            assert "NO3" in content
            assert "Configuration Pack" in content
            assert "official_sette" in content
            assert "PASS" in content
