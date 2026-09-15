"""
Validation Scoreboard Module
Computes a comprehensive validation scoreboard comparing interpolated PISCES
inidata products on ORCA2 (or other NEMO grids) against official SETTE ground truth references.
Also includes mass-conservation verification for boundary and surface forcings.
"""

import os
import argparse
from typing import Dict, Any, Optional, List
import numpy as np
import netCDF4 as nc
from scipy.stats import spearmanr

ALIASES = {
    'NO3': ['NO3', 'no3', 'nitrate', 'n_an'],
    'PO4': ['PO4', 'po4', 'phosphate', 'p_an'],
    'Si': ['Si', 'si', 'silicate', 'SIL', 'i_an'],
    'O2': ['O2', 'o2', 'oxygen', 'OXY', 'o_an'],
    'TALK': ['TALK', 'talk', 'Alkalini', 'alkalini', 'TAlk'],
    'TDIC': ['TDIC', 'tdic', 'DIC', 'dic', 'TCO2'],
    'PiDIC': ['PiDIC', 'pidic', 'DIC', 'dic', 'PI_TCO2'],
    'DOC': ['DOC', 'doc'],
    'Fer': ['Fer', 'fer', 'FER'],
    'dust': ['dust', 'dustfer'],
    'ndep': ['ndep2', 'ndep'],
    'par': ['fr_par'],
    'bathy': ['bathy'],
    'hydrofe': ['epsdb'],
    'river': ['riverdin', 'riverdic'],
    'riverdin': ['riverdin'],
    'riverdic': ['riverdic'],
    'riverdip': ['riverdip'],
    'riverdon': ['riverdon'],
    'riverdop': ['riverdop'],
    'riverdoc': ['riverdoc'],
    'riverdsi': ['riverdsi'],
}

UNITS = {
    'NO3': 'umol N/L',
    'PO4': 'umol P/L',
    'Si': 'umol Si/L',
    'O2': 'umol O2/L',
    'TALK': 'umol eq/L',
    'TDIC': 'umol C/L',
    'PiDIC': 'umol C/L',
    'DOC': 'umol C/L',
    'Fer': 'nmol Fe/L',
    'dust': 'g/m2/yr',
    'ndep': 'gN/m2/yr',
    'par': 'fraction',
    'bathy': 'fraction',
    'hydrofe': 'mol Fe/m2/s',
    'river': 'MgN/m2/yr'
}


def find_var(ds: nc.Dataset, candidates: list) -> Optional[str]:
    for c in candidates:
        if c in ds.variables:
            return c
    for c in candidates:
        for v in ds.variables:
            if c.lower() == v.lower():
                return v
    return None


def compute_diagnostics(test_file: str, ref_file: str, var_key: str) -> Dict[str, Any]:
    """
    Computes statistical validation diagnostics between test_file and ref_file.
    """
    if not os.path.exists(test_file):
        raise FileNotFoundError(f"Test file not found: {test_file}")
    if not os.path.exists(ref_file):
        raise FileNotFoundError(f"Reference file not found: {ref_file}")

    candidates = ALIASES.get(var_key, [var_key])

    with nc.Dataset(test_file, 'r') as ds_test, nc.Dataset(ref_file, 'r') as ds_ref:
        var_test_name = find_var(ds_test, candidates)
        var_ref_name = find_var(ds_ref, candidates)

        if not var_test_name:
            raise KeyError(
                f"Variable '{var_key}' (aliases: {candidates}) not found in test {test_file}. "
                f"Available: {list(ds_test.variables.keys())}"
            )
        if not var_ref_name:
            raise KeyError(
                f"Variable '{var_key}' (aliases: {candidates}) not found in ref {ref_file}. "
                f"Available: {list(ds_ref.variables.keys())}"
            )

        data_test = np.squeeze(ds_test.variables[var_test_name][:])
        data_ref = np.squeeze(ds_ref.variables[var_ref_name][:])

        if data_test.shape != data_ref.shape:
            raise ValueError(f"Shape mismatch for {var_key}: test={data_test.shape} vs ref={data_ref.shape}")

        mask_test = (
            np.ma.getmaskarray(data_test) if np.ma.is_masked(data_test)
            else np.zeros(data_test.shape, dtype=bool)
        )
        mask_ref = (
            np.ma.getmaskarray(data_ref) if np.ma.is_masked(data_ref)
            else np.zeros(data_ref.shape, dtype=bool)
        )

        combined_mask = mask_test | mask_ref | np.isnan(data_test) | np.isnan(data_ref)

        valid_test = np.array(data_test[~combined_mask], dtype=np.float64)
        valid_ref = np.array(data_ref[~combined_mask], dtype=np.float64)

        n_valid = len(valid_test)
        total_cells = data_test.size
        coverage_pct = (n_valid / total_cells) * 100.0 if total_cells > 0 else 0.0

        if n_valid == 0:
            return {
                'var': var_key,
                'valid_count': 0,
                'coverage_pct': 0.0,
                'rmse': np.nan,
                'nrmse_pct': np.nan,
                'mae': np.nan,
                'mbe': np.nan,
                'rel_bias_pct': np.nan,
                'r': np.nan,
                'spearman_rho': np.nan,
                'max_diff': np.nan,
                'mean_ref': np.nan,
                'mean_test': np.nan,
                'unit': UNITS.get(var_key, '')
            }

        diff = valid_test - valid_ref
        abs_diff = np.abs(diff)

        mean_ref = float(np.mean(valid_ref))
        mean_test = float(np.mean(valid_test))
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        mae = float(np.mean(abs_diff))
        mbe = float(np.mean(diff))
        max_diff = float(np.max(abs_diff))

        nrmse_pct = (rmse / abs(mean_ref) * 100.0) if abs(mean_ref) > 1e-12 else np.nan
        rel_bias_pct = (mbe / abs(mean_ref) * 100.0) if abs(mean_ref) > 1e-12 else np.nan

        std_test = np.std(valid_test)
        std_ref = np.std(valid_ref)
        if std_test > 1e-12 and std_ref > 1e-12:
            r = float(np.corrcoef(valid_test, valid_ref)[0, 1])
            try:
                if n_valid > 200000:
                    idx = np.random.choice(n_valid, 100000, replace=False)
                    rho = float(spearmanr(valid_test[idx], valid_ref[idx]).statistic)
                else:
                    rho = float(spearmanr(valid_test, valid_ref).statistic)
            except Exception:
                rho = np.nan
        else:
            r = np.nan
            rho = np.nan

        return {
            'var': var_key,
            'valid_count': n_valid,
            'coverage_pct': coverage_pct,
            'rmse': rmse,
            'nrmse_pct': nrmse_pct,
            'mae': mae,
            'mbe': mbe,
            'rel_bias_pct': rel_bias_pct,
            'r': r,
            'spearman_rho': rho,
            'max_diff': max_diff,
            'mean_ref': mean_ref,
            'mean_test': mean_test,
            'unit': UNITS.get(var_key, '')
        }


def compute_mass_conservation(
    test_file: str,
    ref_file: str,
    var_name: str,
    test_area_file: Optional[str] = None,
    ref_area_file: Optional[str] = None,
    tolerance_pct: float = 0.5
) -> Dict[str, Any]:
    """
    Verifies mass conservation of surface/boundary fluxes between test and reference datasets.
    Calculates spatial integral: Integral = sum(flux * area).
    """
    if not os.path.exists(test_file):
        raise FileNotFoundError(f"Test file not found: {test_file}")
    if not os.path.exists(ref_file):
        raise FileNotFoundError(f"Reference file not found: {ref_file}")

    candidates = ALIASES.get(var_name, [var_name])
    with nc.Dataset(test_file, 'r') as ds_test, nc.Dataset(ref_file, 'r') as ds_ref:
        v_test = find_var(ds_test, candidates)
        v_ref = find_var(ds_ref, candidates)

        if not v_test or not v_ref:
            raise KeyError(f"Variable '{var_name}' not found in test ({test_file}) or ref ({ref_file})")

        data_test = np.squeeze(ds_test.variables[v_test][:])
        data_ref = np.squeeze(ds_ref.variables[v_ref][:])

        test_masked = np.ma.masked_invalid(data_test)
        ref_masked = np.ma.masked_invalid(data_ref)

        area_test = 1.0
        area_ref = 1.0

        if test_area_file and os.path.exists(test_area_file):
            with nc.Dataset(test_area_file, 'r') as ds_a:
                a_var = find_var(ds_a, ['area', 'e1t_e2t', 'cell_area'])
                if a_var:
                    area_test = np.squeeze(ds_a.variables[a_var][:])

        if ref_area_file and os.path.exists(ref_area_file):
            with nc.Dataset(ref_area_file, 'r') as ds_a:
                a_var = find_var(ds_a, ['area', 'e1t_e2t', 'cell_area'])
                if a_var:
                    area_ref = np.squeeze(ds_a.variables[a_var][:])

        integral_test = float(np.sum(test_masked * area_test))
        integral_ref = float(np.sum(ref_masked * area_ref))

        rel_diff_pct = (
            ((integral_test - integral_ref) / abs(integral_ref) * 100.0)
            if abs(integral_ref) > 1e-12 else 0.0
        )
        passed = abs(rel_diff_pct) <= tolerance_pct

        return {
            'var': var_name,
            'integral_test': integral_test,
            'integral_ref': integral_ref,
            'rel_diff_pct': rel_diff_pct,
            'tolerance_pct': tolerance_pct,
            'passed': passed,
            'status': "PASS" if passed else "FAIL"
        }


def generate_scoreboard(
    results: List[Dict[str, Any]],
    conservation_results: Optional[List[Dict[str, Any]]] = None,
    output_md_path: Optional[str] = None
) -> str:
    """
    Renders diagnostic results list into a GitHub Flavored Markdown scoreboard table.
    """
    lines = []
    lines.append("# PISCES Inidata Validation Scoreboard (ORCA2 vs SETTE Ground Truth)")
    lines.append("")
    lines.append("## 1. Tracers and Boundary Forcings Closeness Metrics")
    lines.append("")
    lines.append(
        "| Variable | Product Evaluated | Unit | N Valid | Pearson r | "
        "Spearman $\\rho$ | RMSE | NRMSE (%) | MAE | Bias (MBE) | Rel Bias (%) | Max Diff |"
    )
    lines.append(
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    )

    for r in results:
        r_val = f"{r['r']:.4f}" if not np.isnan(r['r']) else "N/A"
        rho_val = f"{r['spearman_rho']:.4f}" if not np.isnan(r['spearman_rho']) else "N/A"
        rmse_val = f"{r['rmse']:.4g}" if not np.isnan(r['rmse']) else "N/A"
        nrmse_val = f"{r['nrmse_pct']:.2f}%" if not np.isnan(r['nrmse_pct']) else "N/A"
        mae_val = f"{r['mae']:.4g}" if not np.isnan(r['mae']) else "N/A"
        mbe_val = f"{r['mbe']:+.4g}" if not np.isnan(r['mbe']) else "N/A"
        rel_bias = f"{r['rel_bias_pct']:+.2f}%" if not np.isnan(r['rel_bias_pct']) else "N/A"
        max_diff = f"{r['max_diff']:.4g}" if not np.isnan(r['max_diff']) else "N/A"
        prod = r.get('product', 'Default')

        lines.append(
            f"| **{r['var']}** | `{prod}` | {r['unit']} | {r['valid_count']} | "
            f"{r_val} | {rho_val} | {rmse_val} | {nrmse_val} | {mae_val} | {mbe_val} | {rel_bias} | {max_diff} |"
        )

    if conservation_results:
        lines.append("")
        lines.append("## 2. Mass Conservation Verification (Boundary Forcings)")
        lines.append("")
        lines.append("| Variable | Target Integral | Ref Integral | Rel Diff (%) | Tolerance | Status |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for c in conservation_results:
            stat_str = f"**{c['status']}**" if c['passed'] else f"<span style='color:red;'>**{c['status']}**</span>"
            lines.append(
                f"| **{c['var']}** | {c['integral_test']:.4e} | {c['integral_ref']:.4e} | "
                f"{c['rel_diff_pct']:+.2f}% | $\\le {c['tolerance_pct']:.1f}\\%$ | {stat_str} |"
            )

    lines.append("")
    md_content = "\n".join(lines)

    if output_md_path:
        with open(output_md_path, 'w') as f:
            f.write(md_content)
        print(f"Scoreboard saved to {output_md_path}")

    return md_content


def main():
    parser = argparse.ArgumentParser(
        description="Generate PISCES inidata validation scoreboard against SETTE ground truth."
    )
    parser.add_argument("--test-file", help="Path to single test NetCDF file")
    parser.add_argument("--ref-file", help="Path to single reference NetCDF file")
    parser.add_argument("--var", help="Variable name (e.g. NO3, PO4, TALK, DOC)")
    parser.add_argument("--out-md", default="VALIDATION_SCOREBOARD_ORCA2.md", help="Output markdown path")
    args = parser.parse_args()

    if args.test_file and args.ref_file and args.var:
        res = compute_diagnostics(args.test_file, args.ref_file, args.var)
        print(generate_scoreboard([res]))
    else:
        print("Run with --test-file, --ref-file, and --var or via scripts/run_validation_suite.sh")


if __name__ == "__main__":
    main()
