"""
Declarative Dataset Catalog & Conventions Module for PISCES Inidata.
Loads catalog.yaml as the single source of truth for:
  - Input raw packages and directory locations (resilient to upstream directory/archive changes)
  - Observational and reference source products (file patterns, raw variable names, pad depths)
  - Target model conventions (output filenames, target variable names, namelist symlinks)
"""

import os
import yaml
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pisces_inidata.config import find_config_file


_CATALOG_CACHE: Optional[Dict[str, Any]] = None


def find_catalog_yaml(custom_path: Optional[str] = None) -> Optional[str]:
    """Resolves path to catalog.yaml."""
    return find_config_file("catalog.yaml", env_var="PISCES_CATALOG", custom_path=custom_path)


def load_catalog(custom_path: Optional[str] = None, force_reload: bool = False) -> Dict[str, Any]:
    """Loads and caches catalog.yaml."""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None and not force_reload and custom_path is None:
        return _CATALOG_CACHE

    catalog_path = find_catalog_yaml(custom_path)
    if not catalog_path or not os.path.isfile(catalog_path):
        raise FileNotFoundError("catalog.yaml not found in repository root or search paths.")

    with open(catalog_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    if custom_path is None:
        _CATALOG_CACHE = data
    return data


def resolve_package_dir(
    package_name: str,
    raw_dir: Optional[str] = None,
    catalog: Optional[Dict[str, Any]] = None
) -> str:
    """
    Resolves the directory path for an external package (e.g. official_nemo_inputs).
    Supports environment variable overrides (e.g. OFFICIAL_INPUTS_DIR) and sources.yaml configuration.
    """
    cat = catalog or load_catalog()
    pkg_cfg = cat.get("packages", {}).get(package_name, {})

    env_var = pkg_cfg.get("env_override")
    if env_var and os.environ.get(env_var):
        return os.environ[env_var]

    default_sub = pkg_cfg.get("default_dir", package_name)
    base_raw = raw_dir or os.environ.get("RAW_DIR")
    if not base_raw:
        workspace = os.environ.get("PISCES_WORKSPACE")
        base_raw = (
            os.path.join(workspace, "shared", "raw")
            if workspace
            else os.path.join(os.getcwd(), "pisces_raw_sources")
        )

    # Check if directory exists directly in raw_dir
    candidate = os.path.join(base_raw, default_sub)
    if os.path.isdir(candidate):
        return candidate

    # Check if files were unpacked directly into base_raw
    key_file = pkg_cfg.get("key_file")
    if key_file and os.path.isfile(os.path.join(base_raw, key_file)):
        return base_raw

    return candidate


def resolve_source_field(
    var_name: str,
    pack: Optional[str] = None,
    preset: Optional[str] = None,
    raw_dir: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    catalog: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Resolves all source metadata for a 3D tracer or boundary forcing field.
    Returns:
      - var: Canonical variable name (e.g. NO3, TALK, dust, hydrofe)
      - product: Selected product key (e.g. woa23, glodap_v2_2016b, sette_nomask, sette_orca2)
      - handler: Special preparation handler ('woa23', 'glodap', 'doc', or 'generic')
      - src_file: Full path to raw source file (or intermediate directory)
      - src_var: Internal variable name inside the raw file
      - std_var: Variable name inside the standardized Stage 1 file
      - pad_depth: Bottom depth limit in meters (e.g. 6000.0) or None
      - fillmiss: Boolean indicating whether cdo fillmiss should be executed
      - vars_list: List of sub-variables (for multi-variable boundary forcings)
      - coords_source_file: Path to coordinates donor file if needed (e.g. bathy for river)
      - remapping: Remapping method ('bilinear', 'nearest_neighbor', 'distance_conservative')
    """
    cat = catalog or load_catalog()
    from pisces_inidata.config import load_config
    cfg = config or load_config(pack=pack or preset)

    # Determine product key from config
    product_key = cfg.get(f"PRODUCT_{var_name}") or cfg.get(f"PRODUCT_{var_name.upper()}")
    if not product_key and var_name.lower() in ("river", "rivers"):
        product_key = cfg.get("PRODUCT_RIVER")

    # Default product fallback if not in config
    if not product_key:
        if var_name in ("NO3", "PO4", "Si", "O2"):
            product_key = "woa23"
        elif var_name in ("TALK", "TDIC", "PiDIC"):
            product_key = "glodap_v2_2016b"
        elif var_name == "DOC":
            product_key = "panaiotis2024"
        elif var_name == "Fer":
            product_key = "sette_nomask"
        else:
            product_key = "sette_orca2"

    src_dict = cat.get("sources", {}).get(product_key, {})
    handler = src_dict.get("handler", "generic")
    pkg_name = src_dict.get("package")
    pkg_dir = resolve_package_dir(pkg_name, raw_dir=raw_dir, catalog=cat) if pkg_name else ""

    # Check if 3D tracer
    tracers = src_dict.get("tracers", {})
    if var_name in tracers:
        t_meta = tracers[var_name]
        src_var = t_meta.get("var", t_meta.get("raw_var", var_name))
        pad_depth = t_meta.get("pad_depth")
        fillmiss = t_meta.get("fillmiss", False)

        # Standard variable naming convention in intermediate standardized source
        std_var = var_name
        if var_name == "TALK":
            std_var = "Alkalini"
        elif var_name in ("TDIC", "PiDIC"):
            std_var = "DIC"

        # Resolve file path
        if handler == "woa23":
            base_raw = raw_dir or os.environ.get("RAW_DIR")
            if not base_raw:
                workspace = os.environ.get("PISCES_WORKSPACE")
                base_raw = (
                    os.path.join(workspace, "shared", "raw")
                    if workspace
                    else os.path.join(os.getcwd(), "pisces_raw_sources")
                )
            src_file = os.path.join(base_raw, "woa23")
        elif handler == "glodap":
            from pisces_inidata.glodap import resolve_glodap_source
            param = t_meta.get("param", src_var)
            ver_hint = src_dict.get("version_hint", "v2.2016b")
            effective_raw = raw_dir or os.environ.get("RAW_DIR", os.path.join(os.getcwd(), "pisces_raw_sources"))
            try:
                src_file = str(resolve_glodap_source(param, effective_raw, version_hint=ver_hint))
            except Exception:
                # Fallback to direct path candidate
                sub = src_dict.get("dir", "glodap_v2")
                src_file = os.path.join(effective_raw, sub, f"GLODAP{ver_hint}.{param}.nc")
        elif handler == "doc":
            effective_raw = raw_dir or os.environ.get("RAW_DIR", os.path.join(os.getcwd(), "pisces_raw_sources"))
            doc_dir = src_dict.get("dir", "panaiotis2024_doc")
            doc_file = t_meta.get("file", "panaiotis2024_doc_1deg.nc")
            src_file = os.path.join(effective_raw, doc_dir, doc_file)
        else:
            fname = t_meta.get("file", f"data_{var_name}_nomask.nc")
            src_file = os.path.join(pkg_dir, fname)

        return {
            "var": var_name,
            "product": product_key,
            "handler": handler,
            "src_file": src_file,
            "src_var": src_var,
            "std_var": std_var,
            "pad_depth": pad_depth,
            "fillmiss": fillmiss,
            "vars_list": [std_var],
            "coords_source_file": "",
            "remapping": "bilinear",
        }

    # Check if boundary forcing
    forcings = src_dict.get("forcings", {})
    canon_var = "rivers" if var_name in ("river", "rivers") else var_name
    if canon_var in forcings:
        f_meta = forcings[canon_var]
        candidates = f_meta.get("candidate_files", [f_meta.get("file", f"{canon_var}.orca.nc")])
        src_file = os.path.join(pkg_dir, candidates[0])
        for c in candidates:
            cand_path = os.path.join(pkg_dir, c)
            if os.path.isfile(cand_path):
                src_file = cand_path
                break

        vars_list = f_meta.get("variables", [canon_var])
        src_var = vars_list[0]
        remapping = f_meta.get("remapping", "bilinear")
        coords_file = ""
        if f_meta.get("coords_source_file"):
            coords_file = os.path.join(pkg_dir, f_meta["coords_source_file"])

        return {
            "var": canon_var,
            "product": product_key,
            "handler": "forcing",
            "src_file": src_file,
            "src_var": src_var,
            "std_var": src_var,
            "pad_depth": None,
            "fillmiss": False,
            "vars_list": vars_list,
            "coords_source_file": coords_file,
            "remapping": remapping,
        }

    raise KeyError(f"Unknown variable or forcing field '{var_name}' for product '{product_key}' in catalog.yaml")


def resolve_target_field(
    var_name: str,
    grid_name: str,
    convention: str = "nemo4_ece4",
    catalog: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Resolves the target model output conventions for a given field and grid.
    Returns:
      - out_file: formatted output filename (e.g. 'data_TALK_eORCA1.nc')
      - target_var: variable name expected inside the file (e.g. 'Alkalini')
      - units: physical units string
      - symlinks: list of symlink filenames to create for namelist compatibility
    """
    cat = catalog or load_catalog()
    conv_dict = cat.get("conventions", {}).get(convention, {})
    if not conv_dict:
        # Fallback to default convention
        conv_dict = cat.get("conventions", {}).get("nemo4_ece4", {})

    fields = conv_dict.get("fields", {})
    lookup_var = var_name
    if lookup_var not in fields and lookup_var in ("river", "rivers"):
        lookup_var = "rivers" if "rivers" in fields else "river"

    if lookup_var not in fields:
        raise KeyError(f"Field '{var_name}' not defined in convention '{convention}' in catalog.yaml")

    f_meta = fields[lookup_var]
    raw_out = f_meta.get("output_file", f"data_{var_name}_{{grid}}.nc")
    out_file = raw_out.format(grid=grid_name)
    target_var = f_meta.get("target_var", var_name)
    units = f_meta.get("units", "")

    raw_symlinks = f_meta.get("symlinks", [])
    symlinks = [s.format(grid=grid_name) for s in raw_symlinks]

    return {
        "out_file": out_file,
        "target_var": target_var,
        "units": units,
        "symlinks": symlinks,
    }


def get_target_vertical_levels(
    grid_name: str,
    domain_dir: Optional[str] = None,
    raw_dir: Optional[str] = None,
    catalog: Optional[Dict[str, Any]] = None
) -> str:
    """
    Extracts comma-separated vertical levels for target grid.
    First checks domain_cfg.nc for nav_lev. If missing, resolves reference 3D tracer
    from catalog.yaml and extracts levels via cdo showlevel.
    """
    base_domain = domain_dir or os.environ.get("DOMAIN_BASE_DIR") or os.path.join(os.getcwd(), "domain")
    if base_domain:
        domain_cfg = os.path.join(base_domain, grid_name, "domain_cfg.nc")
        if os.path.isfile(domain_cfg):
            try:
                import netCDF4 as nc
                with nc.Dataset(domain_cfg, "r") as ds:
                    if "nav_lev" in ds.variables:
                        levels = [str(float(x)) for x in ds.variables["nav_lev"][:].flatten()]
                        return ",".join(levels)
            except Exception:
                pass
            try:
                res = subprocess.run(
                    ["ncks", "-s", "%f,", "-H", "-C", "-v", "nav_lev", domain_cfg],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5
                )
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip().rstrip(",")
            except Exception:
                pass

    # Fallback to reference 3D tracer from official inputs package
    cat = catalog or load_catalog()
    pkg_dir = resolve_package_dir("official_nemo_inputs", raw_dir=raw_dir, catalog=cat)
    ref_file = os.path.join(pkg_dir, "data_DOC_nomask.nc")
    if not os.path.isfile(ref_file):
        ref_file = os.path.join(pkg_dir, "data_NO3_nomask.nc")

    if os.path.isfile(ref_file):
        try:
            res = subprocess.run(
                ["cdo", "-s", "showlevel", ref_file],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5
            )
            if res.returncode == 0 and res.stdout.strip():
                # Format whitespace separated levels as comma-separated
                levels = res.stdout.strip().split()
                return ",".join(levels)
        except Exception:
            pass

    return ""


def get_expected_products(grid_name: str, convention: str = "nemo4_ece4") -> List[Tuple[str, str]]:
    """Returns list of (expected_output_filename, expected_target_variable) for verify.py."""
    cat = load_catalog()
    conv = cat.get("conventions", {}).get(convention, {})
    fields = conv.get("fields", {})
    results = []
    seen = set()
    for var, meta in fields.items():
        fname = meta.get("output_file", f"data_{var}_{{grid}}.nc").format(grid=grid_name)
        if fname not in seen:
            seen.add(fname)
            results.append((fname, meta.get("target_var", var)))
    return results


def export_source_env(
    var_name: str,
    pack: Optional[str] = None,
    preset: Optional[str] = None,
    raw_dir: Optional[str] = None
) -> str:
    """Exports shell variable definitions for Stage 1 prepare_standard_sources.sh."""
    meta = resolve_source_field(var_name, pack=pack or preset, raw_dir=raw_dir)
    lines = [
        f"export VAR=\"{meta['var']}\"",
        f"export PRODUCT=\"{meta['product']}\"",
        f"export HANDLER=\"{meta['handler']}\"",
        f"export SRC_FILE=\"{meta['src_file']}\"",
        f"export SRC_VAR=\"{meta['src_var']}\"",
        f"export STD_VAR=\"{meta['std_var']}\"",
        f"export PAD_DEPTH=\"{meta['pad_depth'] or ''}\"",
        f"export FILLMISS=\"{1 if meta['fillmiss'] else 0}\"",
        f"export REMAP_METHOD=\"{meta['remapping']}\"",
        f"export COORDS_SOURCE_FILE=\"{meta['coords_source_file']}\"",
        f"export VARS_LIST=\"{' '.join(meta['vars_list'])}\"",
    ]
    return "\n".join(lines)


def export_target_env(var_name: str, grid_name: str, convention: str = "nemo4_ece4") -> str:
    """Exports shell variable definitions for Stage 2 remap_field.sh."""
    meta = resolve_target_field(var_name, grid_name, convention=convention)
    lines = [
        f"export OUT_FILE=\"{meta['out_file']}\"",
        f"export TARGET_VAR=\"{meta['target_var']}\"",
        f"export TARGET_UNITS=\"{meta['units']}\"",
        f"export TARGET_SYMLINKS=\"{' '.join(meta['symlinks'])}\"",
    ]
    return "\n".join(lines)
