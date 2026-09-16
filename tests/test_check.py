"""
Unit tests for pisces_inidata.check pre-flight verification module.
"""

import os
import tempfile
from unittest.mock import patch
from pisces_inidata.check import (
    check_binaries,
    check_python_packages,
    check_disk_space,
    check_target_grid,
    check_raw_sources,
    run_preflight_checks
)


def test_check_binaries():
    results = check_binaries()
    assert isinstance(results, list)
    assert len(results) > 0
    names = [r[0] for r in results]
    assert "cdo" in names
    assert "ncks" in names


def test_check_python_packages():
    results = check_python_packages()
    assert isinstance(results, list)
    names = [r[0] for r in results]
    assert "netCDF4" in names
    assert "numpy" in names
    for name, ok, ver in results:
        assert ok is True


def test_check_disk_space():
    ok, free_gb, req_gb = check_disk_space(".", "ORCA2")
    assert isinstance(ok, bool)
    assert free_gb > 0
    assert req_gb == 2.0

    # With huge required disk space, should fail
    with patch.dict("pisces_inidata.check.MIN_DISK_SPACE_GB", {"ORCA2": 999999.0}):
        ok_fail, _, _ = check_disk_space(".", "ORCA2")
        assert ok_fail is False


def test_check_target_grid():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Check missing grid
        results = check_target_grid("ORCA2", domain_dir=tmpdir)
        assert results[0][1] is False

        # Create dummy target grid
        orca_dir = os.path.join(tmpdir, "ORCA2")
        os.makedirs(orca_dir)
        grid_file = os.path.join(orca_dir, "domain_cfg.nc")
        with open(grid_file, "w") as f:
            f.write("dummy")

        results_ok = check_target_grid("ORCA2", domain_dir=tmpdir)
        assert results_ok[0][1] is True


def test_check_raw_sources():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Non-existent directory
        res_missing = check_raw_sources(os.path.join(tmpdir, "nonexistent"), {})
        assert res_missing[0][1] is False

        # Directory with some files
        raw_dir = os.path.join(tmpdir, "raw")
        os.makedirs(raw_dir)
        with open(os.path.join(raw_dir, "woa23_decav_n00_01.nc"), "w") as f:
            f.write("dummy")
        with open(os.path.join(raw_dir, "GLODAPv2.2016b.TAlk.nc"), "w") as f:
            f.write("dummy")

        res = check_raw_sources(raw_dir, {})
        found_map = {r[0]: r[1] for r in res}
        assert found_map["NO3 / Nutrients"] is True
        assert found_map["GLODAP Inorganics"] is True
        assert found_map["Iron (Fe)"] is False


def test_run_preflight_checks_pass():
    with patch("pisces_inidata.check.check_binaries") as mock_bin, \
         patch("pisces_inidata.check.check_python_packages") as mock_py, \
         patch("pisces_inidata.check.check_target_grid") as mock_grid, \
         patch("pisces_inidata.check.check_raw_sources") as mock_raw, \
         patch("pisces_inidata.check.check_disk_space") as mock_disk:

        mock_bin.return_value = [("cdo", True, "2.4.0", True), ("ncks", True, "5.1", True)]
        mock_py.return_value = [("numpy", True, "1.26")]
        mock_grid.return_value = [("Target Grid", True, "/path/to/grid")]
        mock_raw.return_value = [("Nutrients", True, "Present")]
        mock_disk.return_value = (True, 50.0, 2.0)

        ret = run_preflight_checks(grid_name="ORCA2")
        assert ret == 0


def test_run_preflight_checks_fail():
    with patch("pisces_inidata.check.check_binaries") as mock_bin, \
         patch("pisces_inidata.check.check_python_packages") as mock_py, \
         patch("pisces_inidata.check.check_target_grid") as mock_grid, \
         patch("pisces_inidata.check.check_raw_sources") as mock_raw, \
         patch("pisces_inidata.check.check_disk_space") as mock_disk:

        # CDO missing (critical failure)
        mock_bin.return_value = [("cdo", False, "Missing", True)]
        mock_py.return_value = [("numpy", True, "1.26")]
        mock_grid.return_value = [("Target Grid", True, "/path/to/grid")]
        mock_raw.return_value = [("Nutrients", True, "Present")]
        mock_disk.return_value = (True, 50.0, 2.0)

        ret = run_preflight_checks(grid_name="ORCA2")
        assert ret == 1
