#!/usr/bin/env python3
"""
pad_abyssal_depth.py
Extends the vertical coordinate of a 3D or 4D NetCDF file to 6000m by replicating
the deepest available level. This ensures CDO 1D vertical linear interpolation
(-intlevel) can cleanly bracket and interpolate NEMO deep L75/L121 vertical levels
(down to ~5902m) without generating missing values in the abyssal ocean.
"""

import sys
import os
import netCDF4 as nc
import numpy as np

def pad_abyssal_depth(in_file, out_file, target_bottom_depth=6000.0):
    if not os.path.isfile(in_file):
        raise FileNotFoundError(f"Input file not found: {in_file}")

    with nc.Dataset(in_file, 'r') as src, nc.Dataset(out_file, 'w', format='NETCDF4') as dst:
        # Detect vertical dimension
        depth_dim_names = ['depth', 'depth_surface', 'Depth', 'nav_lev', 'z']
        z_dim = next((d for d in depth_dim_names if d in src.dimensions), None)
        
        # Copy global attributes
        dst.setncatts({k: src.getncattr(k) for k in src.ncattrs()})
        
        # Determine depth variable
        z_var = None
        if z_dim and z_dim in src.variables:
            z_var = z_dim
        else:
            for cand in ['depth', 'Depth', 'nav_lev', 'depth_surface', 'z']:
                if cand in src.variables:
                    z_var = cand
                    break
            
        pad_top = False
        pad_bottom = False
        if z_var is not None and z_dim is not None:
            depth_vals = np.array(src.variables[z_var][:], dtype=np.float32)
            if depth_vals[0] > 0.0:
                pad_top = True
            if depth_vals[-1] < target_bottom_depth:
                pad_bottom = True

        extra_levels = (1 if pad_top else 0) + (1 if pad_bottom else 0)

        # Copy dimensions
        for dname, dim in src.dimensions.items():
            if extra_levels > 0 and dname == z_dim:
                dst.createDimension(dname, len(dim) + extra_levels if not dim.isunlimited() else None)
            else:
                dst.createDimension(dname, len(dim) if not dim.isunlimited() else None)
                
        # Copy variables
        for vname, var in src.variables.items():
            out_dims = var.dimensions
            fill_val = getattr(var, '_FillValue', None)
            out_var = dst.createVariable(vname, var.dtype, out_dims, fill_value=fill_val, zlib=True, complevel=4)
            out_var.setncatts({k: var.getncattr(k) for k in var.ncattrs() if k != '_FillValue'})
            
            if extra_levels > 0 and vname == z_var:
                new_depths = depth_vals
                if pad_top:
                    new_depths = np.insert(new_depths, 0, np.float32(0.0))
                if pad_bottom:
                    new_depths = np.append(new_depths, np.float32(target_bottom_depth))
                out_var[:] = new_depths
            elif extra_levels > 0 and z_dim in out_dims:
                z_axis = out_dims.index(z_dim)
                data = var[:]
                padded_data = data
                if pad_top:
                    first_slice = np.take(padded_data, indices=[0], axis=z_axis)
                    padded_data = np.concatenate([first_slice, padded_data], axis=z_axis)
                if pad_bottom:
                    last_slice = np.take(padded_data, indices=[-1], axis=z_axis)
                    padded_data = np.concatenate([padded_data, last_slice], axis=z_axis)
                out_var[:] = padded_data
            else:
                out_var[:] = var[:]

    print(f"Depth padding completed: {out_file} (surface 0.0m: {pad_top}, bottom {target_bottom_depth}m: {pad_bottom})")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: pad_abyssal_depth.py <input.nc> <output.nc> [target_bottom_depth]")
        sys.exit(1)
    target = float(sys.argv[3]) if len(sys.argv) > 3 else 6000.0
    pad_abyssal_depth(sys.argv[1], sys.argv[2], target)
