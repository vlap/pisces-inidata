"""
Validation Scoreboard Module
Computes a comprehensive validation scoreboard comparing interpolated PISCES
inidata products on ORCA2 (or other NEMO grids) against official SETTE ground truth references.
"""

import os
import argparse
from typing import Dict, Any, Optional
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
    'river': ['riverdin', 'riverdic']
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
    # Fallback to case-insensitive match
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

        # Mask invalid values
        mask_test = (
            np.ma.getmaskarray(data_test) if np.ma.is_masked(data_test)
            else np.zeros(data_test.shape, dtype=bool)
        )
        mask_ref = (
            np.ma.getmaskarray(data_ref) if np.ma.is_masked(data_ref)
            else np.zeros(data_ref.shape, dtype=bool)
        )

        combined_mask = mask_test | mask_ref | np.isnan(data_test) | np.isnan(data_ref)

        # Flatten valid cells
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

        # Correlation
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


def generate_scoreboard(results: list, output_md_path: Optional[str] = None) -> str:
    """
    Renders diagnostic results list into a GitHub Flavored Markdown scoreboard table.
    """
    lines = []
    lines.append("# PISCES Inidata Validation Scoreboard (ORCA2 vs SETTE Ground Truth)")
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
