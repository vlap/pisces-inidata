"""
Tests for decoupled Stage 1 (Grid-Agnostic ETL) and Stage 2 (Remapping) architecture.
"""

import os
import subprocess
import pytest
from pisces_inidata.cli import main, get_repo_root


def test_cli_subparsers_registration(monkeypatch):
    # Test that prepare-sources and remap can be parsed by argparse
    from pisces_inidata.cli import main
    import sys

    # Test prepare-sources --help
    monkeypatch.setattr(sys, 'argv', ['pisces-inidata', 'prepare-sources', '--help'])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0

    # Test remap --help
    monkeypatch.setattr(sys, 'argv', ['pisces-inidata', 'remap', '--help'])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


def test_script_existence_and_executable():
    repo_root = get_repo_root()
    s1 = os.path.join(repo_root, 'scripts', 'prepare_standard_sources.sh')
    s2 = os.path.join(repo_root, 'scripts', 'remap_field.sh')
    launcher = os.path.join(repo_root, 'scripts', 'launcher_pisces_inidata.sh')

    for s in [s1, s2, launcher]:
        assert os.path.isfile(s), f"Script not found: {s}"
        assert os.access(s, os.X_OK), f"Script is not executable: {s}"


def test_launcher_dry_run_stages():
    repo_root = get_repo_root()
    launcher = os.path.join(repo_root, 'scripts', 'launcher_pisces_inidata.sh')

    # Test stage 1 dry-run
    res_stage1 = subprocess.run(
        ["bash", launcher, "dry-run", "stage1"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    assert res_stage1.returncode == 0
    assert "Pipeline Stage: stage1" in res_stage1.stdout
    assert "Checking / Standardizing Source Datasets" in res_stage1.stdout
    assert "Stage 1 preparation completed. Exiting as requested." in res_stage1.stdout
    assert "Submitting 3D Tracer Remapping Jobs" not in res_stage1.stdout

    # Test stage 2 dry-run
    res_stage2 = subprocess.run(
        ["bash", launcher, "dry-run", "stage2"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    assert res_stage2.returncode == 0
    assert "Pipeline Stage: stage2" in res_stage2.stdout
    assert "Submitting 3D Tracer Remapping Jobs" in res_stage2.stdout
    assert "Submitting River Nutrient Remapping Job" in res_stage2.stdout
    assert "Checking / Standardizing Source Datasets" not in res_stage2.stdout


def test_cli_run_dry_run_stage1(monkeypatch):
    import sys
    monkeypatch.setattr(sys, 'argv', ['pisces-inidata', 'run', '--stage', 'stage1', '--dry-run'])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


def test_workspace_structure_config():
    repo_root = get_repo_root()
    cmd = [
        "bash", "-c",
        "source scripts/config.sh && echo WORKSPACE=$WORKSPACE && echo RAW_DIR=$RAW_DIR && "
        "echo STANDARDIZED_DIR=$STANDARDIZED_DIR && echo OUTPUT_DIR=$OUTPUT_DIR && echo TMP_BASE=$TMP_BASE"
    ]
    res = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    assert res.returncode == 0
    assert "grids/eORCA1/inidata" in res.stdout
    assert "shared/standardized" in res.stdout
