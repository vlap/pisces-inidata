"""
Unit tests for declarative platform profiles (platforms.yaml).
"""

import os
import tempfile
from pisces_inidata.platforms import (
    load_all_platforms,
    load_platform_config,
    get_known_platforms,
    export_platform_env_commands,
    detect_current_platform,
)


def test_known_platforms():
    platforms = get_known_platforms()
    assert "nord4" in platforms
    assert "mn5" in platforms
    assert "generic" in platforms


def test_load_nord4():
    cfg = load_platform_config("nord4")
    assert cfg["slurm"]["account"] == "bsc32"
    assert cfg["slurm"]["partition"] == "bsc_es"
    assert "/gpfs/projects/bsc32" in cfg["domain_dir"]
    assert "/gpfs/scratch/bsc32" in cfg["scratch_root"]


def test_load_mn5():
    cfg = load_platform_config("mn5")
    assert cfg["slurm"]["account"] == "bsc32"
    assert cfg["slurm"]["partition"] == "gpp"


def test_load_generic():
    cfg = load_platform_config("generic")
    assert cfg["slurm"]["account"] == ""
    assert cfg["slurm"]["partition"] == ""


def test_detect_platform():
    plat = detect_current_platform()
    assert isinstance(plat, str)
    assert len(plat) > 0


def test_export_platform_env_commands():
    cmds = export_platform_env_commands("nord4")
    assert 'export PLATFORM="nord4"' in cmds
    assert 'export SLURM_ACCOUNT="${SLURM_ACCOUNT:-bsc32}"' in cmds
    assert 'export SLURM_PARTITION="${SLURM_PARTITION:-bsc_es}"' in cmds


def test_custom_platforms_yaml():
    custom_content = """
platforms:
  MY_CLUSTER:
    description: "Custom Institutional Supercomputer"
    slurm:
      account: "my_project"
      partition: "standard"
    module_load: "module load cdo nco"
    scratch_root: "/scratch/work/${USER}"
    domain_dir: "/data/models/nemo/domain"
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(custom_content)
        f_path = f.name

    try:
        all_plats = load_all_platforms(f_path)
        assert "MY_CLUSTER" in all_plats
        cfg = load_platform_config("MY_CLUSTER", f_path)
        assert cfg["slurm"]["account"] == "my_project"
        assert cfg["slurm"]["partition"] == "standard"
        assert cfg["scratch_root"] == "/scratch/work/${USER}"

        cmds = export_platform_env_commands("MY_CLUSTER", f_path)
        assert 'export PLATFORM="MY_CLUSTER"' in cmds
        assert 'export SLURM_ACCOUNT="${SLURM_ACCOUNT:-my_project}"' in cmds
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)
