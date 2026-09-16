"""
Configuration Module for PISCES Inidata.
Loads sources.yaml, applies configuration presets (ece4, ece3, official_sette), validates
source climatology choices, rejects invalid ece3 sources, and exports environment
variables for pipeline shell scripts.
"""

import os
try:
    import yaml
except ImportError:
    yaml = None
from typing import Dict, Optional


def _parse_simple_yaml(text: str) -> dict:
    """
    Minimal fallback parser for simple two-level key-value YAML files (such as sources.yaml)
    when PyYAML is not installed in the cluster environment.
    """
    result = {}
    current_section = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if '#' in line:
            line = line.split('#', 1)[0].strip()
        if not line:
            continue
        if line.endswith(':'):
            current_section = line[:-1].strip()
            result[current_section] = {}
        elif ':' in line:
            k, v = line.split(':', 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if current_section is not None:
                result[current_section][k] = v
            else:
                result[k] = v
    return result


PRESETS = {
    'ece4': {
        'PRODUCT_NO3': 'woa23',
        'PRODUCT_PO4': 'woa23',
        'PRODUCT_Si': 'woa23',
        'PRODUCT_O2': 'woa23',
        'PRODUCT_TALK': 'glodap_v2_2016b',
        'PRODUCT_TDIC': 'glodap_v2_2016b',
        'PRODUCT_PiDIC': 'glodap_v2_2016b',
        'PRODUCT_DOC': 'panaiotis2024',
        'PRODUCT_Fer': 'sette_nomask',
        'PRODUCT_DUST': 'sette_orca2',
        'PRODUCT_NDEP': 'sette_orca2',
        'PRODUCT_PAR': 'sette_orca2',
        'PRODUCT_BATHY': 'sette_orca2',
        'PRODUCT_HYDROFE': 'sette_orca2',
        'PRODUCT_RIVER': 'sette_orca2',
    },
    'ece3': {
        'PRODUCT_NO3': 'woa2009',
        'PRODUCT_PO4': 'woa2009',
        'PRODUCT_Si': 'woa2009',
        'PRODUCT_O2': 'woa2009',
        'PRODUCT_TALK': 'glodap_v1',
        'PRODUCT_TDIC': 'glodap_v1',
        'PRODUCT_PiDIC': 'glodap_v1',
        'PRODUCT_DOC': 'sette_nomask',
        'PRODUCT_Fer': 'sette_nomask',
        'PRODUCT_DUST': 'sette_orca2',
        'PRODUCT_NDEP': 'sette_orca2',
        'PRODUCT_PAR': 'sette_orca2',
        'PRODUCT_BATHY': 'sette_orca2',
        'PRODUCT_HYDROFE': 'sette_orca2',
        'PRODUCT_RIVER': 'sette_orca2',
    },
    'official_sette': {
        'PRODUCT_NO3': 'sette_nomask',
        'PRODUCT_PO4': 'sette_nomask',
        'PRODUCT_Si': 'sette_nomask',
        'PRODUCT_O2': 'sette_nomask',
        'PRODUCT_TALK': 'sette_nomask',
        'PRODUCT_TDIC': 'sette_nomask',
        'PRODUCT_PiDIC': 'sette_nomask',
        'PRODUCT_DOC': 'sette_nomask',
        'PRODUCT_Fer': 'sette_nomask',
        'PRODUCT_DUST': 'sette_orca2',
        'PRODUCT_NDEP': 'sette_orca2',
        'PRODUCT_PAR': 'sette_orca2',
        'PRODUCT_BATHY': 'sette_orca2',
        'PRODUCT_HYDROFE': 'sette_orca2',
        'PRODUCT_RIVER': 'sette_orca2',
    },
}

DEFAULTS = PRESETS['ece4'].copy()

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


def resolve_preset_name(preset: Optional[str]) -> str:
    """Normalizes preset name; defaults to ece4."""
    if not preset:
        return 'ece4'
    return preset.strip().lower()


def load_config(config_path: str = "sources.yaml", preset: Optional[str] = None) -> Dict[str, str]:
    """
    Loads product configuration from preset and sources.yaml or environment variables.
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    explicit_preset = preset or os.environ.get('PRESET') or os.environ.get('INIDATA_PRESET')
    norm_explicit = resolve_preset_name(explicit_preset) if explicit_preset else None

    # If preset is explicitly requested and default sources.yaml is used,
    # load presets/sources_<preset>.yaml if available
    if norm_explicit and os.path.basename(config_path) == "sources.yaml":
        preset_file = os.path.join(repo_root, "presets", f"sources_{norm_explicit}.yaml")
        if os.path.exists(preset_file):
            config_path = preset_file

    resolved_path = None
    candidates = [
        config_path,
        os.path.join(repo_root, config_path),
        os.path.join(repo_root, "sources.yaml"),
    ]
    for c in candidates:
        if c and os.path.exists(c) and not os.path.isdir(c):
            resolved_path = c
            break

    data = {}
    if resolved_path:
        with open(resolved_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if yaml is not None:
            try:
                data = yaml.safe_load(content) or {}
            except Exception as e:
                print(f"Warning: Failed to parse YAML from {resolved_path}: {e}")
                data = {}
        else:
            try:
                data = _parse_simple_yaml(content)
            except Exception as e:
                print(f"Warning: Failed to parse configuration from {resolved_path}: {e}")
                data = {}

    # Determine active preset
    active_preset = preset or os.environ.get('PRESET') or os.environ.get('INIDATA_PRESET')
    if not active_preset and isinstance(data, dict):
        active_preset = data.get('preset')
    norm_preset = resolve_preset_name(active_preset)

    if norm_preset in PRESETS:
        config = PRESETS[norm_preset].copy()
    else:
        print(f"Warning: Unknown preset '{norm_preset}'. Falling back to 'ece4'. Available: {list(PRESETS.keys())}")
        norm_preset = 'ece4'
        config = PRESETS['ece4'].copy()

    config['INIDATA_PRESET'] = norm_preset

    # Apply per-variable overrides from YAML
    if isinstance(data, dict):
        for (section, key), env_var in YAML_MAP.items():
            if section in data and isinstance(data[section], dict) and key in data[section]:
                config[env_var] = str(data[section][key])
        for k, v in data.items():
            if k in DEFAULTS and isinstance(v, (str, int, float)):
                config[k] = str(v)

    # Environment variables override file
    for k in list(DEFAULTS.keys()) + ['INIDATA_PRESET']:
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
                "To use the EC-Earth3 baseline observational sources, set 'preset: ece3' in sources.yaml instead."
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
