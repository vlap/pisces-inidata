"""
Grid Configuration Module for PISCES Inidata.
Loads grids.yaml, provides resource profiles (Slurm time, memory, CPUs, batch weights),
disk space limits, and remapping behaviors for target NEMO grids without hardcoded conditionals.
"""

import os
from typing import Dict, Any, List, Optional
try:
    import yaml
except ImportError:
    yaml = None

DEFAULT_GRID_PROFILES: Dict[str, Dict[str, Any]] = {
    "ORCA2": {
        "description": "NEMO standard 2-degree tripolar grid (148x180, 31 vertical levels)",
        "resources": {
            "time": "00:30:00",
            "memory": "8G",
            "cpus": 8,
            "batch_weights": False,
        },
        "disk_space_gb": 2.0,
        "vertical_levels": 31,
        "native_forcings": True,
        "fallback_coords_source": "official_v5.0.0/bathy.orca.nc",
    },
    "eORCA1": {
        "description": "Extended ORCA 1-degree global grid (362x292, 75 vertical levels)",
        "resources": {
            "time": "01:00:00",
            "memory": "16G",
            "cpus": 16,
            "batch_weights": False,
        },
        "disk_space_gb": 10.0,
        "vertical_levels": 75,
        "native_forcings": False,
        "fallback_coords_source": None,
    },
    "eORCA025": {
        "description": "Extended ORCA 0.25-degree eddy-permitting grid (1442x1207, 75 vertical levels)",
        "resources": {
            "time": "02:00:00",
            "memory": "64G",
            "cpus": 16,
            "batch_weights": True,
        },
        "disk_space_gb": 40.0,
        "vertical_levels": 75,
        "native_forcings": False,
        "fallback_coords_source": None,
    },
    "eORCA12": {
        "description": "Extended ORCA 1/12-degree eddy-resolving grid (4322x3606, 75 vertical levels)",
        "resources": {
            "time": "04:00:00",
            "memory": "128G",
            "cpus": 32,
            "batch_weights": True,
        },
        "disk_space_gb": 120.0,
        "vertical_levels": 75,
        "native_forcings": False,
        "fallback_coords_source": None,
    },
}

GENERIC_DEFAULT_PROFILE: Dict[str, Any] = {
    "description": "Generic NEMO target grid",
    "resources": {
        "time": "01:00:00",
        "memory": "16G",
        "cpus": 16,
        "batch_weights": False,
    },
    "disk_space_gb": 15.0,
    "vertical_levels": 75,
    "native_forcings": False,
    "fallback_coords_source": None,
}


def _find_grids_yaml(custom_path: Optional[str] = None) -> Optional[str]:
    """Resolves path to grids.yaml."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates = [
        custom_path,
        os.environ.get("PISCES_GRIDS_CONFIG"),
        os.path.join(repo_root, "grids.yaml"),
        os.path.join(os.getcwd(), "grids.yaml"),
    ]
    for c in candidates:
        if c and os.path.exists(c) and not os.path.isdir(c):
            return c
    return None


def load_all_grids(config_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Loads all grid definitions from grids.yaml merged over default profiles."""
    profiles = {k: v.copy() for k, v in DEFAULT_GRID_PROFILES.items()}
    resolved_path = _find_grids_yaml(config_path)

    if resolved_path and yaml is not None:
        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            grids_dict = data.get('grids', {})
            if isinstance(grids_dict, dict):
                for g_name, g_cfg in grids_dict.items():
                    if isinstance(g_cfg, dict):
                        if g_name not in profiles:
                            profiles[g_name] = GENERIC_DEFAULT_PROFILE.copy()
                        # Deep merge resources
                        if 'resources' in g_cfg and isinstance(g_cfg['resources'], dict):
                            profiles[g_name]['resources'] = profiles[g_name].get('resources', {}).copy()
                            profiles[g_name]['resources'].update(g_cfg['resources'])
                        for k, v in g_cfg.items():
                            if k != 'resources':
                                profiles[g_name][k] = v
        except Exception as e:
            print(f"Warning: Failed to load grids configuration from {resolved_path}: {e}")

    return profiles


def get_known_grids(config_path: Optional[str] = None) -> List[str]:
    """Returns sorted list of known target grid identifiers."""
    grids_dict = load_all_grids(config_path)
    return sorted(grids_dict.keys())


def load_grid_config(grid_name: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads configuration profile for a specific target grid.
    If the grid is not in grids.yaml, returns a safe generic default.
    """
    all_grids = load_all_grids(config_path)
    if grid_name in all_grids:
        return all_grids[grid_name]

    # Return safe generic default for custom grid
    custom_profile = GENERIC_DEFAULT_PROFILE.copy()
    custom_profile["description"] = f"Custom target grid ({grid_name})"
    return custom_profile


def export_grid_env_commands(grid_name: str, config_path: Optional[str] = None) -> str:
    """
    Generates bash export statements for a target grid.
    Enables shell scripts to consume grid settings without any 'if grid == ...' checks.
    """
    cfg = load_grid_config(grid_name, config_path)
    resources = cfg.get("resources", {})
    batch_weights = "1" if resources.get("batch_weights", False) else "0"
    native_forcings = "1" if cfg.get("native_forcings", False) else "0"
    fallback_coords = cfg.get("fallback_coords_source") or ""

    lines = [
        f"export GRID_NAME=\"{grid_name}\"",
        f"export GRID_DESCRIPTION=\"{cfg.get('description', '')}\"",
        f"export GRID_SLURM_TIME=\"{resources.get('time', '01:00:00')}\"",
        f"export GRID_SLURM_MEM=\"{resources.get('memory', '16G')}\"",
        f"export GRID_SLURM_CPUS=\"{resources.get('cpus', 16)}\"",
        f"export GRID_BATCH_WEIGHTS=\"{batch_weights}\"",
        f"export GRID_NATIVE_FORCINGS=\"{native_forcings}\"",
        f"export GRID_FALLBACK_COORDS=\"{fallback_coords}\"",
        f"export GRID_MIN_DISK_GB=\"{cfg.get('disk_space_gb', 10.0)}\"",
        f"export GRID_VERTICAL_LEVELS=\"{cfg.get('vertical_levels', 75)}\"",
    ]
    return "\n".join(lines)
