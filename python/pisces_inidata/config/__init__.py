"""
Configuration Module for PISCES Inidata.
Loads sources.yaml, applies configuration presets (ece4, ece3, official_sette), validates
source climatology choices, rejects invalid ece3 sources, and exports environment
variables for pipeline shell scripts.
"""

import os
import yaml
from typing import Dict, Optional


YAML_MAP = {
    ('tracers_3d', 'NO3'): 'PRODUCT_NO3',
    ('tracers_3d', 'PO4'): 'PRODUCT_PO4',
    ('tracers_3d', 'Si'): 'PRODUCT_Si',
    ('tracers_3d', 'O2'): 'PRODUCT_O2',
    ('tracers_3d', 'TALK'): 'PRODUCT_TALK',
    ('tracers_3d', 'TDIC'): 'PRODUCT_TDIC',
    ('tracers_3d', 'PiDIC'): 'PRODUCT_PiDIC',
    ('tracers_3d', 'DOC'): 'PRODUCT_DOC',
    ('tracers_3d', 'Fer'): 'PRODUCT_Fer',
    ('boundary_forcings', 'dust'): 'PRODUCT_DUST',
    ('boundary_forcings', 'ndep'): 'PRODUCT_NDEP',
    ('boundary_forcings', 'par'): 'PRODUCT_PAR',
    ('boundary_forcings', 'bathy'): 'PRODUCT_BATHY',
    ('boundary_forcings', 'hydrofe'): 'PRODUCT_HYDROFE',
    ('boundary_forcings', 'rivers'): 'PRODUCT_RIVER',
}


def _load_packs() -> Dict[str, Dict[str, str]]:
    pkg_cfg_dir = os.path.dirname(os.path.abspath(__file__))
    packs_dir = os.path.join(pkg_cfg_dir, "packs")
    loaded = {}
    if os.path.isdir(packs_dir):
        for fname in sorted(os.listdir(packs_dir)):
            if fname.endswith((".yaml", ".yml")):
                pname = fname.replace("sources_", "").replace(".yaml", "").replace(".yml", "")
                with open(os.path.join(packs_dir, fname), "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                pack_dict = {}
                for section in ("tracers_3d", "boundary_forcings"):
                    for k, v in data.get(section, {}).items():
                        mapped = YAML_MAP.get((section, k))
                        if mapped:
                            pack_dict[mapped] = v
                if pack_dict:
                    loaded[pname] = pack_dict
    return loaded


PACKS = _load_packs()
PRESETS = PACKS
DEFAULTS = PACKS.get('ece4', {}).copy()

VALID_SOURCES = {
    'PRODUCT_NO3': ['woa23', 'woa2009', 'sette_nomask'],
    'PRODUCT_PO4': ['woa23', 'woa2009', 'sette_nomask'],
    'PRODUCT_Si': ['woa23', 'woa2009', 'sette_nomask'],
    'PRODUCT_O2': ['woa23', 'woa2009', 'sette_nomask'],
    'PRODUCT_TALK': [
        'glodap_v2_2016b', 'glodap_v2_2023', 'glodap_v1', 'sette_nomask', 'cmems'
    ],
    'PRODUCT_TDIC': [
        'glodap_v2_2016b', 'glodap_v2_2023', 'glodap_v1', 'sette_nomask', 'cmems'
    ],
    'PRODUCT_PiDIC': [
        'glodap_v2_2016b', 'glodap_v2_2023', 'glodap_v1', 'sette_nomask', 'cmems'
    ],
    'PRODUCT_DOC': ['panaiotis2024', 'sette_nomask'],
    'PRODUCT_Fer': ['sette_nomask'],
    'PRODUCT_DUST': ['sette_orca2'],
    'PRODUCT_NDEP': ['sette_orca2'],
    'PRODUCT_PAR': ['sette_orca2'],
    'PRODUCT_BATHY': ['sette_orca2'],
    'PRODUCT_HYDROFE': ['sette_orca2'],
    'PRODUCT_RIVER': ['sette_orca2'],
}


DEFAULT_TRACERS_3D = ["NO3", "PO4", "Si", "O2", "TALK", "TDIC", "PiDIC", "DOC", "Fer"]
DEFAULT_BOUNDARY_FORCINGS = ["dust", "ndep", "par", "bathy", "hydrofe", "rivers"]
DEFAULT_RIVER_VARS = ["riverdin", "riverdip", "riverdon", "riverdop", "riverdoc", "riverdsi", "riverdic"]
DEFAULT_DUST_VARS = ["dust", "dustfer", "dustpo4", "dustsi", "solubility2"]
DEFAULT_NDEP_VARS = ["ndep", "ndep2"]


def get_config_dir() -> str:
    """Returns absolute path to bundled config directory."""
    return os.path.dirname(os.path.abspath(__file__))


def find_config_file(
    filename: str,
    env_var: Optional[str] = None,
    custom_path: Optional[str] = None,
) -> Optional[str]:
    """Resolves path to a bundled or overridden configuration YAML file."""
    candidates = [
        custom_path,
        os.environ.get(env_var) if env_var else None,
        os.path.join(os.getcwd(), filename),
    ]
    try:
        from importlib.resources import files
        bundled = str(files("pisces_inidata.config").joinpath(filename))
        candidates.append(bundled)
    except Exception:
        pass

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates.append(os.path.join(repo_root, filename))

    for c in candidates:
        if c and os.path.exists(c) and not os.path.isdir(c):
            return c
    return None


def resolve_pack_name(pack: Optional[str]) -> str:
    """Normalizes inidata pack name; defaults to ece4."""
    if not pack:
        return 'ece4'
    return pack.strip().lower()


resolve_preset_name = resolve_pack_name


def load_config(
    config_path: str = "sources.yaml",
    pack: Optional[str] = None,
    preset: Optional[str] = None,
) -> Dict[str, str]:
    """
    Loads product configuration from inidata pack and sources.yaml or environment variables.
    """
    pkg_config_dir = get_config_dir()
    repo_root = os.path.dirname(os.path.dirname(pkg_config_dir))
    explicit_pack = (
        pack
        or preset
        or os.environ.get('PISCES_PACK')
        or os.environ.get('PACK')
        or os.environ.get('INIDATA_PACK')
        or os.environ.get('PRESET')
        or os.environ.get('INIDATA_PRESET')
    )
    norm_explicit = resolve_pack_name(explicit_pack) if explicit_pack else None

    # Check environment variable for custom config file if default is passed
    if os.path.basename(config_path) in ("sources.yaml", ""):
        env_cfg = os.environ.get("PISCES_CONFIG") or os.environ.get("CONFIG_FILE")
        if env_cfg and os.path.exists(env_cfg):
            config_path = env_cfg

    # If pack is explicitly requested and default sources.yaml is used,
    # load packs/sources_<pack>.yaml or packs/<pack>.yaml if available
    if norm_explicit and os.path.basename(config_path) == "sources.yaml":
        found_pack_cfg = False
        for base_dir in [pkg_config_dir, repo_root, os.getcwd()]:
            for cand_dir in ["packs", "presets"]:
                for pattern in [f"sources_{norm_explicit}.yaml", f"{norm_explicit}.yaml"]:
                    p_file = os.path.join(base_dir, cand_dir, pattern)
                    if os.path.exists(p_file):
                        config_path = p_file
                        found_pack_cfg = True
                        break
                if found_pack_cfg:
                    break
            if found_pack_cfg:
                break

    resolved_path = None
    candidates = [
        config_path,
        os.path.join(os.getcwd(), config_path),
        os.path.join(repo_root, config_path),
        os.path.join(pkg_config_dir, config_path),
    ]
    if not config_path.endswith((".yaml", ".yml")):
        candidates.extend([
            os.path.join(pkg_config_dir, "packs", f"sources_{config_path}.yaml"),
            os.path.join(pkg_config_dir, "packs", f"{config_path}.yaml"),
            os.path.join(repo_root, "packs", f"sources_{config_path}.yaml"),
            os.path.join(repo_root, "packs", f"{config_path}.yaml"),
        ])
    candidates.extend([
        os.path.join(os.getcwd(), "sources.yaml"),
        os.path.join(repo_root, "sources.yaml"),
        os.path.join(pkg_config_dir, "sources.yaml"),
    ])
    for c in candidates:
        if c and os.path.exists(c) and not os.path.isdir(c):
            resolved_path = c
            break

    data = {}
    if resolved_path:
        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to parse YAML from {resolved_path}: {e}")
            data = {}

    # Determine active inidata pack
    active_pack = (
        pack
        or preset
        or os.environ.get('PISCES_PACK')
        or os.environ.get('PACK')
        or os.environ.get('INIDATA_PACK')
        or os.environ.get('PRESET')
        or os.environ.get('INIDATA_PRESET')
    )
    if not active_pack and isinstance(data, dict):
        active_pack = data.get('pack') or data.get('preset')
    norm_pack = resolve_pack_name(active_pack)

    # Base pack for inheriting defaults (e.g. 'ece4', 'ece3', 'official_sette')
    base_name = 'ece4'
    if isinstance(data, dict):
        base_name = data.get('base_pack') or data.get('base_preset') or 'ece4'
    norm_base = resolve_pack_name(base_name)
    if norm_base not in PACKS:
        norm_base = 'ece4'

    if norm_pack in PACKS:
        config = PACKS[norm_pack].copy()
    else:
        # Custom user pack: inherit unspecified defaults from base_pack
        config = PACKS[norm_base].copy()

    config['INIDATA_PACK'] = norm_pack
    config['INIDATA_PRESET'] = norm_pack

    # Apply per-variable overrides from YAML
    if isinstance(data, dict):
        for (section, key), env_var in YAML_MAP.items():
            if section in data and isinstance(data[section], dict) and key in data[section]:
                config[env_var] = str(data[section][key])
        for k, v in data.items():
            if k in DEFAULTS and isinstance(v, (str, int, float)):
                config[k] = str(v)

    # Determine declarative tracer and forcing lists
    tracers = DEFAULT_TRACERS_3D.copy()
    forcings = DEFAULT_BOUNDARY_FORCINGS.copy()
    river_vars = DEFAULT_RIVER_VARS.copy()
    dust_vars = DEFAULT_DUST_VARS.copy()
    ndep_vars = DEFAULT_NDEP_VARS.copy()

    if isinstance(data, dict):
        if "tracers_3d" in data and isinstance(data["tracers_3d"], dict):
            tracers = list(data["tracers_3d"].keys())
        if "boundary_forcings" in data and isinstance(data["boundary_forcings"], dict):
            forcings = list(data["boundary_forcings"].keys())
        sub_vars = data.get("sub_variables", {})
        if isinstance(sub_vars, dict):
            if "river" in sub_vars and isinstance(sub_vars["river"], list):
                river_vars = [str(x) for x in sub_vars["river"]]
            if "dust" in sub_vars and isinstance(sub_vars["dust"], list):
                dust_vars = [str(x) for x in sub_vars["dust"]]
            if "ndep" in sub_vars and isinstance(sub_vars["ndep"], list):
                ndep_vars = [str(x) for x in sub_vars["ndep"]]

    config['TRACERS_3D_LIST'] = " ".join(tracers)
    config['BOUNDARY_FORCINGS_LIST'] = " ".join(forcings)
    config['RIVER_VARS_LIST'] = " ".join(river_vars)
    config['DUST_VARS_LIST'] = " ".join(dust_vars)
    config['NDEP_VARS_LIST'] = " ".join(ndep_vars)

    # Environment variables override file
    extra_env_keys = [
        'INIDATA_PACK', 'INIDATA_PRESET', 'TRACERS_3D_LIST', 'BOUNDARY_FORCINGS_LIST',
        'RIVER_VARS_LIST', 'DUST_VARS_LIST', 'NDEP_VARS_LIST'
    ]
    for k in list(DEFAULTS.keys()) + extra_env_keys:
        if k in os.environ:
            config[k] = os.environ[k]

    return config


def validate_config(config: Dict[str, str]) -> bool:
    """
    Validates selected products against known supported options.
    Specifically rejects 'ece3' as an individual input source name.
    """
    all_valid = True
    for key, allowed in VALID_SOURCES.items():
        val = config.get(key, DEFAULTS.get(key))
        if val == 'ece3':
            print(
                f"Error: '{key}' is set to 'ece3'. EC-Earth3 inidata cannot be used as an input source. "
                "To use the EC-Earth3 baseline observational sources, set 'pack: ece3' in sources.yaml instead."
            )
            all_valid = False
        elif val not in allowed:
            print(f"Warning: Configuration key '{key}' has invalid value '{val}'. Allowed: {allowed}")
            all_valid = False
    return all_valid


def export_env_commands(config: Dict[str, str]) -> str:
    """
    Generates bash export commands from loaded config.
    """
    lines = []
    for k, v in sorted(config.items()):
        lines.append(f"export {k}=\"{v}\"")
    return "\n".join(lines)
