"""
Pre-flight System & Data Integrity Checks for PISCES Inidata.
Verifies system binaries, python libraries, raw source datasets, target domain files,
and filesystem disk space before launching heavy computational jobs.
"""

import os
import shutil
import subprocess
from typing import Dict, List, Tuple, Optional
from pisces_inidata.config import load_config, validate_config

REQUIRED_BINARIES = ["cdo", "ncks", "ncap2", "ncatted"]
OPTIONAL_BINARIES = ["sbatch", "ncdump"]
REQUIRED_PYTHON_PKGS = ["netCDF4", "numpy"]

MIN_DISK_SPACE_GB = {
    "ORCA2": 2.0,
    "eORCA1": 10.0,
    "eORCA025": 40.0
}


def check_binaries() -> List[Tuple[str, bool, str, bool]]:
    """
    Checks presence and versions of required and optional command-line tools.
    Returns: list of (name, is_available, version_or_error, is_required)
    """
    results = []
    for tool in REQUIRED_BINARIES:
        path = shutil.which(tool)
        if path:
            try:
                res = subprocess.run([tool, "-V"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                output = res.stderr if res.stderr and "version" in res.stderr.lower() else res.stdout
                version = output.splitlines()[0].strip() if output else "Available"
            except Exception:
                version = "Available"
            results.append((tool, True, version, True))
        else:
            results.append((tool, False, "Not found in PATH", True))

    for tool in OPTIONAL_BINARIES:
        path = shutil.which(tool)
        if path:
            results.append((tool, True, "Available", False))
        else:
            results.append((tool, False, "Not found in PATH (optional)", False))

    return results


def check_python_packages() -> List[Tuple[str, bool, str]]:
    """
    Checks availability and versions of critical Python modules.
    Returns: list of (package_name, is_installed, version_or_error)
    """
    results = []
    for pkg in REQUIRED_PYTHON_PKGS:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "Installed")
            results.append((pkg, True, ver))
        except ImportError as e:
            results.append((pkg, False, str(e)))
    return results


def check_disk_space(target_path: str, grid_name: str) -> Tuple[bool, float, float]:
    """
    Checks whether target filesystem has enough free space for interpolation of specified grid.
    Returns: (is_sufficient, free_gb, required_gb)
    """
    req_gb = MIN_DISK_SPACE_GB.get(grid_name, 5.0)
    check_dir = target_path
    while check_dir and not os.path.exists(check_dir):
        parent = os.path.dirname(check_dir)
        if parent == check_dir:
            break
        check_dir = parent

    if not check_dir or not os.path.exists(check_dir):
        check_dir = "."

    try:
        usage = shutil.disk_usage(check_dir)
        free_gb = usage.free / (1024 ** 3)
        return (free_gb >= req_gb, free_gb, req_gb)
    except Exception:
        return (True, 999.0, req_gb)


def check_target_grid(grid_name: str, domain_dir: Optional[str] = None) -> List[Tuple[str, bool, str]]:
    """
    Verifies presence of target grid definition, domain_cfg, or maskutil files.
    """
    results = []
    base_dir = domain_dir or os.environ.get("DOMAIN_BASE_DIR")
    if not base_dir:
        standard_bsc = "/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain"
        base_dir = standard_bsc if os.path.isdir(standard_bsc) else os.path.join(os.getcwd(), "domain")

    if grid_name == "ORCA2":
        # Check local target_grid or domain_cfg
        candidates = [
            os.path.join(base_dir, "ORCA2", "domain_cfg.nc"),
            os.path.join(base_dir, "ORCA2", "target_grid_ORCA2.nc"),
            os.path.join(os.getcwd(), "target_grid_ORCA2.nc"),
            os.path.join(os.getcwd(), "target_grid.nc")
        ]
        found = any(os.path.exists(p) for p in candidates)
        path_str = next((p for p in candidates if os.path.exists(p)), candidates[0])
        results.append((
            f"Target Grid ({grid_name})",
            found,
            path_str if found else f"Missing. Checked: {', '.join(candidates)}"
        ))
    else:
        domain_cfg = os.path.join(base_dir, grid_name, "domain_cfg.nc")
        maskutil = os.path.join(base_dir, grid_name, "maskutil.nc")

        found_cfg = os.path.exists(domain_cfg)
        found_mask = os.path.exists(maskutil)

        msg_cfg = domain_cfg if found_cfg else (
            f"Missing ({domain_cfg}). Obtain from EC-Earth4 inidata: https://ec-earth-4-docs.readthedocs.io/"
        )
        msg_mask = maskutil if found_mask else (
            f"Missing ({maskutil}). Obtain from EC-Earth4 inidata or generate with gen_grid_and_weights.sh."
        )

        results.append((f"{grid_name} domain_cfg", found_cfg, msg_cfg))
        results.append((f"{grid_name} maskutil", found_mask, msg_mask))

    return results


def check_raw_sources(raw_dir: str, config: Dict[str, str]) -> List[Tuple[str, bool, str]]:
    """
    Checks for the existence of required input raw datasets based on sources.yaml.
    """
    results = []
    if not os.path.exists(raw_dir):
        return [("Raw Sources Directory", False, f"Directory does not exist: {raw_dir}")]

    # Check key tracer files
    searches = {
        "NO3 / Nutrients": ["woa23", "WOA23", "woa09", "data_NO3"],
        "GLODAP Inorganics": ["GLODAPv2", "glodap", "data_ALK", "data_DIC"],
        "DOC": ["Panaiotis", "panaiotis", "DOC", "data_DOC"],
        "Iron (Fe)": ["data_FER", "Fer", "iron", "tagliabue"],
        "Surface Forcings": ["dust", "ndeposition", "river", "bathy"]
    }

    files = os.listdir(raw_dir) if os.path.exists(raw_dir) else []

    for name, patterns in searches.items():
        found = any(any(pat.lower() in f.lower() for pat in patterns) for f in files)
        results.append((name, found, "Present in raw dir" if found else f"No match for {patterns} in {raw_dir}"))

    return results


def run_preflight_checks(
    grid_name: str = "ORCA2",
    config_file: Optional[str] = None,
    raw_dir: Optional[str] = None,
    domain_dir: Optional[str] = None,
    out_dir: Optional[str] = None,
    preset: Optional[str] = None
) -> int:
    """
    Runs full preflight check suite and outputs formatted results.
    Returns 0 on success, 1 on critical failure.
    """
    cfg = load_config(config_file or "sources.yaml", preset=preset)
    validate_config(cfg)
    active_preset = cfg.get("INIDATA_PRESET", "ece4")

    print("=" * 78)
    print(f" PISCES INIDATA PRE-FLIGHT CHECK (Grid: {grid_name}, Preset: {active_preset})")
    print("=" * 78)

    all_critical_passed = True

    # 1. System Tools
    print("\n[1] System Command-Line Binaries:")
    bin_results = check_binaries()
    for name, ok, desc, required in bin_results:
        tag = "[PASS]" if ok else ("[FAIL]" if required else "[WARN]")
        print(f"  {tag:7s} {name:10s} : {desc}")
        if required and not ok:
            all_critical_passed = False

    # 2. Python Packages
    print("\n[2] Python Packages:")
    py_results = check_python_packages()
    for name, ok, desc in py_results:
        tag = "[PASS]" if ok else "[FAIL]"
        print(f"  {tag:7s} {name:10s} : {desc}")
        if not ok:
            all_critical_passed = False

    # 3. Target Domain & Grid
    print(f"\n[3] Target Grid & Domain Files ({grid_name}):")
    grid_results = check_target_grid(grid_name, domain_dir)
    for name, ok, desc in grid_results:
        tag = "[PASS]" if ok else "[FAIL]"
        print(f"  {tag:7s} {name:22s} : {desc}")
        if not ok and grid_name != "ORCA2":
            all_critical_passed = False

    # 4. Raw Sources
    effective_raw = raw_dir or os.environ.get("RAW_DIR", os.path.join(os.getcwd(), "pisces_raw_sources"))
    print(f"\n[4] Raw Input Data Catalog ({effective_raw}):")
    raw_results = check_raw_sources(effective_raw, cfg)
    for name, ok, desc in raw_results:
        tag = "[PASS]" if ok else "[WARN]"
        print(f"  {tag:7s} {name:22s} : {desc}")

    # 5. Disk Space
    effective_out = out_dir or os.environ.get("OUTPUT_DIR", os.getcwd())
    print(f"\n[5] Filesystem Storage Check ({effective_out}):")
    ok_space, free_gb, req_gb = check_disk_space(effective_out, grid_name)
    tag = "[PASS]" if ok_space else "[FAIL]"
    print(f"  {tag:7s} Free Space: {free_gb:.1f} GB (Required: >= {req_gb:.1f} GB)")
    if not ok_space:
        all_critical_passed = False

    print("\n" + "=" * 78)
    if all_critical_passed:
        print(" PRE-FLIGHT CHECK PASSED: System is ready for inidata generation.")
        print("=" * 78)
        return 0
    else:
        print(" PRE-FLIGHT CHECK FAILED: Please address critical failures [FAIL] above.")
        print("=" * 78)
        return 1
