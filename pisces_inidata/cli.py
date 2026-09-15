"""
CLI Entry Point for pisces-inidata
Provides unified command-line commands for pipeline execution, padding, validation, and status.
"""

import sys
import os
import argparse
import subprocess
from pisces_inidata import __version__
from pisces_inidata.config import load_config, validate_config
from pisces_inidata.padding import pad_abyssal_depth
from pisces_inidata.check import run_preflight_checks
from pisces_inidata.scoreboard import run_validation_suite
from pisces_inidata.reproduction import run_pipeline_reproduction_test


def get_repo_root() -> str:
    """Finds repository root path."""
    current = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(current)
    if os.path.exists(os.path.join(parent, 'products.cfg')) or os.path.exists(os.path.join(parent, 'scripts')):
        return parent
    return os.getcwd()


def cmd_run(args):
    repo_root = get_repo_root()
    script = os.path.join(repo_root, 'scripts', 'launcher_pisces_inidata.sh')
    if not os.path.exists(script):
        script = os.path.join(repo_root, 'launcher_pisces_inidata.sh')
    if not os.path.exists(script):
        print(f"Error: launcher script not found at {script}")
        sys.exit(1)

    print(f"Launching PISCES inidata pipeline: {script}")
    env = os.environ.copy()
    if args.orca:
        env["GRID_NAME"] = args.orca
    if args.domain_dir:
        env["DOMAIN_BASE_DIR"] = os.path.abspath(args.domain_dir)

    res = subprocess.run(["bash", script], cwd=repo_root, env=env)
    sys.exit(res.returncode)


def cmd_validate(args):
    repo_root = get_repo_root()
    test_dir = args.test_dir
    if not test_dir:
        candidates = [
            os.path.join(repo_root, "output_ORCA2"),
            os.path.join(repo_root, "work_ORCA2"),
            os.path.join(repo_root, "work_orca2"),
            repo_root
        ]
        for c in candidates:
            if os.path.exists(c):
                test_dir = c
                break
        if not test_dir:
            test_dir = os.path.join(repo_root, "output_ORCA2")

    ref_dir = args.ref_dir or os.environ.get("SETTE_REF_DIR", os.path.join(repo_root, "sette_reference_ORCA2"))
    output_md = args.output_md or os.path.join(repo_root, "VALIDATION_SCOREBOARD_ORCA2.md")

    code = run_validation_suite(
        test_dir=test_dir,
        ref_dir=ref_dir,
        output_md=output_md,
        fail_on_error=args.fail_on_error
    )
    sys.exit(code)


def cmd_test_reproduction(args):
    repo_root = get_repo_root()
    test_dir = args.test_dir or os.path.join(repo_root, "work_eORCA1", "reproduction_test")
    ref_dir = args.ref_dir or "/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/pisces"
    output_md = args.output_md or os.path.join(repo_root, "PIPELINE_REPRODUCTION_REPORT.md")

    code = run_pipeline_reproduction_test(
        test_dir=test_dir,
        ref_dir=ref_dir,
        mask_file=args.mask,
        output_md=output_md,
        fail_on_error=args.fail_on_error
    )
    sys.exit(code)


def cmd_info(args):
    repo_root = get_repo_root()
    cfg_file = os.path.join(repo_root, 'products.cfg')
    config = load_config(cfg_file)
    valid = validate_config(config)

    print("=================================================================")
    print(f"  pisces-inidata v{__version__} - System & Configuration Status")
    print("=================================================================")
    print(f"Repository Root: {repo_root}")
    print(f"Configuration File: {cfg_file}")
    print(f"Configuration Valid: {'YES' if valid else 'WARNINGS DETECTED'}")
    print("\nConfigured Products:")
    for k, v in sorted(config.items()):
        print(f"  {k:18s} = {v}")
    print("=================================================================")


def cmd_pad(args):
    pad_abyssal_depth(args.input, args.output, args.depth)


def cmd_check(args):
    repo_root = get_repo_root()
    cfg_file = args.config or os.path.join(repo_root, 'products.cfg')
    code = run_preflight_checks(
        grid_name=args.orca,
        config_file=cfg_file,
        raw_dir=args.raw_dir,
        domain_dir=args.domain_dir,
        out_dir=args.out_dir
    )
    sys.exit(code)


def main():
    parser = argparse.ArgumentParser(
        prog="pisces-inidata",
        description="Global Biogeochemical Initial Conditions Generator for PISCES and EC-Earth4"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: check
    check_parser = subparsers.add_parser("check", help="Run pre-flight system and data integrity verification")
    check_parser.add_argument(
        "--orca",
        choices=["ORCA2", "eORCA1", "eORCA025"],
        default="ORCA2",
        help="Target NEMO grid resolution to verify"
    )
    check_parser.add_argument(
        "--domain-dir",
        help="Path to directory containing target NEMO domain files (${GRID_NAME}/domain_cfg.nc)"
    )
    check_parser.add_argument(
        "--raw-dir",
        help="Path to directory containing raw input products"
    )
    check_parser.add_argument(
        "--out-dir",
        help="Target output directory for free disk space check"
    )
    check_parser.add_argument(
        "--config",
        help="Path to custom products.cfg"
    )
    check_parser.set_defaults(func=cmd_check)

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run end-to-end PISCES initial conditions generation")
    run_parser.add_argument(
        "--orca",
        choices=["ORCA2", "eORCA1", "eORCA025"],
        default="ORCA2",
        help="Target NEMO grid resolution"
    )
    run_parser.add_argument(
        "--domain-dir",
        help="Path to directory containing target NEMO domain files (${GRID_NAME}/domain_cfg.nc). "
             "See https://ec-earth-4-docs.readthedocs.io/ for obtaining official EC-Earth4 inidata."
    )
    run_parser.set_defaults(func=cmd_run)

    # Command: validate
    val_parser = subparsers.add_parser(
        "validate",
        help="Run procedure validation scorecard on ORCA2 vs SETTE benchmark"
    )
    val_parser.add_argument(
        "--test-dir",
        help="Directory containing generated ORCA2 NetCDF files (default: output_ORCA2/)"
    )
    val_parser.add_argument(
        "--ref-dir",
        help="Directory containing SETTE ORCA2 benchmark reference files (default: sette_reference_ORCA2/)"
    )
    val_parser.add_argument(
        "--output-md",
        help="Path to write Markdown scorecard report (default: VALIDATION_SCOREBOARD_ORCA2.md)"
    )
    val_parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with non-zero code if any product encounters a critical validation error"
    )
    val_parser.set_defaults(func=cmd_validate)

    # Command: test-reproduction
    rep_parser = subparsers.add_parser(
        "test-reproduction",
        help="Run precision test verifying reproduction of EC-Earth3 baseline inidata on eORCA1"
    )
    rep_parser.add_argument(
        "--test-dir",
        required=True,
        help="Directory containing re-interpolated eORCA1 test files"
    )
    rep_parser.add_argument(
        "--ref-dir",
        required=True,
        help="Directory containing official EC-Earth3 eORCA1 reference files"
    )
    rep_parser.add_argument(
        "--mask",
        help="Path to land-sea mask NetCDF file (maskutil.nc)"
    )
    rep_parser.add_argument(
        "--output-md",
        help="Path to write Markdown report (default: PIPELINE_REPRODUCTION_REPORT.md)"
    )
    rep_parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with non-zero code if reproduction precision thresholds are not met"
    )
    rep_parser.set_defaults(func=cmd_test_reproduction)

    # Command: info
    info_parser = subparsers.add_parser("info", help="Display current configuration and environment status")
    info_parser.set_defaults(func=cmd_info)

    # Command: pad
    pad_parser = subparsers.add_parser("pad", help="Pad vertical coordinate to abyssal depth")
    pad_parser.add_argument("input", help="Source NetCDF file")
    pad_parser.add_argument("output", help="Target padded NetCDF file")
    pad_parser.add_argument("--depth", type=float, default=6000.0, help="Bottom depth limit in meters")
    pad_parser.set_defaults(func=cmd_pad)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
