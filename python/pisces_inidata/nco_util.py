"""
NCO and CDO Utilities for PISCES Inidata.
Provides configured Cdo and Nco interfaces with robust error handling and a pure
Python netCDF4 fallback when NCO system binaries are not installed in the environment.
"""

import os
import shutil
from typing import Optional, List
import netCDF4 as nc
import numpy as np


class NetCDF4NcoFallback:
    """
    Pure Python netCDF4 fallback implementing standard NCO commands (ncks, ncrename, ncatted, ncwa)
    when NCO command-line binaries (ncks) are not in PATH.
    """

    def ncrename(self, input: str, output: Optional[str] = None, options: Optional[List[str]] = None, **kwargs) -> str:
        """Renames variables or dimensions in NetCDF file."""
        target_path = output or input
        if output and output != input:
            shutil.copyfile(input, output)

        opts = options or []
        # Parse -v old,new and -d old,new
        i = 0
        while i < len(opts):
            opt = opts[i]
            if opt in ("-v", "--variable"):
                val = opts[i + 1]
                i += 2
                old_name, new_name = val.split(",")
                with nc.Dataset(target_path, "r+") as ds:
                    if old_name in ds.variables:
                        ds.renameVariable(old_name, new_name)
            elif opt in ("-d", "--dimension"):
                val = opts[i + 1]
                i += 2
                old_name, new_name = val.split(",")
                with nc.Dataset(target_path, "r+") as ds:
                    if old_name in ds.dimensions:
                        ds.renameDimension(old_name, new_name)
            else:
                i += 1
        return target_path

    def ncatted(self, input: str, output: Optional[str] = None, options: Optional[List[str]] = None, **kwargs) -> str:
        """Edits global and variable NetCDF attributes."""
        target_path = output or input
        if output and output != input:
            shutil.copyfile(input, output)

        opts = options or []
        i = 0
        while i < len(opts):
            opt = opts[i]
            if opt in ("-a", "--attribute"):
                val = opts[i + 1]
                i += 2
                parts = val.split(",")
                if len(parts) >= 5:
                    att_name = parts[0]
                    var_name = parts[1]
                    mode = parts[2]
                    att_type = parts[3]
                    att_val = ",".join(parts[4:]).strip("'\"")
                else:
                    continue

                with nc.Dataset(target_path, "r+") as ds:
                    target_obj = ds if not var_name or var_name == "global" else ds.variables.get(var_name)
                    if target_obj is not None:
                        if mode == "d":
                            if hasattr(target_obj, att_name):
                                delattr(target_obj, att_name)
                        else:
                            if att_type in ("c", "s"):
                                setattr(target_obj, att_name, str(att_val))
                            elif att_type in ("f", "d"):
                                setattr(target_obj, att_name, float(att_val))
                            elif att_type in ("i", "l", "s"):
                                setattr(target_obj, att_name, int(att_val))
                            else:
                                setattr(target_obj, att_name, att_val)
            else:
                i += 1
        return target_path

    def ncks(self, input: str, output: Optional[str] = None, options: Optional[List[str]] = None, **kwargs) -> str:
        """Extracts variables (-v) or appends (-A) variables between NetCDF files."""
        opts = options or []
        append_mode = "-A" in opts
        vars_to_extract: List[str] = []

        i = 0
        while i < len(opts):
            opt = opts[i]
            if opt in ("-v", "--variable"):
                vars_to_extract = [v.strip() for v in opts[i + 1].split(",")]
                i += 2
            else:
                i += 1

        if append_mode:
            target_path = output or input
            with nc.Dataset(input, "r") as src, nc.Dataset(target_path, "r+") as dst:
                vars_to_copy = vars_to_extract or list(src.variables.keys())
                for vname in vars_to_copy:
                    if vname in src.variables and vname not in dst.variables:
                        src_var = src.variables[vname]
                        # Ensure dimensions exist
                        for dim_name in src_var.dimensions:
                            if dim_name not in dst.dimensions:
                                dst.createDimension(dim_name, src.dimensions[dim_name].size)
                        # Create variable
                        dst_var = dst.createVariable(vname, src_var.dtype, src_var.dimensions)
                        for attr in src_var.ncattrs():
                            setattr(dst_var, attr, getattr(src_var, attr))
                        dst_var[:] = src_var[:]
            return target_path
        else:
            if not output:
                return input
            with nc.Dataset(input, "r") as src, nc.Dataset(output, "w", format="NETCDF4") as dst:
                vars_to_copy = vars_to_extract or list(src.variables.keys())
                # Copy dimensions of requested variables
                needed_dims = set()
                for vname in vars_to_copy:
                    if vname in src.variables:
                        needed_dims.update(src.variables[vname].dimensions)
                for dname in needed_dims:
                    dst.createDimension(dname, src.dimensions[dname].size)
                # Copy variables
                for vname in vars_to_copy:
                    if vname in src.variables:
                        s_var = src.variables[vname]
                        d_var = dst.createVariable(vname, s_var.dtype, s_var.dimensions)
                        for attr in s_var.ncattrs():
                            setattr(d_var, attr, getattr(s_var, attr))
                        d_var[:] = s_var[:]
                # Copy global attributes
                for attr in src.ncattrs():
                    setattr(dst, attr, getattr(src, attr))
            return output

    def ncwa(self, input: str, output: Optional[str] = None, options: Optional[List[str]] = None, **kwargs) -> str:
        """Squashes degenerate (size 1) dimensions from NetCDF file."""
        target_path = output or input
        opts = options or []
        dims_to_squeeze: List[str] = []

        i = 0
        while i < len(opts):
            opt = opts[i]
            if opt in ("-a", "--average"):
                dims_to_squeeze = [d.strip() for d in opts[i + 1].split(",")]
                i += 2
            else:
                i += 1

        temp_out = target_path + ".tmp_squeeze.nc"
        with nc.Dataset(input, "r") as src, nc.Dataset(temp_out, "w", format="NETCDF4") as dst:
            for dname, dval in src.dimensions.items():
                if dname not in dims_to_squeeze:
                    dst.createDimension(dname, dval.size)

            for vname, svar in src.variables.items():
                new_dims = tuple(d for d in svar.dimensions if d not in dims_to_squeeze)
                dvar = dst.createVariable(vname, svar.dtype, new_dims)
                for attr in svar.ncattrs():
                    setattr(dvar, attr, getattr(svar, attr))
                data = svar[:]
                # Squeeze or average specified axes
                for ax, dim in reversed(list(enumerate(svar.dimensions))):
                    if dim in dims_to_squeeze:
                        if data.shape[ax] == 1:
                            data = np.squeeze(data, axis=ax)
                        else:
                            data = np.mean(data, axis=ax)
                dvar[...] = data

            for attr in src.ncattrs():
                setattr(dst, attr, getattr(src, attr))

        shutil.move(temp_out, target_path)
        return target_path


def get_nco():
    """
    Returns an Nco instance.
    Uses pynco (from nco import Nco) if ncks binary is available in PATH or ~/.local/nco-env/bin.
    Otherwise returns NetCDF4NcoFallback for seamless operation on systems without NCO binaries.
    """
    if not shutil.which("ncks"):
        cand = os.path.expanduser("~/.local/nco-env/bin")
        if os.path.isfile(os.path.join(cand, "ncks")):
            os.environ["PATH"] = cand + os.pathsep + os.environ.get("PATH", "")

    if shutil.which("ncks"):
        try:
            from nco import Nco
            return Nco()
        except Exception:
            pass
    return NetCDF4NcoFallback()


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
