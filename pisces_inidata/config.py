"""
Configuration Module for PISCES Inidata
Parses products.cfg, validates tracer choices, and ensures consistency across the pipeline.
"""

import os
import re
from typing import Dict

VALID_PRODUCTS = {
    'PRODUCT_NO3': ['woa23', 'woa2009', 'sette_nomask', 'ece3'],
    'PRODUCT_PO4': ['woa23', 'woa2009', 'sette_nomask', 'ece3'],
    'PRODUCT_Si': ['woa23', 'woa2009', 'sette_nomask', 'ece3'],
    'PRODUCT_O2': ['woa23', 'woa2009', 'sette_nomask', 'ece3'],
    'PRODUCT_TALK': [
        'glodap_v3', 'glodap_v2_2016b', 'glodap_v2_2023', 'glodap_v1',
        'sette_nomask', 'ece3', 'cmems'
    ],
    'PRODUCT_TDIC': [
        'glodap_v3', 'glodap_v2_2016b', 'glodap_v2_2023', 'glodap_v1',
        'sette_nomask', 'ece3', 'cmems'
    ],
    'PRODUCT_PiDIC': [
        'glodap_v3', 'glodap_v2_2016b', 'glodap_v2_2023', 'glodap_v1',
        'sette_nomask', 'ece3', 'cmems'
    ],
    'PRODUCT_DOC': ['panaiotis2024', 'sette_nomask', 'ece3'],
    'PRODUCT_Fer': ['sette_nomask', 'ece3'],
    'PRODUCT_DUST': ['ece3', 'sette_orca2'],
    'PRODUCT_NDEP': ['ece3', 'sette_orca2'],
    'PRODUCT_PAR': ['ece3', 'sette_orca2'],
    'PRODUCT_BATHY': ['ece3', 'sette_orca2'],
    'PRODUCT_HYDROFE': ['sette_orca2'],
    'PRODUCT_RIVER': ['ece3', 'sette_orca2'],
}

DEFAULTS = {
    'PRODUCT_NO3': 'woa23',
    'PRODUCT_PO4': 'woa23',
    'PRODUCT_Si': 'woa23',
    'PRODUCT_O2': 'woa23',
    'PRODUCT_TALK': 'glodap_v3',
    'PRODUCT_TDIC': 'glodap_v3',
    'PRODUCT_PiDIC': 'glodap_v3',
    'PRODUCT_DOC': 'panaiotis2024',
    'PRODUCT_Fer': 'sette_nomask',
    'PRODUCT_DUST': 'ece3',
    'PRODUCT_NDEP': 'ece3',
    'PRODUCT_PAR': 'ece3',
    'PRODUCT_BATHY': 'ece3',
    'PRODUCT_HYDROFE': 'sette_orca2',
    'PRODUCT_RIVER': 'ece3',
}


def load_config(config_path: str = "products.cfg") -> Dict[str, str]:
    """
    Loads product configuration from shell-style products.cfg or environment variables.
    """
    config = DEFAULTS.copy()

    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('export'):
                    continue
                match = re.match(r'([A-Za-z0-9_]+)=["\']?\$\{?[A-Za-z0-9_]+:-?([^}"\']*)\}?["\']?', line)
                if match:
                    key = match.group(1)
                    val = match.group(2)
                    config[key] = val
                else:
                    match_direct = re.match(r'([A-Za-z0-9_]+)=["\']?([^"\']*)["\']?', line)
                    if match_direct:
                        key = match_direct.group(1)
                        val = match_direct.group(2)
                        config[key] = val

    # Environment variables override file
    for k in DEFAULTS.keys():
        if k in os.environ:
            config[k] = os.environ[k]

    return config


def validate_config(config: Dict[str, str]) -> bool:
    """
    Validates selected products against known supported options.
    """
    all_valid = True
    for key, allowed in VALID_PRODUCTS.items():
        val = config.get(key, DEFAULTS.get(key))
        if val not in allowed:
            print(f"Warning: Configuration key '{key}' has invalid value '{val}'. Allowed: {allowed}")
            all_valid = False
    return all_valid
