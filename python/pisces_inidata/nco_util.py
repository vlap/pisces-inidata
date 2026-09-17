"""
CDO Utilities for PISCES Inidata.
Provides configured Cdo interfaces with thread and option management.
"""

import os
from typing import Optional, List


def get_cdo(threads: Optional[int] = None, options: Optional[List[str]] = None):
    """
    Returns a configured Cdo instance with threading and default options.
    """
    from cdo import Cdo
    cdo = Cdo()
    opts = list(options or [])
    n_threads = threads or os.environ.get("CDO_THREADS")
    if n_threads:
        opts.extend(["-P", str(n_threads)])
    if "-L" not in opts:
        opts.append("-L")
    cdo.env["CDO_OPTS"] = " ".join(opts)
    return cdo
