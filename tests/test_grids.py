"""
Unit tests for declarative grids configuration (grids.yaml).
"""

import os
import tempfile
from pisces_inidata.grids import (
    load_all_grids,
    load_grid_config,
    get_known_grids,
    export_grid_env_commands,
)


def test_known_grids():
    grids = get_known_grids()
    assert "ORCA2" in grids
    assert "eORCA1" in grids
    assert "eORCA025" in grids
    assert "eORCA12" in grids


def test_load_orca2():
    cfg = load_grid_config("ORCA2")
    assert cfg["vertical_levels"] == 31
    assert cfg["resources"]["batch_weights"] is False
    assert cfg["disk_space_gb"] == 2.0
    assert cfg["fallback_coords_source"] == "official_v5.0.0/bathy.orca.nc"


def test_load_eorca025():
    cfg = load_grid_config("eORCA025")
    assert cfg["vertical_levels"] == 75
    assert cfg["resources"]["batch_weights"] is True
    assert cfg["resources"]["memory"] == "64G"
    assert cfg["disk_space_gb"] == 40.0


def test_load_custom_grid_fallback():
    cfg = load_grid_config("UNKNOWN_CUSTOM_GRID")
    assert cfg["resources"]["memory"] == "16G"
    assert cfg["resources"]["batch_weights"] is False
    assert cfg["vertical_levels"] == 75


def test_export_grid_env_commands():
    cmds = export_grid_env_commands("eORCA025")
    assert 'export GRID_NAME="eORCA025"' in cmds
    assert 'export GRID_SLURM_MEM="64G"' in cmds
    assert 'export GRID_BATCH_WEIGHTS="1"' in cmds


def test_custom_grids_yaml():
    custom_content = """
grids:
  REGIONAL_TEST:
    description: "Regional Mediterranean 1/16-degree subgrid"
    resources:
      time: "03:00:00"
      memory: "32G"
      cpus: 16
      batch_weights: true
    disk_space_gb: 25.0
    vertical_levels: 90
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(custom_content)
        f_path = f.name

    try:
        all_grids = load_all_grids(f_path)
        assert "REGIONAL_TEST" in all_grids
        cfg = load_grid_config("REGIONAL_TEST", f_path)
        assert cfg["vertical_levels"] == 90
        assert cfg["resources"]["memory"] == "32G"
        assert cfg["resources"]["batch_weights"] is True
        assert cfg["disk_space_gb"] == 25.0

        cmds = export_grid_env_commands("REGIONAL_TEST", f_path)
        assert 'export GRID_NAME="REGIONAL_TEST"' in cmds
        assert 'export GRID_SLURM_MEM="32G"' in cmds
        assert 'export GRID_BATCH_WEIGHTS="1"' in cmds
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)
