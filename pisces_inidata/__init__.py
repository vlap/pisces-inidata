"""
pisces-inidata: Biogeochemical Initial Conditions Generator for PISCES & EC-Earth4.
"""

__version__ = "1.0.0"
__author__ = "Vladimir Lapin, Barcelona Supercomputing Center (BSC)"
__license__ = "Apache-2.0"

from .padding import pad_abyssal_depth
from .scoreboard import compute_diagnostics, generate_scoreboard
from .config import load_config, validate_config

__all__ = [
    "__version__",
    "pad_abyssal_depth",
    "compute_diagnostics",
    "generate_scoreboard",
    "load_config",
    "validate_config",
]
