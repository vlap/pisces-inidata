"""
Verification module for generated PISCES initial conditions and boundary forcings.
Inspects all 15 expected NetCDF output files, verifies non-empty dimensions,
and calculates physical min/mean/max bounds to guarantee no blank/all-zero/NaN outputs.
"""

import os
from typing import Dict, Any, List, Tuple, Optional
import netCDF4 as nc
import numpy as np


def _load_expected_products() -> List[Tuple[str, str]]:
    try:
        from pisces_inidata.catalog import load_catalog
        cat = load_catalog()
        fields = cat.get("conventions", {}).get("nemo4_ece4", {}).get("fields", {})
        prods = []
        seen = set()
        for var, meta in fields.items():
            pattern = meta.get("output_file", f"data_{var}_{{grid}}.nc")
            if pattern not in seen:
                seen.add(pattern)
                prods.append((pattern, meta.get("target_var", var)))
        if prods:
            return prods
    except Exception:
        pass
    return [
        ('data_NO3_{grid}.nc', 'NO3'),
        ('data_PO4_{grid}.nc', 'PO4'),
        ('data_Si_{grid}.nc', 'Si'),
        ('data_O2_{grid}.nc', 'O2'),
        ('data_TALK_{grid}.nc', 'Alkalini'),
        ('data_TDIC_{grid}.nc', 'DIC'),
        ('data_PiDIC_{grid}.nc', 'DIC'),
        ('data_DOC_{grid}.nc', 'DOC'),
        ('data_Fer_{grid}.nc', 'Fer'),
        ('dust.orca.nc', 'dust'),
        ('ndeposition.orca.nc', 'ndep'),
        ('par.orca.nc', 'fr_par'),
        ('bathy.orca.nc', 'bathy'),
        ('hydrofe.orca.nc', 'epsdb'),
        ('river.orca.nc', 'riverdin'),
    ]


EXPECTED_PRODUCTS = _load_expected_products()

VAR_ALIASES = {
    'NO3': ['NO3', 'no3', 'nitrate', 'n_an'],
    'PO4': ['PO4', 'po4', 'phosphate', 'p_an'],
    'Si': ['Si', 'si', 'silicate', 'SIL', 'i_an'],
    'O2': ['O2', 'o2', 'oxygen', 'OXY', 'o_an'],
    'TALK': ['TALK', 'talk', 'Alkalini', 'alkalini', 'TAlk'],
    'Alkalini': ['Alkalini', 'alkalini', 'TALK', 'talk', 'TAlk'],
    'TDIC': ['TDIC', 'tdic', 'DIC', 'dic', 'TCO2'],
    'DIC': ['DIC', 'dic', 'TDIC', 'tdic', 'PiDIC', 'pidic', 'TCO2'],
    'PiDIC': ['PiDIC', 'pidic', 'DIC', 'dic', 'PI_TCO2'],
    'DOC': ['DOC', 'doc'],
    'Fer': ['Fer', 'fer', 'FER'],
    'dust': ['dust', 'dustfer'],
    'ndep': ['ndep2', 'ndep'],
    'par': ['fr_par', 'par'],
    'bathy': ['bathy'],
    'hydrofe': ['epsdb', 'hydrofe'],
    'river': ['riverdin', 'riverdic'],
    'riverdin': ['riverdin', 'river_din'],
    'riverdic': ['riverdic'],
    'riverdip': ['riverdip'],
    'riverdon': ['riverdon'],
    'riverdop': ['riverdop'],
    'riverdoc': ['riverdoc'],
    'riverdsi': ['riverdsi'],
}


def find_var(ds: nc.Dataset, candidates: Any) -> Optional[str]:
    """Finds first matching variable name in dataset among candidates (case-insensitive fallback)."""
    for c in candidates:
        if c in ds.variables:
            return c
    for c in candidates:
        c_low = str(c).lower()
        for v in ds.variables:
            if c_low == v.lower():
                return v
    return None


def find_variable(ds: nc.Dataset, target_var: str):
    """Locates target variable or supported aliases within a NetCDF dataset."""
    candidates = [target_var] + VAR_ALIASES.get(target_var, [])
    vname = find_var(ds, candidates)
    return ds.variables[vname] if vname else None


def verify_output_directory(out_dir: str, grid_name: str = "eORCA025") -> Tuple[int, List[Dict[str, Any]]]:
    """
    Verifies all expected inidata products in the specified output directory.

    Returns:
        Tuple of (exit_code: int [0 for all pass, 1 for any failure], results: List[Dict])
    """
    results = []
    all_ok = True

    header = (
        f"| {'Product / File':30s} | {'Variable':9s} | {'Shape':18s} | "
        f"{'Size':9s} | {'Min':10s} | {'Mean':10s} | {'Max':10s} | {'Status':6s} |"
    )
    sep = (
        '|' + '-' * 32 + '|' + '-' * 11 + '|' + '-' * 20 + '|'
        + '-' * 11 + '|' + '-' * 12 + '|' + '-' * 12 + '|' + '-' * 12 + '|' + '-' * 8 + '|'
    )
    print("\n" + header)
    print(sep)

    for tmpl, vname in EXPECTED_PRODUCTS:
        fname = tmpl.format(grid=grid_name)
        fpath = os.path.join(out_dir, fname)

        res: Dict[str, Any] = {
            'file': fname,
            'variable': vname,
            'path': fpath,
            'exists': os.path.exists(fpath),
            'shape': None,
            'size_mb': 0.0,
            'min': None,
            'mean': None,
            'max': None,
            'status': 'FAIL'
        }

        if not res['exists']:
            print(f"| {fname:30s} | {vname:9s} | {'MISSING':18s} | {'-':9s} | "
                  f"{'-':10s} | {'-':10s} | {'-':10s} | FAIL   |")
            all_ok = False
            results.append(res)
            continue

        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        res['size_mb'] = size_mb
        size_str = f"{size_mb:.1f} MB" if size_mb < 1000 else f"{size_mb / 1024:.2f} GB"

        try:
            with nc.Dataset(fpath, 'r') as ds:
                var_obj = find_variable(ds, vname)
                if var_obj is None:
                    print(f"| {fname:30s} | {vname:9s} | {'VAR_NOT_FOUND':18s} | {size_str:9s} | "
                          f"{'-':10s} | {'-':10s} | {'-':10s} | FAIL   |")
                    all_ok = False
                    results.append(res)
                    continue

                res['shape'] = var_obj.shape
                # Inspect 2D slice or full field
                data = var_obj[0] if var_obj.ndim >= 3 else var_obj[:]
                if hasattr(data, 'mask'):
                    valid_vals = data.data[~data.mask]
                else:
                    valid_vals = data[~np.isnan(data)]

                if len(valid_vals) > 0:
                    vmin = float(np.min(valid_vals))
                    vmean = float(np.mean(valid_vals))
                    vmax = float(np.max(valid_vals))
                else:
                    vmin, vmean, vmax = float('nan'), float('nan'), float('nan')

                res['min'] = vmin
                res['mean'] = vmean
                res['max'] = vmax

                # Status check: non-empty valid values, mean is not NaN, and field is not completely blank (all zeros)
                is_valid = len(valid_vals) > 0 and not np.isnan(vmean) and (vmin != 0.0 or vmax != 0.0)
                status = 'PASS' if is_valid else 'FAIL'
                res['status'] = status
                if status == 'FAIL':
                    all_ok = False

                shape_str = str(var_obj.shape)
                print(
                    f"| {fname:30s} | {vname:9s} | {shape_str:18s} | {size_str:9s} | "
                    f"{vmin:10.4g} | {vmean:10.4g} | {vmax:10.4g} | {status:6s} |"
                )
        except Exception as e:
            print(f"| {fname:30s} | {vname:9s} | {'READ_ERROR':18s} | {size_str:9s} | "
                  f"{'-':10s} | {'-':10s} | {'-':10s} | FAIL   |")
            res['error'] = str(e)
            all_ok = False

        results.append(res)

    print(sep)
    passed_count = sum(1 for r in results if r['status'] == 'PASS')
    total_count = len(results)
    print("\n========================================================================")
    print(f"  VERIFICATION RESULT: {passed_count}/{total_count} PASSED"
          f" ({'PASS' if all_ok else 'FAIL - Inspection found blank/missing files'})")
    print("========================================================================\n")

    return (0 if all_ok else 1), results
