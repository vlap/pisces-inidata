"""
Tests for pisces_inidata.verify module and CLI subcommand.
"""

import os
import sys
import tempfile
import pytest
import numpy as np
import netCDF4 as nc
from pisces_inidata.verify import verify_output_directory, EXPECTED_PRODUCTS
from pisces_inidata.cli import main


def test_verify_missing_directory():
    exit_code, results = verify_output_directory("/nonexistent/directory", grid_name="eORCA025")
    assert exit_code == 1
    assert len(results) == len(EXPECTED_PRODUCTS)
    assert all(r['status'] == 'FAIL' for r in results)


def test_verify_synthetic_valid_and_blank():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create all 15 expected files synthetically
        grid = "eORCA025"
        for tmpl, vname in EXPECTED_PRODUCTS:
            fpath = os.path.join(tmp_dir, tmpl.format(grid=grid))
            with nc.Dataset(fpath, 'w') as ds:
                ds.createDimension('x', 4)
                ds.createDimension('y', 4)
                if 'data_' in tmpl:
                    ds.createDimension('depth', 3)
                    var = ds.createVariable(vname, 'f4', ('depth', 'y', 'x'))
                    var[:] = np.ones((3, 4, 4), dtype=np.float32) * 2.5
                else:
                    var = ds.createVariable(vname, 'f4', ('y', 'x'))
                    var[:] = np.ones((4, 4), dtype=np.float32) * 1.5

        # All files valid -> Should pass
        code, results = verify_output_directory(tmp_dir, grid_name=grid)
        assert code == 0
        assert all(r['status'] == 'PASS' for r in results)

        # Make one file completely blank (all zeros)
        blank_file = os.path.join(tmp_dir, EXPECTED_PRODUCTS[0][0].format(grid=grid))
        with nc.Dataset(blank_file, 'w') as ds:
            ds.createDimension('x', 4)
            ds.createDimension('y', 4)
            ds.createDimension('depth', 3)
            var = ds.createVariable(EXPECTED_PRODUCTS[0][1], 'f4', ('depth', 'y', 'x'))
            var[:] = np.zeros((3, 4, 4), dtype=np.float32)

        code_fail, results_fail = verify_output_directory(tmp_dir, grid_name=grid)
        assert code_fail == 1
        assert results_fail[0]['status'] == 'FAIL'


def test_cli_verify_help(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['pisces-inidata', 'verify', '--help'])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
