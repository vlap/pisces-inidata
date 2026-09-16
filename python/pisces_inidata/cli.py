"""
CLI Entry Point for pisces-inidata
Provides unified command-line commands for pipeline execution, padding, validation, and status.
"""

import sys
import os
import argparse
import subprocess
from typing import Optional, List
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


def cmd_resolve_glodap(args):
    from pisces_inidata.glodap import resolve_glodap_source
    raw_dir = args.raw_dir or os.environ.get("RAW_DIR", os.path.join(os.getcwd(), "pisces_raw_sources"))
    path = resolve_glodap_source(args.param, raw_dir, args.version)
    print(str(path))


def cmd_stamp(args):
    from pisces_inidata.provenance import stamp_netcdf_provenance
    stamp_netcdf_provenance(
        args.file,
        grid_name=args.grid,
        institution=args.institution,
        preset=args.preset,
    )


def cmd_prepare_sources(args):
    repo_root = get_repo_root()
    script = os.path.join(repo_root, 'scripts', 'prepare_standard_sources.sh')
    if not os.path.exists(script):
        print(f"Error: prepare script not found at {script}")
        sys.exit(1)

    env = os.environ.copy()
    if getattr(args, 'config', None):
        env["PISCES_CONFIG"] = os.path.abspath(args.config)
    if getattr(args, 'preset', None):
        env["PRESET"] = args.preset
        env["INIDATA_PRESET"] = args.preset
    if getattr(args, 'force', False):
        env["FORCE"] = "1"

    cmd = ["bash", script, args.variable]
    res = subprocess.run(cmd, cwd=repo_root, env=env)
    sys.exit(res.returncode)


def cmd_remap(args):
    repo_root = get_repo_root()
    script = os.path.join(repo_root, 'scripts', 'remap_field.sh')
    if not os.path.exists(script):
        print(f"Error: remap script not found at {script}")
        sys.exit(1)

    env = os.environ.copy()
    grid_name = getattr(args, 'grid', None) or getattr(args, 'orca', None)
    if grid_name:
        env["GRID_NAME"] = grid_name
    if args.domain_dir:
        env["DOMAIN_BASE_DIR"] = os.path.abspath(args.domain_dir)
    if getattr(args, 'config', None):
        env["PISCES_CONFIG"] = os.path.abspath(args.config)
    if getattr(args, 'preset', None):
        env["PRESET"] = args.preset
        env["INIDATA_PRESET"] = args.preset

    cmd = ["bash", script, args.variable]
    res = subprocess.run(cmd, cwd=repo_root, env=env)
    sys.exit(res.returncode)


def cmd_produce(args):
    repo_root = get_repo_root()
    script = os.path.join(repo_root, 'scripts', 'launcher_pisces_inidata.sh')
    if not os.path.exists(script):
        script = os.path.join(repo_root, 'launcher_pisces_inidata.sh')
    if not os.path.exists(script):
        print(f"Error: launcher script not found at {script}")
        sys.exit(1)

    grid_name = getattr(args, 'grid', None) or getattr(args, 'orca', None) or "eORCA1"
    env = os.environ.copy()
    env["GRID_NAME"] = grid_name
    if getattr(args, 'domain_dir', None):
        env["DOMAIN_BASE_DIR"] = os.path.abspath(args.domain_dir)
    if getattr(args, 'config', None):
        env["PISCES_CONFIG"] = os.path.abspath(args.config)
    if getattr(args, 'preset', None):
        env["PRESET"] = args.preset
        env["INIDATA_PRESET"] = args.preset

    submit_mode = "dry-run" if getattr(args, 'dry_run', False) else "submit"
    stage = getattr(args, 'stage', 'stage2')
    preset = env.get("PRESET", "ece4")
    print(f"Producing PISCES inidata for {grid_name} (preset: {preset}, stage: {stage})...")
    res = subprocess.run(["bash", script, submit_mode, stage], cwd=repo_root, env=env)
    sys.exit(res.returncode)


def cmd_run(args):
    cmd_produce(args)


def get_default_workspace() -> str:
    """Resolves default PISCES workspace from environment or platform profile."""
    if os.environ.get("PISCES_WORKSPACE"):
        return os.environ["PISCES_WORKSPACE"]
    from pisces_inidata.platforms import load_platform_config
    plat = load_platform_config()
    scratch = os.path.expandvars(plat.get("scratch_root", "${HOME}/scratch"))
    return os.path.join(scratch, "pisces_inidata")


def resolve_output_dir(
    grid_name: str,
    preferred: Optional[str] = None,
    extra_candidates: Optional[List[str]] = None
) -> str:
    """Resolves output directory by checking preferred, workspace, and repo-level fallback paths."""
    if preferred:
        return preferred
    repo_root = get_repo_root()
    workspace = get_default_workspace()
    candidates = []
    if workspace:
        candidates.append(os.path.join(workspace, "grids", grid_name, "inidata"))
    candidates.extend([
        os.path.join(repo_root, "grids", grid_name, "inidata"),
        os.path.join(repo_root, f"output_{grid_name}"),
        os.path.join(repo_root, f"work_{grid_name}", f"output_{grid_name}"),
    ])
    if extra_candidates:
        candidates.extend(extra_candidates)
    candidates.extend([
        os.path.join(repo_root, f"work_{grid_name}"),
        os.path.join(repo_root, f"work_{grid_name.lower()}"),
    ])
    for c in candidates:
        if os.path.exists(c) and os.path.isdir(c):
            return c
    return candidates[0]


def resolve_sette_ref_dir(preferred: Optional[str] = None) -> str:
    """Resolves SETTE benchmark reference directory from environment or standard paths."""
    if preferred:
        return preferred
    if os.environ.get("SETTE_REF_DIR"):
        return os.environ["SETTE_REF_DIR"]
    repo_root = get_repo_root()
    workspace = get_default_workspace()
    candidates = []
    if workspace:
        candidates.append(os.path.join(workspace, "grids", "ORCA2", "sette_reference"))
    candidates.extend([
        os.path.join(repo_root, "sette_reference_ORCA2"),
        os.path.join(repo_root, "work_ORCA2", "sette_reference_ORCA2"),
    ])
    for rc in candidates:
        if os.path.exists(rc) and os.path.isdir(rc):
            return rc
    return candidates[0] if candidates else os.path.join(repo_root, "sette_reference_ORCA2")


def cmd_validate(args):
    repo_root = get_repo_root()
    preset = getattr(args, 'preset', 'official_sette')
    test_dir = resolve_output_dir("ORCA2", args.test_dir)
    ref_dir = resolve_sette_ref_dir(args.ref_dir)
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
    extra = [os.path.join(repo_root, "work_eORCA1", "reproduction_test")]
    test_dir = resolve_output_dir("eORCA1", args.test_dir, extra_candidates=extra)
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


def cmd_verify(args):
    from pisces_inidata.verify import verify_output_directory
    grid_name = getattr(args, 'grid', None) or getattr(args, 'orca', None) or "eORCA1"
    out_dir = resolve_output_dir(grid_name, args.out_dir)

    print(f"Inspecting PISCES inidata outputs for {grid_name} in: {out_dir}")
    exit_code, _ = verify_output_directory(out_dir, grid_name=grid_name)
    sys.exit(exit_code)


def cmd_info(args):
    repo_root = get_repo_root()
    cfg_file = getattr(args, 'config', None) or getattr(args, 'file', None) or os.path.join(repo_root, 'sources.yaml')
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
    cfg_file = getattr(args, 'config', None) or getattr(args, 'file', None) or os.path.join(repo_root, 'sources.yaml')
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


def cmd_grid_config(args):
    from pisces_inidata.grids import load_grid_config, export_grid_env_commands, load_all_grids
    grid_name = getattr(args, 'grid', None) or getattr(args, 'orca', None)
    config_file = getattr(args, 'config', None) or getattr(args, 'file', None)
    if not grid_name:
        all_grids = load_all_grids(config_file)
        print("Configured NEMO Target Grids:")
        for name, cfg in sorted(all_grids.items()):
            res = cfg.get("resources", {})
            print(f"  {name:10s}: {cfg.get('description', '')}")
            print(
                f"               Mem: {res.get('memory', '16G')}, Time: {res.get('time', '01:00:00')}, "
                f"Batch weights: {res.get('batch_weights', False)}"
            )
        return

    if getattr(args, 'export', False):
        print(export_grid_env_commands(grid_name, config_file))
    else:
        cfg = load_grid_config(grid_name, config_file)
        print(f"Target Grid Configuration ({grid_name}):")
        for k, v in sorted(cfg.items()):
            print(f"  {k}: {v}")


def cmd_platform_config(args):
    from pisces_inidata.platforms import (
        load_platform_config,
        export_platform_env_commands,
        load_all_platforms,
        detect_current_platform,
    )
    plat_name = getattr(args, 'platform', None)
    config_file = getattr(args, 'config', None) or getattr(args, 'file', None)
    if not plat_name and not getattr(args, 'export', False):
        all_plats = load_all_platforms(config_file)
        detected = detect_current_platform(config_file)
        print(f"Configured HPC Platforms (Active/Detected: {detected}):")
        for name, cfg in sorted(all_plats.items()):
            slurm = cfg.get("slurm", {})
            tag = " [ACTIVE]" if name == detected else ""
            print(f"  {name:10s}{tag}: {cfg.get('description', '')}")
            if slurm.get("account"):
                print(f"               Account: {slurm.get('account')}, Partition: {slurm.get('partition')}")
            if cfg.get("scratch_root"):
                print(f"               Scratch: {cfg.get('scratch_root')}")
        return

    if getattr(args, 'export', False):
        print(export_platform_env_commands(plat_name, config_file))
    else:
        cfg = load_platform_config(plat_name, config_file)
        print(f"Platform Configuration ({plat_name or detect_current_platform(config_file)}):")
        for k, v in sorted(cfg.items()):
            print(f"  {k}: {v}")


def cmd_download(args):
    from pisces_inidata.download import download_sources
    repo_root = get_repo_root()
    cfg_file = (
        getattr(args, 'config', None)
        or getattr(args, 'sources', None)
        or os.path.join(repo_root, 'sources.yaml')
    )
    raw_dir = args.raw_dir
    if not raw_dir:
        workspace = os.environ.get("PISCES_WORKSPACE")
        if workspace:
            raw_dir = os.path.join(workspace, "shared", "raw")
        elif os.environ.get("RAW_DIR"):
            raw_dir = os.environ["RAW_DIR"]
        elif os.path.isdir(os.path.join(repo_root, "pisces_raw_sources")):
            raw_dir = os.path.join(repo_root, "pisces_raw_sources")
        else:
            raw_dir = os.path.join(repo_root, "pisces_raw_sources")
    preset = getattr(args, 'preset', None)
    code = download_sources(config_file=cfg_file, raw_dir=raw_dir, dry_run=args.dry_run, preset=preset)
    if code != 0:
        sys.exit(code)

    if getattr(args, 'prepare', False) and not args.dry_run:
        print("\n=== Automatically running Stage 1 Source Standardization (hub04) ===")
        args.variable = "all"
        args.config = cfg_file
        cmd_prepare_sources(args)

    sys.exit(0)


def cmd_pad(args):
    pad_abyssal_depth(args.input, args.output, args.depth)


def cmd_check(args):
    repo_root = get_repo_root()
    cfg_file = args.config or os.path.join(repo_root, 'sources.yaml')
    preset = getattr(args, 'preset', None)
    grid_name = getattr(args, 'grid', None) or getattr(args, 'orca', 'ORCA2')
    code = run_preflight_checks(
        grid_name=grid_name,
        config_file=cfg_file,
        raw_dir=args.raw_dir,
        domain_dir=args.domain_dir,
        out_dir=args.out_dir,
        preset=preset
    )
    sys.exit(code)


def make_config_parent():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--config", "--file", dest="config", help="Path to custom sources.yaml")
    p.add_argument(
        "--preset",
        help="Configuration preset (default: ece4; e.g. ece4, ece3, official_sette, or custom)"
    )
    return p


def make_domain_parent():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument(
        "--domain-dir",
        help="Path to directory containing target NEMO domain files (${GRID_NAME}/domain_cfg.nc)"
    )
    return p


def make_dry_run_parent():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect sbatch job scripts without submitting"
    )
    return p


def add_grid_argument(parser, default="ORCA2", help_text=None):
    parser.add_argument(
        "--grid", "--orca",
        default=default,
        help=help_text or f"Target NEMO grid resolution (default: {default})"
    )


def main():
    parser = argparse.ArgumentParser(
        prog="pisces-inidata",
        description="Global Biogeochemical Initial Conditions Generator for PISCES and EC-Earth4"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: check
    check_parser = subparsers.add_parser(
        "check", parents=[make_config_parent(), make_domain_parent()],
        help="Run pre-flight system and data integrity verification"
    )
    add_grid_argument(check_parser, default="ORCA2", help_text="Target NEMO grid resolution to verify (default: ORCA2)")
    check_parser.add_argument("--raw-dir", help="Path to directory containing raw input products")
    check_parser.add_argument("--out-dir", help="Target output directory for free disk space check")
    check_parser.set_defaults(func=cmd_check)

    # Command: produce
    produce_parser = subparsers.add_parser(
        "produce", parents=[make_config_parent(), make_domain_parent(), make_dry_run_parent()],
        help="Produce PISCES initial conditions for target grid (defaults: eORCA1, stage2 parallel remapping)"
    )
    add_grid_argument(produce_parser, default="eORCA1")
    produce_parser.add_argument(
        "--stage", choices=["stage2", "all", "stage1"], default="stage2",
        help="Pipeline execution stage (default: stage2 [parallel remapping])"
    )
    produce_parser.set_defaults(func=cmd_produce)

    # Command: run
    run_parser = subparsers.add_parser(
        "run", parents=[make_config_parent(), make_domain_parent(), make_dry_run_parent()],
        help="Run end-to-end PISCES initial conditions generation"
    )
    add_grid_argument(run_parser, default="ORCA2")
    run_parser.add_argument(
        "--stage", choices=["all", "stage1", "stage2"], default="all",
        help="Pipeline execution stage: 'all' (default), 'stage1' (prepare sources), or 'stage2' (remap)"
    )
    run_parser.set_defaults(func=cmd_run)

    # Command: validate
    val_parser = subparsers.add_parser(
        "validate", help="Run procedure validation scorecard on ORCA2 vs SETTE benchmark"
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
        "test-reproduction", help="Run precision test verifying reproduction of EC-Earth3 baseline inidata on eORCA1"
    )
    rep_parser.add_argument(
        "--test-dir",
        help="Directory containing re-interpolated eORCA1 test files (default: output_eORCA1/)"
    )
    rep_parser.add_argument("--ref-dir", help="Directory containing official EC-Earth3 eORCA1 reference files")
    rep_parser.add_argument("--mask", help="Path to land-sea mask NetCDF file (maskutil.nc)")
    rep_parser.add_argument(
        "--preset",
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
    info_parser = subparsers.add_parser(
        "info", parents=[make_config_parent()],
        help="Display current configuration and environment status"
    )
    info_parser.set_defaults(func=cmd_info)

    # Command: config
    cfg_parser = subparsers.add_parser(
        "config", parents=[make_config_parent()],
        help="Inspect sources.yaml or export shell environment variables"
    )
    cfg_parser.add_argument("--export", action="store_true", help="Print bash export statements")
    cfg_parser.set_defaults(func=cmd_config)

    # Command: grid-config
    grid_cfg_parser = subparsers.add_parser(
        "grid-config", help="Inspect or export declarative grid profile from grids.yaml"
    )
    add_grid_argument(
        grid_cfg_parser, default=None,
        help_text="Target grid identifier (e.g. ORCA2, eORCA1, eORCA025, eORCA12)"
    )
    grid_cfg_parser.add_argument("--file", "--config", dest="config", help="Path to custom grids.yaml")
    grid_cfg_parser.add_argument("--export", action="store_true", help="Print bash export statements for grid")
    grid_cfg_parser.set_defaults(func=cmd_grid_config)

    # Command: platform-config
    plat_cfg_parser = subparsers.add_parser(
        "platform-config", help="Inspect HPC platform profile (Slurm, modules, scratch) or emit shell exports"
    )
    plat_cfg_parser.add_argument("--platform", help="Platform identifier (e.g. nord4, mn5, generic)")
    plat_cfg_parser.add_argument("--file", "--config", dest="config", help="Path to custom platforms.yaml")
    plat_cfg_parser.add_argument("--export", action="store_true", help="Print bash export statements for platform")
    plat_cfg_parser.set_defaults(func=cmd_platform_config)

    # Command: download
    dl_parser = subparsers.add_parser(
        "download", parents=[make_config_parent(), make_dry_run_parent()],
        help="Fetch and stage raw observational datasets based on sources.yaml"
    )
    dl_parser.add_argument("--sources", dest="config", help="Path to custom sources.yaml")
    dl_parser.add_argument("--raw-dir", help="Target directory to store raw sources")
    dl_parser.add_argument(
        "--prepare", action="store_true",
        help="Automatically run Stage 1 source standardization immediately after download"
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
    woa_parser.add_argument("var_code", help="Tracer code: n (NO3), p (PO4), i (Si), o (O2) [also accepts aliases]")
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
        "prepare-glodap", help="Standardize GLODAP vertical coordinate and pad to 6000m"
    )
    glodap_parser.add_argument("var_name", help="GLODAP variable name (TAlk, TCO2, PI_TCO2)")
    glodap_parser.add_argument("src_file", help="Path to raw GLODAP NetCDF file")
    glodap_parser.add_argument("out_file", help="Path to standardized output NetCDF file")
    glodap_parser.set_defaults(func=cmd_prepare_glodap)

    # Command: resolve-glodap
    res_glodap_parser = subparsers.add_parser("resolve-glodap", help="Resolve path to GLODAP NetCDF file")
    res_glodap_parser.add_argument("param", help="GLODAP parameter (TAlk, TCO2, PI_TCO2)")
    res_glodap_parser.add_argument("--raw-dir", help="Directory containing raw datasets")
    res_glodap_parser.add_argument("--version", help="GLODAP version hint (e.g. v2.2016b, v2.2023, v1)")
    res_glodap_parser.set_defaults(func=cmd_resolve_glodap)

    # Command: stamp
    stamp_parser = subparsers.add_parser("stamp", help="Apply CF provenance global attributes to NetCDF file")
    stamp_parser.add_argument("file", help="Path to NetCDF file to stamp")
    stamp_parser.add_argument("--grid", help="Target grid name (e.g. eORCA1)")
    stamp_parser.add_argument("--institution", help="Institution name")
    stamp_parser.add_argument("--preset", help="Configuration preset name")
    stamp_parser.set_defaults(func=cmd_stamp)

    # Command: prepare-sources (Stage 1 ETL)
    prep_src_parser = subparsers.add_parser(
        "prepare-sources", parents=[make_config_parent()],
        help="Stage 1 (Grid-Agnostic ETL): Format, pad, and standardize regular NetCDF sources"
    )
    prep_src_parser.add_argument(
        "variable", nargs="?", default="all",
        choices=[
            "all", "NO3", "PO4", "Si", "O2", "TALK", "TDIC", "PiDIC",
            "DOC", "Fer", "dust", "ndep", "par", "bathy", "hydrofe", "river"
        ],
        help="Variable or component to standardize (default: all)"
    )
    prep_src_parser.add_argument(
        "--force", action="store_true",
        help="Force regeneration even if standardized source file already exists"
    )
    prep_src_parser.set_defaults(func=cmd_prepare_sources)

    # Command: remap (Stage 2 Remap)
    remap_parser = subparsers.add_parser(
        "remap", parents=[make_config_parent(), make_domain_parent()],
        help="Stage 2 (Target Remap): Interpolate standardized source to target NEMO grid"
    )
    remap_parser.add_argument(
        "variable", nargs="?", default="all",
        choices=[
            "all", "NO3", "PO4", "Si", "O2", "TALK", "TDIC", "PiDIC",
            "DOC", "Fer", "dust", "ndep", "par", "bathy", "hydrofe", "river"
        ],
        help="Variable or component to remap (default: all)"
    )
    add_grid_argument(remap_parser, default="ORCA2")
    remap_parser.set_defaults(func=cmd_remap)

    # Command: verify
    verify_parser = subparsers.add_parser(
        "verify", help="Inspect output files, check shapes, physical min/mean/max, and ensure no blank files"
    )
    add_grid_argument(verify_parser, default="eORCA025")
    verify_parser.add_argument("--out-dir", help="Path to output directory to inspect (default: output_${GRID_NAME})")
    verify_parser.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
