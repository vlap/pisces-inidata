"""
Configuration Module for PISCES Inidata.
Loads sources.yaml, validates source climatology choices, rejects invalid ece3 sources,
and exports environment variables for pipeline shell scripts.
"""

import os
import sys
import yaml
from typing import Dict

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

DEFAULTS = {
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
}

# Mapping from sources.yaml keys to PRODUCT_* environment variables
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


def load_config(config_path: str = "sources.yaml") -> Dict[str, str]:
    """
    Loads product configuration from sources.yaml or environment variables.
    """
    config = DEFAULTS.copy()

    resolved_path = None
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates = [
        config_path,
        os.path.join(repo_root, config_path),
        os.path.join(repo_root, "sources.yaml"),
    ]
    for c in candidates:
        if c and os.path.exists(c) and not os.path.isdir(c):
            resolved_path = c
            break

    if resolved_path:
        with open(resolved_path, 'r') as f:
            try:
                data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to parse YAML from {resolved_path}: {e}")
                data = {}

        if isinstance(data, dict):
            # Parse nested structure
            for (section, key), env_var in YAML_MAP.items():
                if section in data and isinstance(data[section], dict) and key in data[section]:
                    config[env_var] = str(data[section][key])
            # Also support flat keys if provided directly
            for k, v in data.items():
                if k in DEFAULTS and isinstance(v, (str, int, float)):
                    config[k] = str(v)

    # Environment variables override file
    for k in DEFAULTS.keys():
        if k in os.environ:
            config[k] = os.environ[k]

    return config


def validate_config(config: Dict[str, str]) -> bool:
    """
    Validates selected products against known supported options.
    Specifically rejects 'ece3' as an input source, since EC-Earth3 inidata
    is reserved exclusively for reproduction verification.
    """
    all_valid = True
    for key, allowed in VALID_SOURCES.items():
        val = config.get(key, DEFAULTS.get(key))
        if val == 'ece3':
            print(
                f"Error: '{key}' is set to 'ece3'. EC-Earth3 inidata cannot be used as an input source. "
                "It is reserved exclusively for reproduction verification."
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


if __name__ == "__main__":
    cfg_file = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "sources.yaml"
    cfg = load_config(cfg_file)
    if "--export" in sys.argv or (len(sys.argv) > 1 and sys.argv[1] == "export"):
        print(export_env_commands(cfg))
    else:
        valid = validate_config(cfg)
        for k, v in sorted(cfg.items()):
            print(f"{k} = {v}")
        sys.exit(0 if valid else 1)
