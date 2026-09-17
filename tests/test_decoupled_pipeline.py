"""
Tests for decoupled Stage 1 (Grid-Agnostic ETL) and Stage 2 (Remapping) architecture.
Pure Python test suite verifying stage decoupling, CLI entrypoints, and launcher modes.
"""

import sys
import pytest
from pisces_inidata.cli import main
from pisces_inidata.launcher import launch_pipeline
from pisces_inidata.remap import get_output_dir, get_weights_dir
from pisces_inidata.etl import get_standardized_dir


def test_cli_subparsers_registration(monkeypatch):
    """Test that prepare-sources, remap, produce, and gen-weights can be parsed by argparse."""
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

    # Test produce --help
    monkeypatch.setattr(sys, 'argv', ['pisces-inidata', 'produce', '--help'])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0

    # Test gen-weights --help
    monkeypatch.setattr(sys, 'argv', ['pisces-inidata', 'gen-weights', '--help'])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


def test_launcher_dry_run_stages():
    """Verify launch_pipeline cleanly executes dry-run for stage1, stage2, and all stages."""
    # Test stage 1 dry-run
    res_stage1 = launch_pipeline(
        grid_name="eORCA1",
        pack="ece4",
        stage="stage1",
        dry_run=True,
        executor="local",
    )
    assert res_stage1["grid"] == "eORCA1"
    assert res_stage1["pack"] == "ece4"
    assert res_stage1["preset"] == "ece4"
    assert res_stage1["stage"] == "stage1"

    # Test stage 2 dry-run
    res_stage2 = launch_pipeline(
        grid_name="eORCA1",
        pack="ece4",
        stage="stage2",
        dry_run=True,
        executor="local",
    )
    assert res_stage2["grid"] == "eORCA1"
    assert res_stage2["pack"] == "ece4"
    assert res_stage2["stage"] == "stage2"

    # Test weights dry-run
    res_weights = launch_pipeline(
        grid_name="eORCA1",
        pack="ece4",
        stage="weights",
        dry_run=True,
        executor="local",
    )
    assert res_weights["grid"] == "eORCA1"
    assert res_weights["pack"] == "ece4"
    assert res_weights["stage"] == "weights"


def test_cli_run_dry_run_stage1(monkeypatch):
    """Test CLI run alias with --stage stage1 --dry-run and --pack."""
    import sys
    monkeypatch.setattr(sys, 'argv', ['pisces-inidata', 'run', '--stage', 'stage1', '--pack', 'ece4', '--dry-run'])
    main()


def test_cli_produce_dry_run(monkeypatch):
    """Test CLI produce with --grid eORCA1 --pack and --preset backward compatibility."""
    cmd_pack = ['pisces-inidata', 'produce', '--grid', 'eORCA1', '--pack', 'official_sette', '--dry-run']
    monkeypatch.setattr(sys, 'argv', cmd_pack)
    main()

    # Verify --preset alias still works
    cmd_preset = ['pisces-inidata', 'produce', '--grid', 'eORCA1', '--preset', 'official_sette', '--dry-run']
    monkeypatch.setattr(sys, 'argv', cmd_preset)
    main()


def test_workspace_directory_resolution():
    """Verify directory resolution for weights, standardized sources, and grid outputs."""
    out_dir = get_output_dir("eORCA1")
    assert "eORCA1" in out_dir

    weights_dir = get_weights_dir()
    assert "weights" in weights_dir

    std_dir = get_standardized_dir()
    assert "standardized" in std_dir
