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
    script = os.path.join(repo_root, 'scripts', 'run_validation_suite.sh')
    if not os.path.exists(script):
        script = os.path.join(repo_root, 'run_validation_suite.sh')
    if not os.path.exists(script):
        print(f"Error: validation suite script not found at {script}")
        sys.exit(1)

    print(f"Launching PISCES validation suite: {script}")
    res = subprocess.run(["bash", script], cwd=repo_root)
    sys.exit(res.returncode)


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
    val_parser = subparsers.add_parser("validate", help="Run statistical validation suite against SETTE ground truth")
    val_parser.set_defaults(func=cmd_validate)

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
