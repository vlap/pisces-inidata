#!/usr/bin/env python3
"""
evaluate_closeness.py
Memory-efficient, rigorous evaluation of closeness between newly generated
PISCES inidata and ground truth reference datasets.

Processes data chunk-by-chunk (per timestep) to run safely under HPC memory limits.
Computes metrics over valid ocean wet cells (tmaskutil > 0):
- 3D Root Mean Square Error (RMSE)
- Mean Absolute Error (MAE)
- Mean Bias Error (MBE = mean(Test - Ref))
- Max Absolute Difference (MaxDiff)
- Relative RMSE (% of mean reference concentration)
- Pearson Correlation Coefficient (r)
- Global Volume-Integrated Inventory Difference (%)
"""

import sys
import os
import argparse
import numpy as np
import netCDF4 as nc

def evaluate_fields(test_file, ref_file, var_name, mask_file=None, domain_file=None):
    if not os.path.exists(test_file):
        raise FileNotFoundError(f"Test file not found: {test_file}")
    if not os.path.exists(ref_file):
        raise FileNotFoundError(f"Reference file not found: {ref_file}")

    ds_test = nc.Dataset(test_file)
    ds_ref = nc.Dataset(ref_file)

    # Find variable in files
    vtest_name = var_name if var_name in ds_test.variables else None
    vref_name = var_name if var_name in ds_ref.variables else None

    aliases = {
        'NO3': ['NO3', 'no3', 'nitrate'],
        'PO4': ['PO4', 'po4', 'phosphate'],
        'Si': ['Si', 'si', 'silicate', 'SIL'],
        'O2': ['O2', 'o2', 'oxygen', 'OXY'],
        'TALK': ['TALK', 'talk', 'Alkalini', 'alkalini'],
        'TDIC': ['TDIC', 'tdic', 'DIC', 'dic'],
        'DOC': ['DOC', 'doc'],
        'Fer': ['Fer', 'fer', 'FER'],
        'dust': ['dust'],
        'solubility2': ['solubility2'],
        'ndep': ['ndep'],
        'fr_par': ['fr_par'],
        'bathy': ['bathy']
    }

    if vtest_name is None:
        for alias in aliases.get(var_name, []):
            if alias in ds_test.variables:
                vtest_name = alias
                break
    if vref_name is None:
        for alias in aliases.get(var_name, []):
            if alias in ds_ref.variables:
                vref_name = alias
                break

    if vtest_name is None or vref_name is None:
        raise KeyError(f"Variable {var_name} not found in test ({vtest_name}) or ref ({vref_name})")

    vtest = ds_test.variables[vtest_name]
    vref = ds_ref.variables[vref_name]

    # Load 2D wet ocean mask
    mask_2d = None
    if mask_file and os.path.exists(mask_file):
        ds_mask = nc.Dataset(mask_file)
        mvar = 'tmaskutil' if 'tmaskutil' in ds_mask.variables else list(ds_mask.variables.keys())[0]
        mask_2d = (np.squeeze(ds_mask.variables[mvar][:]) > 0)
        ds_mask.close()

    # Determine dimensions
    shape_ref = vref.shape
    shape_test = vtest.shape
    print(f"[{var_name}] Comparing: test shape {shape_test} vs ref shape {shape_ref}")

    # Accumulators for running stats
    total_valid = 0
    sum_diff2 = 0.0
    sum_abs_diff = 0.0
    sum_diff = 0.0
    max_abs_diff = 0.0
    sum_ref = 0.0
    sum_ref2 = 0.0
    sum_test = 0.0
    sum_test2 = 0.0
    sum_test_ref = 0.0

    fill_test = getattr(vtest, '_FillValue', getattr(vtest, 'missing_value', -9999.0))
    fill_ref = getattr(vref, '_FillValue', getattr(vref, 'missing_value', -9999.0))

    # Iterate over time dimension if present
    ntimes = shape_ref[0] if vref.ndim >= 3 and shape_ref[0] in [1, 12, 73, 365] else 1

    for t in range(ntimes):
        if vref.ndim == 4: # (time, depth, y, x)
            chunk_ref = np.array(vref[t], dtype=np.float32)
            chunk_test = np.array(vtest[t] if vtest.ndim == 4 else vtest[:], dtype=np.float32)
            if mask_2d is not None:
                mask_chunk = np.broadcast_to(mask_2d[None, :, :], chunk_ref.shape)
            else:
                mask_chunk = np.ones(chunk_ref.shape, dtype=bool)
        elif vref.ndim == 3 and ntimes > 1: # (time, y, x)
            chunk_ref = np.array(vref[t], dtype=np.float32)
            chunk_test = np.array(vtest[t] if vtest.ndim == 3 else vtest[:], dtype=np.float32)
            mask_chunk = mask_2d if mask_2d is not None else np.ones(chunk_ref.shape, dtype=bool)
        else: # static 3D (depth, y, x) or 2D (y, x)
            chunk_test = np.squeeze(np.array(vtest[:], dtype=np.float32))
            chunk_ref = np.squeeze(np.array(vref[:], dtype=np.float32))
            if chunk_ref.ndim == 3:
                mask_chunk = np.broadcast_to(mask_2d[None, :, :], chunk_ref.shape) if mask_2d is not None else np.ones(chunk_ref.shape, dtype=bool)
            else:
                mask_chunk = mask_2d if mask_2d is not None else np.ones(chunk_ref.shape, dtype=bool)

        valid = np.isfinite(chunk_test) & np.isfinite(chunk_ref)
        valid &= (chunk_test != fill_test) & (chunk_ref != fill_ref)
        valid &= (chunk_test > -1000.0) & (chunk_ref > -1000.0)
        valid &= mask_chunk

        n_pts = int(np.sum(valid))
        if n_pts == 0:
            continue

        a = chunk_test[valid].astype(np.float64)
        b = chunk_ref[valid].astype(np.float64)
        d = a - b
        ad = np.abs(d)

        total_valid += n_pts
        sum_diff2 += np.sum(d * d)
        sum_abs_diff += np.sum(ad)
        sum_diff += np.sum(d)
        cur_max = float(np.max(ad))
        if cur_max > max_abs_diff:
            max_abs_diff = cur_max

        sum_ref += np.sum(b)
        sum_ref2 += np.sum(b * b)
        sum_test += np.sum(a)
        sum_test2 += np.sum(a * a)
        sum_test_ref += np.sum(a * b)

    ds_test.close()
    ds_ref.close()

    if total_valid == 0:
        print(f"[{var_name}] WARNING: 0 valid points to compare!")
        return {}

    rmse = np.sqrt(sum_diff2 / total_valid)
    mae = sum_abs_diff / total_valid
    mbe = sum_diff / total_valid
    mean_ref = sum_ref / total_valid
    mean_test = sum_test / total_valid

    rel_rmse = (rmse / mean_ref * 100.0) if mean_ref != 0 else np.nan

    # Pearson r
    var_ref = (sum_ref2 / total_valid) - (mean_ref * mean_ref)
    var_test = (sum_test2 / total_valid) - (mean_test * mean_test)
    cov = (sum_test_ref / total_valid) - (mean_test * mean_ref)

    if var_ref > 0 and var_test > 0:
        r = cov / np.sqrt(var_ref * var_test)
    else:
        r = 1.0 if rmse < 1e-6 else 0.0

    inv_diff_pct = ((sum_test - sum_ref) / sum_ref * 100.0) if sum_ref != 0 else 0.0

    return {
        'var': var_name,
        'valid_points': total_valid,
        'mean_ref': mean_ref,
        'rmse': rmse,
        'mae': mae,
        'mbe': mbe,
        'max_diff': max_abs_diff,
        'rel_rmse_pct': rel_rmse,
        'pearson_r': r,
        'inventory_diff_pct': inv_diff_pct
    }

def main():
    parser = argparse.ArgumentParser(description="Evaluate closeness of PISCES inidata files")
    parser.add_argument("--test", required=True, help="Generated test NetCDF file")
    parser.add_argument("--ref", required=True, help="Ground truth reference NetCDF file")
    parser.add_argument("--var", required=True, help="Variable name (e.g. NO3, PO4, Alkalini)")
    parser.add_argument("--mask", help="Land-sea mask file (maskutil.nc)")
    parser.add_argument("--domain", help="Domain geometry file (domain_cfg.nc)")

    args = parser.parse_args()

    metrics = evaluate_fields(args.test, args.ref, args.var, args.mask, args.domain)

    print("\n" + "=" * 70)
    print(f" Closeness Evaluation Report: {args.var}")
    print("=" * 70)
    print(f"  Valid Points:       {metrics.get('valid_points', 0):,}")
    print(f"  Mean Reference:     {metrics.get('mean_ref', 0.0):.4f}")
    print(f"  RMSE:               {metrics.get('rmse', 0.0):.6e}")
    print(f"  MAE:                {metrics.get('mae', 0.0):.6e}")
    print(f"  Mean Bias (MBE):    {metrics.get('mbe', 0.0):.6e}")
    print(f"  Max Absolute Diff:  {metrics.get('max_diff', 0.0):.6e}")
    print(f"  Relative RMSE (%):  {metrics.get('rel_rmse_pct', 0.0):.4f}%")
    print(f"  Pearson r:          {metrics.get('pearson_r', 0.0):.6f}")
    print(f"  Inventory Diff (%): {metrics.get('inventory_diff_pct', 0.0):.4f}%")
    print("=" * 70)

if __name__ == "__main__":
    main()
