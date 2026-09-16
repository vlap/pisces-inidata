"""
Platform Configuration Module for PISCES Inidata.
Loads platforms.yaml, provides environment profiles (Slurm account/partition, module loads,
default scratch and domain paths) to decouple HPC cluster specifics from scripts and codebase.
"""

import os
import socket
from typing import Dict, Any, List, Optional
try:
    import yaml
except ImportError:
    yaml = None

GENERIC_PLATFORM_PROFILE: Dict[str, Any] = {
    "description": "Generic Linux Workstation or Cluster",
    "slurm": {
        "account": "",
        "partition": "",
    },
    "module_load": "",
    "scratch_root": "${HOME}/scratch",
    "domain_dir": "",
}


def _find_platforms_yaml(custom_path: Optional[str] = None) -> Optional[str]:
    """Resolves path to platforms.yaml."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates = [
        custom_path,
        os.environ.get("PISCES_PLATFORMS_CONFIG"),
        os.path.join(repo_root, "platforms.yaml"),
        os.path.join(os.getcwd(), "platforms.yaml"),
    ]
    for c in candidates:
        if c and os.path.exists(c) and not os.path.isdir(c):
            return c
    return None


def load_all_platforms(config_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Loads platform definitions directly from platforms.yaml as the single source of truth.
    Uses PyYAML to parse platforms.yaml.
    """
    resolved_path = _find_platforms_yaml(config_path)
    profiles: Dict[str, Dict[str, Any]] = {}

    if resolved_path and os.path.exists(resolved_path) and yaml is not None:
        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            plat_dict = data.get('platforms', {})
            if isinstance(plat_dict, dict):
                for p_name, p_cfg in plat_dict.items():
                    if isinstance(p_cfg, dict):
                        profiles[p_name] = p_cfg
        except Exception as e:
            print(f"Warning: Failed to load platforms configuration from {resolved_path}: {e}")

    # Fallback to generic profile if platforms.yaml is unavailable or generic is missing
    if "generic" not in profiles:
        profiles["generic"] = GENERIC_PLATFORM_PROFILE.copy()

    return profiles


def detect_current_platform(config_path: Optional[str] = None) -> str:
    """Detects active platform from environment or host inspection."""
    env_plat = os.environ.get("PLATFORM") or os.environ.get("PISCES_PLATFORM")
    if env_plat:
        return env_plat

    hostname = socket.gethostname().lower()
    if os.path.isdir("/gpfs/projects/bsc32") or os.path.isdir("/gpfs/scratch/bsc32"):
        if "mn5" in hostname or "marenostrum" in hostname:
            return "mn5"
        return "nord4"

    return "generic"


def load_platform_config(platform_name: Optional[str] = None, config_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads configuration profile for a specific platform."""
    target_name = platform_name or detect_current_platform(config_path)
    all_plats = load_all_platforms(config_path)
    if target_name in all_plats:
        return all_plats[target_name]
    custom = GENERIC_PLATFORM_PROFILE.copy()
    custom["description"] = f"Custom platform ({target_name})"
    return custom


def get_known_platforms(config_path: Optional[str] = None) -> List[str]:
    """Returns sorted list of known platform identifiers."""
    return sorted(load_all_platforms(config_path).keys())


def export_platform_env_commands(platform_name: Optional[str] = None, config_path: Optional[str] = None) -> str:
    """
    Generates bash export statements for a platform.
    Allows config.sh and Slurm launchers to adapt to the host environment without hardcoded logic.
    """
    target_name = platform_name or detect_current_platform(config_path)
    cfg = load_platform_config(target_name, config_path)
    slurm = cfg.get("slurm", {})

    scratch_raw = cfg.get("scratch_root", "${HOME}/scratch")
    domain_raw = cfg.get("domain_dir", "")
    module_load = cfg.get("module_load", "")

    lines = [
        f'export PLATFORM="{target_name}"',
        f'export DEFAULT_PLATFORM_SCRATCH="{scratch_raw}"',
        f'export DEFAULT_PLATFORM_DOMAIN="{domain_raw}"',
        f'export SLURM_ACCOUNT="${{SLURM_ACCOUNT:-{slurm.get("account", "")}}}"',
        f'export SLURM_PARTITION="${{SLURM_PARTITION:-{slurm.get("partition", "")}}}"',
        f'export MODULE_LOAD_CMD="${{MODULE_LOAD_CMD:-{module_load}}}"',
    ]
    return "\n".join(lines)
