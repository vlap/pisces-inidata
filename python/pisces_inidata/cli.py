"""
CLI Entry Point for pisces-inidata
Provides unified command-line commands for pipeline execution, padding, validation, and status.
"""

import sys
import os
import argparse
import subprocess
from pisces_inidata import __version__
from pisces_inidata.config import load_config, validate_config, export_env_commands
from pisces_inidata.padding import pad_abyssal_depth
from pisces_inidata.check import run_preflight_checks
from pisces_inidata.scoreboard import run_validation_suite
from pisces_inidata.reproduction import run_pipeline_reproduction_test


def get_repo_root() -> str:
    """Finds repository root path by traversing parent directories."""
    cur = os.path.dirname(os.path.abspath(__file__))
    while cur and cur != os.path.dirname(cur):
        if os.path.exists(os.path.join(cur, 'sources.yaml')) or os.path.exists(os.path.join(cur, 'scripts')):
            return cur
        cur = os.path.dirname(cur)
    return os.getcwd()


def cmd_prepare_woa(args):
    from pisces_inidata.woa23 import process_tracer
    process_tracer(args.var_code, args.woa_dir, args.out_file)


def cmd_prepare_doc(args):
    from pisces_inidata.doc import build_doc_climatology
    build_doc_climatology(args.raw_dir, args.out_file)


def cmd_prepare_glodap(args):
    from pisces_inidata.glodap import prepare_glodap_tracer
    prepare_glodap_tracer(args.src_file, args.var_name, args.out_file)


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
    if getattr(args, 'preset', None):
        env["PRESET"] = args.preset
        env["INIDATA_PRESET"] = args.preset

    res = subprocess.run(["bash", script], cwd=repo_root, env=env)
    sys.exit(res.returncode)


def cmd_validate(args):
    repo_root = get_repo_root()
    preset = getattr(args, 'preset', 'official_sette')
    test_dir = args.test_dir
    if not test_dir:
        candidates = [
            os.path.join(repo_root, "output_ORCA2"),
            os.path.join(repo_root, "work_ORCA2", "output_ORCA2"),
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
        fail_on_error=args.fail_on_error,
        preset=preset
    )
    sys.exit(code)


def cmd_test_reproduction(args):
    repo_root = get_repo_root()
    preset = getattr(args, 'preset', 'official_sette')
    test_dir = args.test_dir
    if not test_dir:
        candidates = [
            os.path.join(repo_root, "output_eORCA1"),
            os.path.join(repo_root, "work_eORCA1", "output_eORCA1"),
            os.path.join(repo_root, "work_eORCA1", "reproduction_test"),
            os.path.join(repo_root, "work_eORCA1"),
            repo_root
        ]
        for c in candidates:
            if os.path.exists(c):
                test_dir = c
                break
        if not test_dir:
            test_dir = os.path.join(repo_root, "output_eORCA1")

    ref_dir = args.ref_dir or os.environ.get(
        "ECE4_PISCES_REF",
        os.environ.get(
            "ECE3_PISCES_DIR",
            "/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/pisces"
        )
    )

    mask_file = args.mask
    if not mask_file:
        domain_base = os.environ.get(
            "DOMAIN_BASE_DIR",
            "/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain"
        )
        cand_mask = os.path.join(domain_base, "eORCA1", "maskutil.nc")
        if os.path.exists(cand_mask):
            mask_file = cand_mask

    output_md = args.output_md or os.path.join(repo_root, "PIPELINE_REPRODUCTION_REPORT.md")

    code = run_pipeline_reproduction_test(
        test_dir=test_dir,
        ref_dir=ref_dir,
        mask_file=mask_file,
        output_md=output_md,
        fail_on_error=args.fail_on_error,
        preset=preset
    )
    sys.exit(code)


def cmd_info(args):
    repo_root = get_repo_root()
    cfg_file = getattr(args, 'file', None) or os.path.join(repo_root, 'sources.yaml')
    preset = getattr(args, 'preset', None)
    config = load_config(cfg_file, preset=preset)
    valid = validate_config(config)

    print("=================================================================")
    print(f"  pisces-inidata v{__version__} - System & Configuration Status")
    print("=================================================================")
    print(f"Repository Root:     {repo_root}")
    print(f"Sources File:        {cfg_file}")
    print(f"Active Preset:       {config.get('INIDATA_PRESET', 'ece4')}")
    print(f"Configuration Valid: {'YES' if valid else 'WARNINGS DETECTED'}")
    print("\nConfigured Sources:")
    for k, v in sorted(config.items()):
        if k != 'INIDATA_PRESET':
            print(f"  {k:18s} = {v}")
    print("=================================================================")


def cmd_config(args):
    repo_root = get_repo_root()
    cfg_file = args.file or os.path.join(repo_root, 'sources.yaml')
    preset = getattr(args, 'preset', None)
    config = load_config(cfg_file, preset=preset)
    if args.export:
        print(export_env_commands(config))
    else:
        valid = validate_config(config)
        for k, v in sorted(config.items()):
            print(f"{k} = {v}")
        if not valid:
            sys.exit(1)


def cmd_download(args):
    from pisces_inidata.download import download_sources
    repo_root = get_repo_root()
    cfg_file = args.sources or os.path.join(repo_root, 'sources.yaml')
    raw_dir = args.raw_dir or os.path.join(repo_root, 'pisces_raw_sources')
    preset = getattr(args, 'preset', None)
    code = download_sources(config_file=cfg_file, raw_dir=raw_dir, dry_run=args.dry_run, preset=preset)
    sys.exit(code)


def cmd_pad(args):
    pad_abyssal_depth(args.input, args.output, args.depth)


def cmd_check(args):
    repo_root = get_repo_root()
    cfg_file = args.config or os.path.join(repo_root, 'sources.yaml')
    preset = getattr(args, 'preset', None)
    code = run_preflight_checks(
        grid_name=args.orca,
        config_file=cfg_file,
        raw_dir=args.raw_dir,
        domain_dir=args.domain_dir,
        out_dir=args.out_dir,
        preset=preset
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
        help="Path to custom sources.yaml"
    )
    check_parser.add_argument(
        "--preset",
        choices=["ece4", "ece3", "official_sette"],
        help="Configuration preset (ece4: modern [default], ece3: WOA09+GLODAPv1, "
             "official_sette: all from SETTE with pure interpolation)"
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
    run_parser.add_argument(
        "--preset",
        choices=["ece4", "ece3", "official_sette"],
        help="Configuration preset (ece4: modern [default], ece3: WOA09+GLODAPv1, "
             "official_sette: all from SETTE with pure interpolation)"
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
        "--preset",
        choices=["ece4", "ece3", "official_sette"],
        default="official_sette",
        help="Configuration preset tested in validation (default: official_sette)"
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
        help="Directory containing re-interpolated eORCA1 test files (default: output_eORCA1/)"
    )
    rep_parser.add_argument(
        "--ref-dir",
        help="Directory containing official EC-Earth3 eORCA1 reference files"
    )
    rep_parser.add_argument(
        "--mask",
        help="Path to land-sea mask NetCDF file (maskutil.nc)"
    )
    rep_parser.add_argument(
        "--preset",
        choices=["ece4", "ece3", "official_sette"],
        default="official_sette",
        help="Configuration preset tested for reproduction (default: official_sette)"
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
    info_parser.add_argument("--file", help="Path to custom sources.yaml")
    info_parser.add_argument(
        "--preset",
        choices=["ece4", "ece3", "official_sette"],
        help="Configuration preset to preview"
    )
    info_parser.set_defaults(func=cmd_info)

    # Command: config
    cfg_parser = subparsers.add_parser("config", help="Inspect sources.yaml or export shell environment variables")
    cfg_parser.add_argument("--file", help="Path to custom sources.yaml")
    cfg_parser.add_argument(
        "--preset",
        choices=["ece4", "ece3", "official_sette"],
        help="Configuration preset to export"
    )
    cfg_parser.add_argument("--export", action="store_true", help="Print bash export statements")
    cfg_parser.set_defaults(func=cmd_config)

    # Command: download
    dl_parser = subparsers.add_parser(
        "download", help="Fetch and stage raw observational datasets based on sources.yaml"
    )
    dl_parser.add_argument("--sources", help="Path to custom sources.yaml")
    dl_parser.add_argument("--raw-dir", help="Target directory to store raw sources")
    dl_parser.add_argument(
        "--preset",
        choices=["ece4", "ece3", "official_sette"],
        help="Configuration preset to download"
    )
    dl_parser.add_argument(
        "--dry-run", action="store_true", help="Inspect what would be downloaded without downloading"
    )
    dl_parser.set_defaults(func=cmd_download)

    # Command: pad
    pad_parser = subparsers.add_parser("pad", help="Pad vertical coordinate to abyssal depth")
    pad_parser.add_argument("input", help="Source NetCDF file")
    pad_parser.add_argument("output", help="Target padded NetCDF file")
    pad_parser.add_argument("--depth", type=float, default=6000.0, help="Bottom depth limit in meters")
    pad_parser.set_defaults(func=cmd_pad)

    # Command: prepare-woa
    woa_parser = subparsers.add_parser("prepare-woa", help="Combine monthly WOA23 files with annual deep levels")
    woa_parser.add_argument(
        "var_code", choices=["n", "p", "i", "o"],
        help="Tracer code: n (NO3), p (PO4), i (Si), o (O2)"
    )
    woa_parser.add_argument("woa_dir", help="Directory containing WOA23 raw files")
    woa_parser.add_argument("out_file", help="Path to output 12-month 3D NetCDF")
    woa_parser.set_defaults(func=cmd_prepare_woa)

    # Command: prepare-doc
    doc_parser = subparsers.add_parser("prepare-doc", help="Convert Panaïotis et al. (2024) DOC CSVs to NetCDF")
    doc_parser.add_argument("raw_dir", help="Directory containing or downloading DOC CSVs")
    doc_parser.add_argument("out_file", help="Path to output 12-month 3D NetCDF")
    doc_parser.set_defaults(func=cmd_prepare_doc)

    # Command: prepare-glodap
    glodap_parser = subparsers.add_parser(
        "prepare-glodap",
        help="Standardize GLODAP vertical coordinate and pad to 6000m"
    )
    glodap_parser.add_argument("var_name", help="GLODAP variable name (TAlk, TCO2, PI_TCO2)")
    glodap_parser.add_argument("src_file", help="Path to raw GLODAP NetCDF file")
    glodap_parser.add_argument("out_file", help="Path to standardized output NetCDF file")
    glodap_parser.set_defaults(func=cmd_prepare_glodap)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
