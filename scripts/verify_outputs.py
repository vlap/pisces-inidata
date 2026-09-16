#!/usr/bin/env python3
"""
Verification script for generated PISCES initial conditions.
Inspects all expected NetCDF output files, verifies non-empty dimensions,
calculates min/mean/max bounds to ensure no blank/NaN outputs.
"""

import os
import sys
import netCDF4 as nc
import numpy as np

out_dir = sys.argv[1] if len(sys.argv) > 1 else 'output_eORCA025'

expected = [
    ('data_NO3_eORCA025.nc', 'NO3'),
    ('data_PO4_eORCA025.nc', 'PO4'),
    ('data_Si_eORCA025.nc', 'Si'),
    ('data_O2_eORCA025.nc', 'O2'),
    ('data_TALK_eORCA025.nc', 'Alkalini'),
    ('data_TDIC_eORCA025.nc', 'DIC'),
    ('data_PiDIC_eORCA025.nc', 'DIC'),
    ('data_DOC_eORCA025.nc', 'DOC'),
    ('data_Fer_eORCA025.nc', 'Fer'),
    ('dust.orca.nc', 'dust'),
    ('ndeposition.orca.nc', 'ndep'),
    ('par.orca.nc', 'fr_par'),
    ('bathy.orca.nc', 'bathy'),
    ('hydrofe.orca.nc', 'epsdb'),
    ('river.orca.nc', 'riverdin'),
]

header = (
    f"| {'Product / File':28s} | {'Variable':9s} | {'Shape':18s} | "
    f"{'Size':9s} | {'Min':10s} | {'Mean':10s} | {'Max':10s} | {'Status':6s} |"
)
sep = (
    '|' + '-' * 30 + '|' + '-' * 11 + '|' + '-' * 20 + '|'
    + '-' * 11 + '|' + '-' * 12 + '|' + '-' * 12 + '|' + '-' * 12 + '|' + '-' * 8 + '|'
)
print(header)
print(sep)

all_ok = True
for fname, vname in expected:
    fpath = os.path.join(out_dir, fname)
    if not os.path.exists(fpath):
        print(f"| {fname:28s} | {vname:9s} | {'MISSING':18s} | {'-':9s} | {'-':10s} | {'-':10s} | {'-':10s} | FAIL   |")
        all_ok = False
        continue
    size_mb = os.path.getsize(fpath) / (1024 * 1024)
    size_str = f"{size_mb:.1f} MB" if size_mb < 1000 else f"{size_mb / 1024:.2f} GB"
    with nc.Dataset(fpath, 'r') as ds:
        v = ds.variables[vname]
        data = v[0] if v.ndim >= 3 else v[:]
        # Mask out fill values or nans
        if hasattr(data, 'mask'):
            valid_vals = data.data[~data.mask]
        else:
            valid_vals = data[~np.isnan(data)]

        vmin = float(np.min(valid_vals)) if len(valid_vals) > 0 else float('nan')
        vmean = float(np.mean(valid_vals)) if len(valid_vals) > 0 else float('nan')
        vmax = float(np.max(valid_vals)) if len(valid_vals) > 0 else float('nan')

        status = 'PASS' if len(valid_vals) > 0 and not np.isnan(vmean) and (vmin != 0 or vmax != 0) else 'FAIL'
        if status == 'FAIL':
            all_ok = False
        shape_str = str(v.shape)
        print(
            f"| {fname:28s} | {vname:9s} | {shape_str:18s} | {size_str:9s} | "
            f"{vmin:10.4g} | {vmean:10.4g} | {vmax:10.4g} | {status:6s} |"
        )

print('\n========================================================================')
print('  OVERALL RESULT:', 'PASS (All 15 products valid & non-blank)' if all_ok else 'FAIL')
print('========================================================================')
sys.exit(0 if all_ok else 1)
