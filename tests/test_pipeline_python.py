"""
Unit and Integration Tests for Pure Python CDO & PyNCO Pipeline.
Tests weights, etl, remap, launcher, and reference modules.
"""

import os
import tempfile
import netCDF4 as nc
import numpy as np

from pisces_inidata.remap import (
    resolve_field_type,
    get_output_dir,
    get_weights_dir,
    is_same_grid,
    clamp_file_non_negative
)
from pisces_inidata.etl import get_standardized_dir, sanitize_source_coords
from pisces_inidata.launcher import generate_slurm_array_script, launch_pipeline, PIPELINE_FIELDS
from pisces_inidata.reference import TRACER_MAP, NATIVE_FORCINGS
from pisces_inidata.catalog import resolve_target_field, resolve_source_field


def test_field_type_resolution():
    assert resolve_field_type("NO3") == "3d"
    assert resolve_field_type("TALK") == "3d"
    assert resolve_field_type("dust") == "2d"
    assert resolve_field_type("ndep") == "2d"
    assert resolve_field_type("par") == "2d"
    assert resolve_field_type("bathy") == "bathy"
    assert resolve_field_type("hydrofe") == "hydrofe"
    assert resolve_field_type("river") == "river"
    assert resolve_field_type("rivers") == "river"


def test_output_and_weights_dir_resolution():
    out = get_output_dir("eORCA1")
    assert "eORCA1" in out
    w_dir = get_weights_dir()
    assert "weights" in w_dir
    std_dir = get_standardized_dir()
    assert "standardized_sources" in std_dir


def test_is_same_grid():
    with tempfile.TemporaryDirectory() as td:
        f1 = os.path.join(td, "grid1.nc")
        f2 = os.path.join(td, "grid2.nc")
        f3 = os.path.join(td, "grid3.nc")

        with nc.Dataset(f1, "w") as ds:
            ds.createDimension("x", 10)
            ds.createDimension("y", 10)
            v = ds.createVariable("var", "f4", ("y", "x"))
            v[...] = 1.0

        with nc.Dataset(f2, "w") as ds:
            ds.createDimension("x", 10)
            ds.createDimension("y", 10)
            v = ds.createVariable("var", "f4", ("y", "x"))
            v[...] = 2.0

        with nc.Dataset(f3, "w") as ds:
            ds.createDimension("x", 20)
            ds.createDimension("y", 10)
            v = ds.createVariable("var", "f4", ("y", "x"))
            v[...] = 3.0

        assert is_same_grid(f1, f2) is True
        assert is_same_grid(f1, f3) is False


def test_clamp_file_non_negative():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "test_tracer.nc")
        with nc.Dataset(f, "w") as ds:
            ds.createDimension("x", 4)
            v = ds.createVariable("NO3", "f4", ("x",), fill_value=1e20)
            v[:] = np.ma.masked_array([-2.5, 0.0, 15.2, 1e20], mask=[False, False, False, True])

        clamp_file_non_negative(f, ["NO3"])

        with nc.Dataset(f, "r") as ds:
            res = ds.variables["NO3"][:]
            assert res[0] == 0.0
            assert res[1] == 0.0
            assert np.isclose(res[2], 15.2)
            assert res.mask[3] is True or res.mask[3] == 1


def test_sanitize_source_coords():
    with tempfile.TemporaryDirectory() as td:
        in_nc = os.path.join(td, "input.nc")
        out_nc = os.path.join(td, "output.nc")

        with nc.Dataset(in_nc, "w", format="NETCDF4") as ds:
            ds.createDimension("x", 2)
            ds.createDimension("y", 2)
            v_lon = ds.createVariable("nav_lon", "f4", ("y", "x"))
            v_lon[:] = [[0, 1], [0, 1]]
            v_lat = ds.createVariable("nav_lat", "f4", ("y", "x"))
            v_lat[:] = [[0, 0], [1, 1]]
            v_data = ds.createVariable("dust", "f4", ("y", "x"))
            v_data[:] = [[0.1, 0.2], [0.3, 0.4]]

        sanitize_source_coords(in_nc, out_nc, ["dust"])
        assert os.path.isfile(out_nc)

        with nc.Dataset(out_nc, "r") as ds:
            assert getattr(ds.variables["dust"], "coordinates") == "nav_lon nav_lat"
            assert getattr(ds.variables["nav_lon"], "units") == "degrees_east"
            assert getattr(ds.variables["nav_lat"], "units") == "degrees_north"


def test_generate_slurm_array_script():
    with tempfile.TemporaryDirectory() as td:
        jobs_dir = os.path.join(td, "jobs")
        log_dir = os.path.join(td, "logs")

        script = generate_slurm_array_script(
            grid_name="eORCA1",
            pack="ece4",
            convention="nemo4_ece4",
            jobs_dir=jobs_dir,
            log_dir=log_dir,
            concurrency_limit=4,
        )

        assert os.path.isfile(script)
        with open(script, "r", encoding="utf-8") as f:
            content = f.read()

        assert "#SBATCH --array=0-14%4" in content
        assert "pisces.remap.eORCA1" in content
        assert "pisces-inidata remap --grid \"eORCA1\"" in content
        assert "Pack: ece4" in content
        for fld in PIPELINE_FIELDS:
            assert fld in content


def test_launch_pipeline_dry_run():
    res = launch_pipeline(
        grid_name="eORCA1",
        pack="ece4",
        convention="nemo4_ece4",
        stage="all",
        dry_run=True,
        executor="local",
    )
    assert res["grid"] == "eORCA1"
    assert res["pack"] == "ece4"
    assert res["preset"] == "ece4"
    assert res["stage"] == "all"


def test_launch_pipeline_slurm_dry_run():
    with tempfile.TemporaryDirectory() as td:
        res = launch_pipeline(
            grid_name="eORCA025",
            pack="ece4",
            stage="stage2",
            dry_run=True,
            executor="slurm",
            jobs_dir=os.path.join(td, "jobs"),
            log_dir=os.path.join(td, "logs"),
        )
        assert res["grid"] == "eORCA025"
        assert res["pack"] == "ece4"
        assert res["submitted_job_id"] == "DRY_RUN_ARRAY_ID"


def test_reference_mappings():
    assert len(TRACER_MAP) == 9
    tracers = [t[2] for t in TRACER_MAP]
    assert "NO3" in tracers
    assert "TALK" in tracers
    assert "DOC" in tracers

    assert len(NATIVE_FORCINGS) == 6
    forcings = [f[1] for f in NATIVE_FORCINGS]
    assert "dust.orca.nc" in forcings
    assert "river.orca.nc" in forcings


def test_catalog_resolution_for_pipeline():
    for fld in PIPELINE_FIELDS:
        tgt = resolve_target_field(fld, grid_name="eORCA1")
        assert "out_file" in tgt
        assert "target_var" in tgt

        src = resolve_source_field(fld, pack="ece4")
        assert "src_var" in src
        assert "handler" in src
