"""
CLI Entry Point for pisces-inidata
Provides unified command-line commands for pipeline execution, padding, validation, and status.
"""

import sys
import os
import argparse
from typing import Optional, List
from pisces_inidata import __version__
from pisces_inidata.config import load_config, validate_config, export_env_commands, find_config_file
from pisces_inidata.padding import pad_abyssal_depth
from pisces_inidata.check import run_preflight_checks
from pisces_inidata.scoreboard import run_validation_suite
from pisces_inidata.reproduction import run_pipeline_reproduction_test


def get_repo_root() -> str:
    """Finds repository root path by traversing parent directories."""
    cur = os.path.dirname(os.path.abspath(__file__))
    while cur and cur != os.path.dirname(cur):
        if (
            os.path.exists(os.path.join(cur, 'pyproject.toml'))
            or os.path.exists(os.path.join(cur, '.git'))
            or (os.path.isdir(os.path.join(cur, 'config')) and os.path.isdir(os.path.join(cur, 'python')))
        ):
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


def get_pack_from_args(args, default: Optional[str] = "ece4") -> Optional[str]:
    """Helper to extract inidata pack with --preset and environment variable fallback."""
    val = getattr(args, 'pack', None) or getattr(args, 'preset', None)
    if val:
        return val
    return (
        os.environ.get("INIDATA_PACK")
        or os.environ.get("PACK")
        or os.environ.get("INIDATA_PRESET")
        or os.environ.get("PRESET")
        or default
    )


def cmd_stamp(args):
    from pisces_inidata.provenance import stamp_netcdf_provenance
    pack = get_pack_from_args(args, default=None)
    stamp_netcdf_provenance(
        args.file,
        grid_name=args.grid,
        institution=args.institution,
        pack=pack,
    )


def cmd_prepare_sources(args):
    from pisces_inidata.etl import standardize_source, standardize_all_sources
    pack = get_pack_from_args(args, default="ece4")
    force = getattr(args, 'force', False)
    var = getattr(args, 'variable', 'all')
    raw_dir = getattr(args, 'raw_dir', None)
    if not raw_dir:
        workspace = os.environ.get("PISCES_WORKSPACE")
        if workspace:
            raw_dir = os.path.join(workspace, "shared", "raw")
        elif os.environ.get("RAW_DIR"):
            raw_dir = os.environ["RAW_DIR"]
        elif os.path.isdir(os.path.join(get_repo_root(), "pisces_raw_sources")):
            raw_dir = os.path.join(get_repo_root(), "pisces_raw_sources")

    try:
        if var == "all":
            standardize_all_sources(pack=pack, force=force, raw_dir=raw_dir)
        else:
            standardize_source(var_name=var, pack=pack, force=force, raw_dir=raw_dir)
    except Exception as exc:
        print(f"\n[FAIL-FAST ERROR] Stage 1 source standardization failed: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_remap(args):
    from pisces_inidata.remap import remap_field, remap_all_fields
    grid_name = getattr(args, 'grid', None) or getattr(args, 'orca', None) or os.environ.get("GRID_NAME", "eORCA1")
    var = getattr(args, 'variable', None) or getattr(args, 'var', 'all')
    pack = get_pack_from_args(args, default="ece4")
    convention = getattr(args, 'convention', 'nemo4_ece4')
    force = getattr(args, 'force', False)
    domain_dir = getattr(args, 'domain_dir', None)
    out_dir = getattr(args, 'out_dir', None)
    threads = getattr(args, 'threads', None)

    try:
        if var == "all":
            remap_all_fields(
                grid_name=grid_name,
                pack=pack,
                convention=convention,
                force=force,
                domain_dir=domain_dir,
                out_dir=out_dir,
                threads=threads,
            )
        else:
            remap_field(
                var_name=var,
                grid_name=grid_name,
                pack=pack,
                convention=convention,
                force=force,
                domain_dir=domain_dir,
                out_dir=out_dir,
                threads=threads,
            )
    except Exception as exc:
        print(f"\n[FAIL-FAST ERROR] Stage 2 remapping failed: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_produce(args):
    from pisces_inidata.launcher import launch_pipeline
    grid_name = getattr(args, 'grid', None) or getattr(args, 'orca', None) or "eORCA1"
    pack = get_pack_from_args(args, default="ece4")
    convention = getattr(args, 'convention', 'nemo4_ece4')
    stage = getattr(args, 'stage', 'stage2')
    dry_run = getattr(args, 'dry_run', False)
    force = getattr(args, 'force', False)
    executor = getattr(args, 'executor', 'auto')
    jobs = getattr(args, 'jobs', 1)
    no_submit = getattr(args, 'no_submit', False)
    domain_dir = getattr(args, 'domain_dir', None)
    platform_name = getattr(args, 'platform', None)

    try:
        launch_pipeline(
            grid_name=grid_name,
            pack=pack,
            convention=convention,
            stage=stage,
            force=force,
            dry_run=dry_run,
            executor=executor,
            jobs=jobs,
            no_submit=no_submit,
            domain_dir=domain_dir,
            platform_name=platform_name,
        )
    except Exception as exc:
        print(f"\n[FAIL-FAST ERROR] Pipeline production failed: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_gen_weights(args):
    from pisces_inidata.weights import ensure_grid_and_weights
    grid_name = getattr(args, 'grid', None) or getattr(args, 'orca', None) or "eORCA1"
    domain_dir = getattr(args, 'domain_dir', None)
    weights_dir = getattr(args, 'weights_dir', None)
    raw_dir = getattr(args, 'raw_dir', None)
    force = getattr(args, 'force', False)

    try:
        ensure_grid_and_weights(
            grid_name=grid_name,
            domain_dir=domain_dir,
            weights_dir=weights_dir,
            raw_dir=raw_dir,
            force=force,
        )
    except Exception as exc:
        print(f"\n[FAIL-FAST ERROR] Weights generation failed: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_prepare_sette_reference(args):
    from pisces_inidata.reference import assemble_sette_reference_orca2
    raw_dir = getattr(args, 'raw_dir', None)
    out_dir = getattr(args, 'out_dir', None)
    force = getattr(args, 'force', False)

    try:
        assemble_sette_reference_orca2(raw_dir=raw_dir, out_dir=out_dir, force=force)
    except Exception as exc:
        print(f"\n[FAIL-FAST ERROR] SETTE reference assembly failed: {exc}", file=sys.stderr)
        sys.exit(1)


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
    pack = get_pack_from_args(args, default='official_sette')
    test_dir = resolve_output_dir("ORCA2", args.test_dir)
    ref_dir = resolve_sette_ref_dir(args.ref_dir)
    output_md = args.output_md or os.path.join(repo_root, "VALIDATION_SCOREBOARD_ORCA2.md")

    code = run_validation_suite(
        test_dir=test_dir,
        ref_dir=ref_dir,
        output_md=output_md,
        fail_on_error=args.fail_on_error,
        pack=pack
    )
    sys.exit(code)


def cmd_test_reproduction(args):
    repo_root = get_repo_root()
    pack = get_pack_from_args(args, default='official_sette')
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
        pack=pack
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
    cfg_file = getattr(args, 'config', None) or getattr(args, 'file', None)
    pack = get_pack_from_args(args, default=None)
    grid_name = getattr(args, 'grid', None) or getattr(args, 'orca', None)
    plat_name = getattr(args, 'platform', None)
    do_export = getattr(args, 'export', False)
    show_grids_only = getattr(args, 'grids', False)
    show_plats_only = getattr(args, 'platforms', False)

    from pisces_inidata.grids import load_grid_config, export_grid_env_commands, load_all_grids
    from pisces_inidata.platforms import (
        load_platform_config,
        export_platform_env_commands,
        load_all_platforms,
        detect_current_platform,
    )

    # 1. Export mode:
    if do_export:
        if grid_name:
            print(export_grid_env_commands(grid_name, cfg_file))
            return
        elif plat_name:
            print(export_platform_env_commands(plat_name, cfg_file))
            return
        else:
            resolved_cfg = cfg_file or os.path.join(repo_root, 'sources.yaml')
            config = load_config(resolved_cfg, pack=pack)
            print(export_env_commands(config))
            return

    # 2. Specific grid detailed inspection:
    if grid_name:
        cfg = load_grid_config(grid_name, cfg_file)
        print(f"Target Grid Configuration ({grid_name}):")
        for k, v in sorted(cfg.items()):
            print(f"  {k}: {v}")
        return

    # 3. Specific platform detailed inspection:
    if plat_name:
        cfg = load_platform_config(plat_name, cfg_file)
        print(f"Platform Configuration ({plat_name}):")
        for k, v in sorted(cfg.items()):
            print(f"  {k}: {v}")
        return

    # 4. Grids only list:
    if show_grids_only:
        all_grids = load_all_grids(cfg_file)
        print("Configured NEMO Target Grids:")
        for name, cfg in sorted(all_grids.items()):
            res = cfg.get("resources", {})
            print(f"  {name:10s}: {cfg.get('description', '')}")
            print(
                f"               Mem: {res.get('memory', '16G')}, Time: {res.get('time', '01:00:00')}, "
                f"Batch weights: {res.get('batch_weights', False)}"
            )
        return

    # 5. Platforms only list:
    if show_plats_only:
        all_plats = load_all_platforms(cfg_file)
        detected = detect_current_platform(cfg_file)
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

    # 6. Default: Unified Comprehensive Status
    config = load_config(cfg_file, pack=pack)
    valid = validate_config(config)

    print("=================================================================")
    print(f"  pisces-inidata v{__version__} - System, Configuration & Platform Status")
    print("=================================================================")
    print(f"Repository Root:     {repo_root}")
    conf_dir = os.path.join(repo_root, "config")
    if os.path.isdir(conf_dir):
        print(f"Config Directory:    {conf_dir}")
    active_pack = config.get('INIDATA_PACK', config.get('INIDATA_PRESET', 'ece4'))
    print(f"Active Pack:         {active_pack}")
    pack_path = find_config_file(f"packs/{active_pack}.yaml") or cfg_file
    if pack_path:
        print(f"Pack Config File:    {pack_path}")
    print(f"Configuration Valid: {'YES' if valid else 'WARNINGS DETECTED'}")

    print("\nConfigured Sources:")
    for k, v in sorted(config.items()):
        if k not in ('INIDATA_PACK', 'INIDATA_PRESET'):
            print(f"  {k:18s} = {v}")

    try:
        all_grids = load_all_grids(cfg_file)
        print("\nConfigured NEMO Target Grids:")
        for name, gcfg in sorted(all_grids.items()):
            res = gcfg.get("resources", {})
            print(f"  {name:10s}: {gcfg.get('description', '')}")
            print(
                f"               Mem: {res.get('memory', '16G')}, Time: {res.get('time', '01:00:00')}, "
                f"Batch weights: {res.get('batch_weights', False)}"
            )
    except Exception as exc:
        print(f"\nConfigured NEMO Target Grids: (Failed to load: {exc})")

    try:
        all_plats = load_all_platforms(cfg_file)
        detected = detect_current_platform(cfg_file)
        print(f"\nConfigured HPC Platforms (Active/Detected: {detected}):")
        for name, pcfg in sorted(all_plats.items()):
            slurm = pcfg.get("slurm", {})
            tag = " [ACTIVE]" if name == detected else ""
            print(f"  {name:10s}{tag}: {pcfg.get('description', '')}")
            if slurm.get("account"):
                print(f"               Account: {slurm.get('account')}, Partition: {slurm.get('partition')}")
            if pcfg.get("scratch_root"):
                print(f"               Scratch: {pcfg.get('scratch_root')}")
    except Exception as exc:
        print(f"\nConfigured HPC Platforms: (Failed to load: {exc})")

    print("=================================================================")


def _dispatch_grid_config(args):
    if not getattr(args, 'grid', None) and not getattr(args, 'orca', None) and not getattr(args, 'export', False):
        setattr(args, 'grids', True)
    return cmd_info(args)


def _dispatch_platform_config(args):
    if not getattr(args, 'platform', None) and not getattr(args, 'export', False):
        setattr(args, 'platforms', True)
    return cmd_info(args)


def cmd_grid_config(args):
    return _dispatch_grid_config(args)


def cmd_platform_config(args):
    return _dispatch_platform_config(args)


def cmd_config(args):
    cfg_file = getattr(args, 'config', None) or getattr(args, 'file', None)
    pack = get_pack_from_args(args, default=None)
    config = load_config(cfg_file, pack=pack)
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
    cfg_file = getattr(args, 'config', None) or getattr(args, 'sources', None)
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
    pack = get_pack_from_args(args, default=None)
    code = download_sources(config_file=cfg_file, raw_dir=raw_dir, dry_run=args.dry_run, pack=pack)
    if code != 0:
        sys.exit(code)

    if getattr(args, 'prepare', False) and not args.dry_run:
        print("\n=== Automatically running Stage 1 Source Standardization (hub04) ===", flush=True)
        args.variable = "all"
        args.config = cfg_file
        args.raw_dir = raw_dir
        cmd_prepare_sources(args)

    sys.exit(0)


def cmd_pad(args):
    pad_abyssal_depth(args.input, args.output, args.depth)


def cmd_check(args):
    cfg_file = getattr(args, 'config', None)
    pack = get_pack_from_args(args, default=None)
    grid_name = getattr(args, 'grid', None) or getattr(args, 'orca', 'ORCA2')
    code = run_preflight_checks(
        grid_name=grid_name,
        config_file=cfg_file,
        raw_dir=args.raw_dir,
        domain_dir=args.domain_dir,
        out_dir=args.out_dir,
        pack=pack
    )
    sys.exit(code)


def cmd_resolve_source(args):
    from pisces_inidata.catalog import resolve_source_field, export_source_env
    pack = get_pack_from_args(args, default=None)
    raw_dir = getattr(args, 'raw_dir', None)
    if getattr(args, 'export', False):
        print(export_source_env(args.variable, pack=pack, raw_dir=raw_dir))
    else:
        import json
        meta = resolve_source_field(args.variable, pack=pack, raw_dir=raw_dir)
        print(json.dumps(meta, indent=2))
    sys.exit(0)


def cmd_resolve_target(args):
    from pisces_inidata.catalog import resolve_target_field, export_target_env
    grid_name = getattr(args, 'grid', None) or getattr(args, 'orca', 'eORCA1')
    convention = getattr(args, 'convention', 'nemo4_ece4')
    if getattr(args, 'export', False):
        print(export_target_env(args.variable, grid_name, convention=convention))
    else:
        import json
        meta = resolve_target_field(args.variable, grid_name, convention=convention)
        print(json.dumps(meta, indent=2))
    sys.exit(0)


def cmd_get_vertical_levels(args):
    from pisces_inidata.catalog import get_target_vertical_levels
    grid_name = getattr(args, 'grid', None) or getattr(args, 'orca', 'ORCA2')
    domain_dir = getattr(args, 'domain_dir', None)
    raw_dir = getattr(args, 'raw_dir', None)
    levels = get_target_vertical_levels(grid_name, domain_dir=domain_dir, raw_dir=raw_dir)
    print(levels)
    sys.exit(0)


def cmd_catalog(args):
    from pisces_inidata.catalog import load_catalog, resolve_package_dir
    subcmd = getattr(args, 'subcommand', None)
    if subcmd == "package-dir":
        pkg_dir = resolve_package_dir(args.package_name, raw_dir=getattr(args, 'raw_dir', None))
        print(pkg_dir)
        sys.exit(0)
    import json
    cat = load_catalog()
    print(json.dumps(cat, indent=2))
    sys.exit(0)


def make_config_parent():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--config", "--file", dest="config", help="Path to custom sources.yaml")
    p.add_argument(
        "--pack", "--preset",
        dest="pack",
        help="Inidata source pack (default: ece4; e.g. ece4, ece3, official_sette, or custom)"
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


def main(argv=None):
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
        "produce", aliases=["run"],
        parents=[make_config_parent(), make_domain_parent(), make_dry_run_parent()],
        help="Produce PISCES initial conditions for target grid (defaults: eORCA1, stage2 parallel remapping)"
    )
    add_grid_argument(produce_parser, default="eORCA1")
    produce_parser.add_argument(
        "--stage", choices=["stage2", "all", "stage1", "weights"], default="stage2",
        help="Pipeline execution stage (default: stage2 [parallel remapping])"
    )
    produce_parser.add_argument(
        "--executor", choices=["auto", "slurm", "local"], default="auto",
        help="Pipeline executor mode: auto (slurm if available, else local), slurm, or local"
    )
    produce_parser.add_argument(
        "-j", "--jobs", type=int, default=1,
        help="Number of concurrent worker processes for local execution (default: 1 [sequential])"
    )
    produce_parser.add_argument(
        "--no-submit", action="store_true",
        help="Generate Slurm job array script without submitting it to sbatch"
    )
    produce_parser.add_argument(
        "--force", action="store_true",
        help="Force regeneration of files even if they already exist"
    )
    produce_parser.add_argument(
        "--convention", default="nemo4_ece4",
        help="Target model convention (default: nemo4_ece4)"
    )
    produce_parser.add_argument(
        "--platform", help="Platform profile to use for Slurm configuration (e.g. nord4, mn5)"
    )
    produce_parser.set_defaults(func=cmd_produce)

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
        "--pack", "--preset",
        dest="pack",
        default="official_sette",
        help="Inidata pack tested in validation (default: official_sette)"
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
        "--pack", "--preset",
        dest="pack",
        default="official_sette",
        help="Inidata pack tested for reproduction (default: official_sette)"
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

    # Command: info (Unified system, configuration, target grids, and HPC platforms inspection)
    info_parser = subparsers.add_parser(
        "info", parents=[make_config_parent()],
        help="Inspect system status, active source pack, target grids, and HPC platforms"
    )
    add_grid_argument(
        info_parser, default=None,
        help_text="Inspect specific target grid identifier (e.g. ORCA2, eORCA1, eORCA025, eORCA12)"
    )
    info_parser.add_argument("--grids", action="store_true", help="List all configured NEMO target grids")
    info_parser.add_argument("--platform", help="Inspect specific HPC platform profile (e.g. nord4, mn5, generic)")
    info_parser.add_argument("--platforms", action="store_true", help="List all configured HPC platform profiles")
    info_parser.add_argument(
        "--export", action="store_true",
        help="Print bash export statements for selected grid/platform/sources"
    )
    info_parser.set_defaults(func=cmd_info)

    # Command: config
    cfg_parser = subparsers.add_parser(
        "config", parents=[make_config_parent()],
        help="Inspect sources.yaml or export shell environment variables"
    )
    cfg_parser.add_argument("--export", action="store_true", help="Print bash export statements")
    cfg_parser.set_defaults(func=cmd_config)

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
    stamp_parser.add_argument("--pack", "--preset", dest="pack", help="Inidata pack name")
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
    prep_src_parser.add_argument("--raw-dir", help="Directory containing raw datasets")
    prep_src_parser.add_argument("--out-dir", help="Target directory for standardized source NetCDFs")
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
    remap_parser.add_argument(
        "-v", "--var", "--variable", dest="var", default=None,
        help="Variable or component to remap (alternative flag)"
    )
    add_grid_argument(remap_parser, default="ORCA2")
    remap_parser.add_argument(
        "--convention", default="nemo4_ece4",
        help="Target model convention (default: nemo4_ece4)"
    )
    remap_parser.add_argument(
        "--force", action="store_true",
        help="Force remapping even if output file already exists"
    )
    remap_parser.add_argument("--out-dir", help="Path to output directory for remapped files")
    remap_parser.add_argument("--threads", type=int, help="Number of CDO OpenMP worker threads")
    remap_parser.set_defaults(func=cmd_remap)

    # Command: gen-weights
    weights_parser = subparsers.add_parser(
        "gen-weights", parents=[make_domain_parent()],
        help="Generate target grid coordinates and SCRIP remapping weights"
    )
    add_grid_argument(weights_parser, default="eORCA1")
    weights_parser.add_argument("--weights-dir", help="Directory to store generated weights")
    weights_parser.add_argument("--raw-dir", help="Directory containing raw datasets")
    weights_parser.add_argument("--force", action="store_true", help="Force regeneration of weights")
    weights_parser.set_defaults(func=cmd_gen_weights)

    # Command: prepare-sette-reference
    sette_ref_parser = subparsers.add_parser(
        "prepare-sette-reference",
        help="Assemble official SETTE benchmark reference datasets on ORCA2"
    )
    sette_ref_parser.add_argument("--raw-dir", help="Directory containing raw datasets")
    sette_ref_parser.add_argument("--out-dir", help="Output directory for reference dataset")
    sette_ref_parser.add_argument("--force", action="store_true", help="Force reassembly")
    sette_ref_parser.set_defaults(func=cmd_prepare_sette_reference)

    # Command: verify
    verify_parser = subparsers.add_parser(
        "verify", help="Inspect output files, check shapes, physical min/mean/max, and ensure no blank files"
    )
    add_grid_argument(verify_parser, default="eORCA025")
    verify_parser.add_argument("--out-dir", help="Path to output directory to inspect (default: output_${GRID_NAME})")
    verify_parser.set_defaults(func=cmd_verify)

    # Command: resolve-source
    res_src_parser = subparsers.add_parser(
        "resolve-source", parents=[make_config_parent()],
        help="Resolve source dataset metadata, file paths, and variable mappings from catalog.yaml"
    )
    res_src_parser.add_argument("variable", help="Variable or forcing component (e.g. NO3, TALK, DOC, dust, river)")
    res_src_parser.add_argument("--raw-dir", help="Directory containing raw datasets")
    res_src_parser.add_argument("--export", action="store_true", help="Print bash export statements")
    res_src_parser.set_defaults(func=cmd_resolve_source)

    # Command: resolve-target
    res_tgt_parser = subparsers.add_parser(
        "resolve-target",
        help="Resolve target model output filenames, variables, and symlinks from catalog.yaml conventions"
    )
    res_tgt_parser.add_argument("variable", help="Variable or forcing component (e.g. NO3, TALK, DOC, dust, river)")
    add_grid_argument(res_tgt_parser, default="eORCA1")
    res_tgt_parser.add_argument(
        "--convention", default="nemo4_ece4",
        help="Target model convention (default: nemo4_ece4)"
    )
    res_tgt_parser.add_argument("--export", action="store_true", help="Print bash export statements")
    res_tgt_parser.set_defaults(func=cmd_resolve_target)

    # Command: get-vertical-levels
    levels_parser = subparsers.add_parser(
        "get-vertical-levels", parents=[make_domain_parent()],
        help="Extract vertical coordinate levels for target grid from domain_cfg.nc or catalog reference"
    )
    add_grid_argument(levels_parser, default="ORCA2")
    levels_parser.add_argument("--raw-dir", help="Directory containing raw datasets")
    levels_parser.set_defaults(func=cmd_get_vertical_levels)

    # Command: catalog
    cat_parser = subparsers.add_parser(
        "catalog",
        help="Inspect declarative dataset catalog and resolve package directories"
    )
    cat_sub = cat_parser.add_subparsers(dest="subcommand")
    cat_pkg = cat_sub.add_parser("package-dir", help="Resolve external package directory path")
    cat_pkg.add_argument("package_name", help="Package name (e.g. official_nemo_inputs)")
    cat_pkg.add_argument("--raw-dir", help="Directory containing raw datasets")
    cat_parser.set_defaults(func=cmd_catalog)

    if argv is None:
        argv = sys.argv[1:]
    else:
        argv = list(argv)

    # Transparent backward compatibility: grid-config and platform-config redirect to info
    if argv and argv[0] == "grid-config":
        argv[0] = "info"
        if not any(arg in argv for arg in ("--grid", "-g", "--orca", "--export")):
            argv.append("--grids")
    elif argv and argv[0] == "platform-config":
        argv[0] = "info"
        if not any(arg in argv for arg in ("--platform", "-p", "--export")):
            argv.append("--platforms")

    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
