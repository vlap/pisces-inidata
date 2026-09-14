#!/usr/bin/env python3
"""
prepare_woa23_tracer.py
Combines 12 monthly WOA23 NetCDF files with the annual mean deep levels
into a complete 12-month, 102-level NetCDF for PISCES interpolation.
Dynamically handles variables with different monthly vertical resolutions
(e.g., 43 levels for nutrients vs 57 levels for oxygen).
Follows HPC login node memory constraints: writes chunked per-timestep.
"""

import sys
import os
import netCDF4 as nc
import numpy as np

def process_tracer(var_code, woa_dir, out_file):
    var_map = {
        'n': ('nitrate', 'n_an', 'NO3', 'umol/l'),
        'p': ('phosphate', 'p_an', 'PO4', 'umol/l'),
        'i': ('silicate', 'i_an', 'Si', 'umol/l'),
        'o': ('oxygen', 'o_an', 'O2', 'umol/l'),
    }
    
    if var_code not in var_map:
        raise ValueError(f"Unknown var_code: {var_code}. Choose from {list(var_map.keys())}")
        
    var_folder, nc_var, out_var, units = var_map[var_code]
    folder_path = os.path.join(woa_dir, var_folder)
    
    # 1. Read annual file for full depth coordinate and deep levels
    ann_path = os.path.join(folder_path, f"woa23_all_{var_code}00_01.nc")
    if not os.path.isfile(ann_path):
        raise FileNotFoundError(f"Annual file not found: {ann_path}")
        
    with nc.Dataset(ann_path, 'r') as ds_ann:
        depth_full = np.array(ds_ann.variables['depth'][:], dtype=np.float32)
        lat = np.array(ds_ann.variables['lat'][:], dtype=np.float32)
        lon = np.array(ds_ann.variables['lon'][:], dtype=np.float32)
        ann_data = np.array(ds_ann.variables[nc_var][0, :, :, :], dtype=np.float32)
        ann_fill = float(getattr(ds_ann.variables[nc_var], '_FillValue', -9999.0))

    # Inspect first month to detect number of monthly levels dynamically
    m1_path = os.path.join(folder_path, f"woa23_all_{var_code}01_01.nc")
    with nc.Dataset(m1_path, 'r') as ds_m1:
        n_m_levs = ds_m1.variables['depth'].shape[0]

    deep_data = ann_data[n_m_levs:, :, :]
    print(f"[{out_var}] Monthly levels: {n_m_levs}, Annual deep levels: {len(depth_full) - n_m_levs} (Total: {len(depth_full)})")

    # 2. Create output NetCDF
    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    with nc.Dataset(out_file, 'w', format='NETCDF4') as ds_out:
        ds_out.createDimension('time_counter', 12)
        ds_out.createDimension('depth', len(depth_full))
        ds_out.createDimension('lat', len(lat))
        ds_out.createDimension('lon', len(lon))
        
        v_time = ds_out.createVariable('time_counter', 'f8', ('time_counter',))
        v_time.units = "months since 0001-01-01 00:00:00"
        v_time.calendar = "noleap"
        v_time[:] = np.arange(0.5, 12.5, 1.0)
        
        v_depth = ds_out.createVariable('depth', 'f4', ('depth',))
        v_depth.units = "m"
        v_depth.positive = "down"
        v_depth.axis = "Z"
        v_depth[:] = depth_full
        
        v_lat = ds_out.createVariable('lat', 'f4', ('lat',))
        v_lat.units = "degrees_north"
        v_lat.axis = "Y"
        v_lat[:] = lat
        
        v_lon = ds_out.createVariable('lon', 'f4', ('lon',))
        v_lon.units = "degrees_east"
        v_lon.axis = "X"
        v_lon[:] = lon
        
        v_var = ds_out.createVariable(
            out_var, 'f4', ('time_counter', 'depth', 'lat', 'lon'),
            fill_value=ann_fill, zlib=True, complevel=4
        )
        v_var.units = units
        v_var.long_name = f"WOA23 Climatological {out_var}"
        
        # 3. Stream each month directly to file
        for m_idx in range(12):
            m_str = f"{m_idx + 1:02d}"
            m_path = os.path.join(folder_path, f"woa23_all_{var_code}{m_str}_01.nc")
            if not os.path.isfile(m_path):
                raise FileNotFoundError(f"Monthly file not found: {m_path}")
            
            step_data = np.full((len(depth_full), len(lat), len(lon)), ann_fill, dtype=np.float32)
            with nc.Dataset(m_path, 'r') as ds_m:
                step_data[:n_m_levs, :, :] = ds_m.variables[nc_var][0, :, :, :]
            step_data[n_m_levs:, :, :] = deep_data
            v_var[m_idx, :, :, :] = step_data

    print(f"Successfully generated combined WOA23 file: {out_file}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: prepare_woa23_tracer.py <n|p|i|o> <woa_dir> <out_file>")
        sys.exit(1)
    process_tracer(sys.argv[1], sys.argv[2], sys.argv[3])
