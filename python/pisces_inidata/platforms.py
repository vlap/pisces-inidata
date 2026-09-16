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

DEFAULT_PLATFORM_PROFILES: Dict[str, Dict[str, Any]] = {
    "nord4": {
        "description": "BSC Nord4 Cluster (Intel Xeon Platinum 8480+)",
        "slurm": {
            "account": "bsc32",
            "partition": "bsc_es",
        },
        "module_load": "module load CDO NCO 2>/dev/null || true",
        "scratch_root": "/gpfs/scratch/bsc32/${USER}",
        "domain_dir": "/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain",
    },
    "mn5": {
        "description": "BSC MareNostrum 5 (GPP)",
        "slurm": {
            "account": "bsc32",
            "partition": "gpp",
        },
        "module_load": "module load cdo nco 2>/dev/null || true",
        "scratch_root": "/gpfs/scratch/bsc32/${USER}",
        "domain_dir": "/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain",
    },
    "generic": {
        "description": "Generic Linux Workstation or Cluster",
        "slurm": {
            "account": "",
            "partition": "",
        },
        "module_load": "",
        "scratch_root": "${HOME}/scratch",
        "domain_dir": "",
    },
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
    """Loads all platform definitions from platforms.yaml merged over default profiles."""
    profiles = {k: v.copy() for k, v in DEFAULT_PLATFORM_PROFILES.items()}
    resolved_path = _find_platforms_yaml(config_path)

    if resolved_path and yaml is not None:
        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            plat_dict = data.get('platforms', {})
            if isinstance(plat_dict, dict):
                for p_name, p_cfg in plat_dict.items():
                    if isinstance(p_cfg, dict):
                        if p_name not in profiles:
                            profiles[p_name] = DEFAULT_PLATFORM_PROFILES["generic"].copy()
                        if 'slurm' in p_cfg and isinstance(p_cfg['slurm'], dict):
                            profiles[p_name]['slurm'] = profiles[p_name].get('slurm', {}).copy()
                            profiles[p_name]['slurm'].update(p_cfg['slurm'])
                        for k, v in p_cfg.items():
                            if k != 'slurm':
                                profiles[p_name][k] = v
        except Exception as e:
            print(f"Warning: Failed to load platforms configuration from {resolved_path}: {e}")

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
    custom = DEFAULT_PLATFORM_PROFILES["generic"].copy()
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
