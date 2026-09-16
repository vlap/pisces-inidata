#!/usr/bin/env python3
"""
prepare_woa23_tracer.py
Combines 12 monthly WOA23 NetCDF files with the annual mean deep levels
into a complete 12-month, 102-level NetCDF for PISCES interpolation.
Dynamically handles variables with different monthly vertical resolutions
(e.g., 43 levels for nutrients vs 57 levels for oxygen).
Follows HPC login node memory constraints: writes chunked per-timestep.
"""

import os
import netCDF4 as nc
import numpy as np
from pisces_inidata.provenance import create_cf_coordinates

TRACER_LOOKUP = {
    'n': ('n', 'nitrate', 'n_an', 'NO3', 'umol/l'),
    'n_an': ('n', 'nitrate', 'n_an', 'NO3', 'umol/l'),
    'no3': ('n', 'nitrate', 'n_an', 'NO3', 'umol/l'),
    'nitrate': ('n', 'nitrate', 'n_an', 'NO3', 'umol/l'),
    'p': ('p', 'phosphate', 'p_an', 'PO4', 'umol/l'),
    'p_an': ('p', 'phosphate', 'p_an', 'PO4', 'umol/l'),
    'po4': ('p', 'phosphate', 'p_an', 'PO4', 'umol/l'),
    'phosphate': ('p', 'phosphate', 'p_an', 'PO4', 'umol/l'),
    'i': ('i', 'silicate', 'i_an', 'Si', 'umol/l'),
    'i_an': ('i', 'silicate', 'i_an', 'Si', 'umol/l'),
    'si': ('i', 'silicate', 'i_an', 'Si', 'umol/l'),
    'sil': ('i', 'silicate', 'i_an', 'Si', 'umol/l'),
    'silicate': ('i', 'silicate', 'i_an', 'Si', 'umol/l'),
    'o': ('o', 'oxygen', 'o_an', 'O2', 'umol/l'),
    'o_an': ('o', 'oxygen', 'o_an', 'O2', 'umol/l'),
    'o2': ('o', 'oxygen', 'o_an', 'O2', 'umol/l'),
    'oxy': ('o', 'oxygen', 'o_an', 'O2', 'umol/l'),
    'oxygen': ('o', 'oxygen', 'o_an', 'O2', 'umol/l'),
}


def process_tracer(var_code, woa_dir, out_file):
    key = str(var_code).lower().strip()
    if key not in TRACER_LOOKUP:
        raise ValueError(
            f"Unknown var_code: {var_code}. Choose from: n, p, i, o or NO3, PO4, Si, O2"
        )

    code_char, var_folder, nc_var, out_var, units = TRACER_LOOKUP[key]
    folder_path = os.path.join(woa_dir, var_folder)

    # 1. Read annual file for full depth coordinate and deep levels
    ann_path = os.path.join(folder_path, f"woa23_all_{code_char}00_01.nc")
    if not os.path.isfile(ann_path):
        raise FileNotFoundError(f"Annual file not found: {ann_path}")

    with nc.Dataset(ann_path, 'r') as ds_ann:
        depth_full = np.array(ds_ann.variables['depth'][:], dtype=np.float32)
        lat = np.array(ds_ann.variables['lat'][:], dtype=np.float32)
        lon = np.array(ds_ann.variables['lon'][:], dtype=np.float32)
        ann_data = np.array(ds_ann.variables[nc_var][0, :, :, :], dtype=np.float32)
        ann_fill = float(getattr(ds_ann.variables[nc_var], '_FillValue', -9999.0))

    # Inspect first month to detect number of monthly levels dynamically
    m1_path = os.path.join(folder_path, f"woa23_all_{code_char}01_01.nc")
    with nc.Dataset(m1_path, 'r') as ds_m1:
        n_m_levs = ds_m1.variables['depth'].shape[0]

    deep_data = ann_data[n_m_levs:, :, :]
    # Abyssal padding: extend depth coordinate to 6000m by replicating the deepest level (5500m)
    if depth_full[-1] < 6000.0:
        depth_full = np.append(depth_full, np.float32(6000.0))
        deep_data = np.concatenate([deep_data, deep_data[-1:, :, :]], axis=0)

    n_deep = len(depth_full) - n_m_levs
    print(f"[{out_var}] Monthly levels: {n_m_levs}, Annual deep levels: {n_deep} (Total: {len(depth_full)})")

    # 2. Create output NetCDF
    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    with nc.Dataset(out_file, 'w', format='NETCDF4') as ds_out:
        create_cf_coordinates(
            ds_out,
            lons=lon,
            lats=lat,
            depths=depth_full,
            times=np.arange(0.5, 12.5, 1.0),
            time_units="months since 0001-01-01 00:00:00",
        )

        v_var = ds_out.createVariable(
            out_var, 'f4', ('time_counter', 'depth', 'lat', 'lon'),
            fill_value=ann_fill, zlib=True, complevel=4
        )
        v_var.units = units
        v_var.long_name = f"WOA23 Climatological {out_var}"

        # 3. Stream each month directly to file
        for m_idx in range(12):
            m_str = f"{m_idx + 1:02d}"
            m_path = os.path.join(folder_path, f"woa23_all_{code_char}{m_str}_01.nc")
            if not os.path.isfile(m_path):
                raise FileNotFoundError(f"Monthly file not found: {m_path}")

            step_data = np.full((len(depth_full), len(lat), len(lon)), ann_fill, dtype=np.float32)
            with nc.Dataset(m_path, 'r') as ds_m:
                step_data[:n_m_levs, :, :] = ds_m.variables[nc_var][0, :, :, :]
            step_data[n_m_levs:, :, :] = deep_data
            v_var[m_idx, :, :, :] = step_data

    print(f"Successfully generated combined WOA23 file: {out_file}")
