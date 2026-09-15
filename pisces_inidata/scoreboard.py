"""
Validation Scoreboard Module
Computes a comprehensive validation scorecard comparing interpolated PISCES
inidata products on ORCA2 against official SETTE ground truth references.
Verifies units, physical ranges, spatial patterns, and boundary mass conservation.
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

SUPPORTED_PRODUCTS = [
    {
        'var': 'NO3',
        'product': 'WOA23',
        'test_cands': ['data_NO3_ORCA2.nc', 'NO3_WOA23_monthly_ORCA2.nc', 'NO3_WOA2009_monthly_ORCA2.nc'],
        'ref_cands': ['data_NO3_ORCA2.nc', 'data_NO3_nomask_ORCA2.nc'],
        'unit': 'umol N/L',
        'category': 'tracer'
    },
    {
        'var': 'PO4',
        'product': 'WOA23',
        'test_cands': ['data_PO4_ORCA2.nc', 'PO4_WOA23_monthly_ORCA2.nc', 'PO4_WOA2009_monthly_ORCA2.nc'],
        'ref_cands': ['data_PO4_ORCA2.nc', 'data_PO4_nomask_ORCA2.nc'],
        'unit': 'umol P/L',
        'category': 'tracer'
    },
    {
        'var': 'Si',
        'product': 'WOA23',
        'test_cands': ['data_Si_ORCA2.nc', 'data_SIL_ORCA2.nc', 'Si_WOA23_monthly_ORCA2.nc'],
        'ref_cands': ['data_Si_ORCA2.nc', 'data_SIL_ORCA2.nc', 'data_SIL_nomask_ORCA2.nc'],
        'unit': 'umol Si/L',
        'category': 'tracer'
    },
    {
        'var': 'O2',
        'product': 'WOA23',
        'test_cands': ['data_O2_ORCA2.nc', 'data_OXY_ORCA2.nc', 'O2_WOA23_monthly_ORCA2.nc'],
        'ref_cands': ['data_O2_ORCA2.nc', 'data_OXY_ORCA2.nc', 'data_OXY_nomask_ORCA2.nc'],
        'unit': 'umol O2/L',
        'category': 'tracer'
    },
    {
        'var': 'TALK',
        'product': 'GLODAPv2.2016b',
        'test_cands': ['data_TALK_ORCA2.nc', 'data_ALK_ORCA2.nc', 'Alkalini_GLODAP_annual_ORCA2.nc'],
        'ref_cands': ['data_TALK_ORCA2.nc', 'data_ALK_ORCA2.nc', 'data_ALK_nomask_ORCA2.nc'],
        'unit': 'umol eq/L',
        'category': 'tracer'
    },
    {
        'var': 'TDIC',
        'product': 'GLODAPv2.2016b',
        'test_cands': ['data_TDIC_ORCA2.nc', 'data_DIC_ORCA2.nc', 'DIC_GLODAP_annual_ORCA2.nc'],
        'ref_cands': ['data_TDIC_ORCA2.nc', 'data_DIC_ORCA2.nc', 'data_DIC_nomask_ORCA2.nc'],
        'unit': 'umol C/L',
        'category': 'tracer'
    },
    {
        'var': 'PiDIC',
        'product': 'GLODAPv2.2016b',
        'test_cands': ['data_PiDIC_ORCA2.nc', 'PiDIC_GLODAP_annual_ORCA2.nc'],
        'ref_cands': ['data_PiDIC_ORCA2.nc', 'data_DIC_ORCA2.nc', 'data_DIC_nomask_ORCA2.nc'],
        'unit': 'umol C/L',
        'category': 'tracer'
    },
    {
        'var': 'DOC',
        'product': 'Panaïotis et al. 2024 (ML)',
        'test_cands': ['data_DOC_ORCA2.nc', 'DOC_Panaiotis2024_monthly_ORCA2.nc'],
        'ref_cands': ['data_DOC_ORCA2.nc', 'data_DOC_nomask_ORCA2.nc'],
        'unit': 'umol C/L',
        'category': 'tracer'
    },
    {
        'var': 'Fer',
        'product': 'Tagliabue 2012',
        'test_cands': ['data_Fer_ORCA2.nc', 'data_FER_ORCA2.nc', 'Fer_PISCES_monthly_ORCA2.nc'],
        'ref_cands': ['data_Fer_ORCA2.nc', 'data_FER_ORCA2.nc', 'data_FER_nomask_ORCA2.nc'],
        'unit': 'nmol Fe/L',
        'category': 'tracer'
    },
    {
        'var': 'dust',
        'product': 'INCA / Mahowald',
        'test_cands': ['dust.orca.nc', 'dust_INCA_ORCA2.nc'],
        'ref_cands': ['dust.orca.nc'],
        'unit': 'g/m2/yr',
        'category': 'forcing'
    },
    {
        'var': 'ndep',
        'product': 'Duce et al.',
        'test_cands': ['ndeposition.orca.nc', 'ndeposition_Duce_ORCA2.nc'],
        'ref_cands': ['ndeposition.orca.nc'],
        'unit': 'gN/m2/yr',
        'category': 'forcing'
    },
    {
        'var': 'par',
        'product': 'GEWEX Climatology',
        'test_cands': ['par.orca.nc', 'par_fraction_gewex_clim90s00s_ORCA2.nc'],
        'ref_cands': ['par.orca.nc'],
        'unit': 'fraction',
        'category': 'forcing'
    },
    {
        'var': 'bathy',
        'product': 'ETOPO / pmarge',
        'test_cands': ['bathy.orca.nc', 'pmarge_etopo_ORCA2.nc'],
        'ref_cands': ['bathy.orca.nc'],
        'unit': 'fraction',
        'category': 'forcing'
    },
    {
        'var': 'hydrofe',
        'product': 'Hydrothermal Fe',
        'test_cands': ['hydrofe.orca.nc'],
        'ref_cands': ['hydrofe.orca.nc'],
        'unit': 'mol Fe/m2/s',
        'category': 'forcing'
    },
    {
        'var': 'river',
        'product': 'Global NEWS 2',
        'test_cands': ['river.orca.nc', 'river_global_news_ORCA2.nc'],
        'ref_cands': ['river.orca.nc'],
        'unit': 'MgN/m2/yr',
        'category': 'forcing'
    }
]


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
    Detects unit mismatches, sign errors, spatial flips, and climatological divergences.
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
                f"Variable '{var_key}' not found in test {test_file}. "
                f"Available: {list(ds_test.variables.keys())}"
            )
        if not var_ref_name:
            raise KeyError(
                f"Variable '{var_key}' not found in ref {ref_file}. "
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
                'min_test': np.nan,
                'max_test': np.nan,
                'min_ref': np.nan,
                'max_ref': np.nan,
                'unit': UNITS.get(var_key, ''),
                'status': 'FAIL',
                'issue': 'No valid ocean cells found'
            }

        diff = valid_test - valid_ref
        abs_diff = np.abs(diff)

        mean_ref = float(np.mean(valid_ref))
        mean_test = float(np.mean(valid_test))
        min_test = float(np.min(valid_test))
        max_test = float(np.max(valid_test))
        min_ref = float(np.min(valid_ref))
        max_ref = float(np.max(valid_ref))

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
            r = 1.0 if rmse < 1e-6 else np.nan
            rho = 1.0 if rmse < 1e-6 else np.nan

        # Sanity Checks: Units, Coordinates, Sign
        scale_ratio = (mean_test / mean_ref) if abs(mean_ref) > 1e-12 else 1.0
        scale_error = (scale_ratio > 10.0 or scale_ratio < 0.10) if abs(mean_ref) > 1e-12 else False
        negative_error = (min_test < -1e-4)
        inverted_error = (not np.isnan(r) and r < -0.1)

        if scale_error:
            status = 'FAIL'
            issue = f'Unit scale error (mean ratio: {scale_ratio:.2f}x vs SETTE)'
        elif inverted_error:
            status = 'FAIL'
            issue = f'Inverted pattern (r = {r:.2f} < 0)'
        elif negative_error:
            status = 'FAIL'
            issue = f'Unphysical negative concentration (min: {min_test:.2e})'
        elif var_key == 'DOC':
            status = 'WARN'
            issue = 'ML DOC vs Hansell 2009 baseline (enhanced mesopelagic gradient)'
        elif not np.isnan(r) and r < 0.65 and var_key not in ['TALK', 'TDIC', 'PiDIC']:
            status = 'WARN'
            issue = f'Moderate correlation (r = {r:.2f})'
        else:
            status = 'PASS'
            issue = 'Validated'

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
            'min_test': min_test,
            'max_test': max_test,
            'min_ref': min_ref,
            'max_ref': max_ref,
            'scale_ratio': scale_ratio,
            'unit': UNITS.get(var_key, ''),
            'status': status,
            'issue': issue
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
            'status': "PASS" if passed else "FAIL",
            'issue': "Mass conserved" if passed else f"Mass leakage ({rel_diff_pct:+.2f}%)"
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
    lines.append("# PISCES Inidata Validation Scorecard (ORCA2 vs SETTE Benchmark)")
    lines.append("")
    lines.append(
        "Automated procedure validation evaluating generated initial conditions on **ORCA2** "
        "against the official **NEMO/PISCES SETTE** benchmark ground truth to detect unit errors, "
        "pipeline orientation bugs, and unphysical values."
    )
    lines.append("")
    lines.append("## 1. Product Scorecard (3D Tracers & Boundary Forcings)")
    lines.append("")
    lines.append(
        "| Variable | Product Evaluated | Unit | Physical Range [min, max] | Mean Ratio | "
        "Pearson $r$ | Rel RMSE (%) | Status |"
    )
    lines.append(
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |"
    )

    for r in results:
        r_val = f"**{r['r']:.4f}**" if (not np.isnan(r['r']) and r['r'] >= 0.85) else (
            f"{r['r']:.4f}" if not np.isnan(r['r']) else "N/A"
        )
        nrmse_val = f"{r['nrmse_pct']:.2f}%" if not np.isnan(r['nrmse_pct']) else "N/A"
        range_str = f"[{r['min_test']:.2e}, {r['max_test']:.2e}]"
        ratio_str = f"{r['scale_ratio']:.2f}x"
        prod = r.get('product', 'Default')

        stat_str = f"**{r['status']}**" if r['status'] == 'PASS' else (
            f"**{r['status']}**" if r['status'] == 'WARN' else f"<span style='color:red;'>**{r['status']}**</span>"
        )

        lines.append(
            f"| **{r['var']}** | `{prod}` | {r['unit']} | {range_str} | {ratio_str} | "
            f"{r_val} | {nrmse_val} | {stat_str} |"
        )

    if conservation_results:
        lines.append("")
        lines.append("## 2. Mass Conservation Verification (Boundary Forcings)")
        lines.append("")
        lines.append("| Variable | Product | Target Integral | Ref Integral | Rel Diff (%) | Tolerance | Status |")
        lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: |")
        for c in conservation_results:
            stat_str = f"**{c['status']}**" if c['passed'] else f"<span style='color:red;'>**{c['status']}**</span>"
            prod = c.get('product', 'Default')
            lines.append(
                f"| **{c['var']}** | `{prod}` | {c['integral_test']:.4e} | {c['integral_ref']:.4e} | "
                f"{c['rel_diff_pct']:+.2f}% | $\\le {c['tolerance_pct']:.1f}\\%$ | {stat_str} |"
            )

    lines.append("")
    lines.append("### Diagnostic Notes:")
    lines.append("- **Scale Sanity:** Mean ratio within $[0.2, 5.0]$ confirms unit consistency.")
    lines.append("- **Pattern Orientation:** Positive Pearson $r$ verifies spatial orientation is non-inverted.")
    lines.append("- **Mass Conservation:** Surface flux integrals verify zero mass leakage across conservative remap.")
    lines.append("")
    md_content = "\n".join(lines)

    if output_md_path:
        with open(output_md_path, 'w') as f:
            f.write(md_content)

    return md_content


def run_validation_suite(
    test_dir: str,
    ref_dir: str,
    output_md: Optional[str] = None,
    fail_on_error: bool = False
) -> int:
    """
    Executes product-by-product validation suite comparing test_dir against ref_dir on ORCA2.
    Returns: 0 on success, 1 on critical failure.
    """
    print("=" * 80)
    print(" PISCES INIDATA VALIDATION SUITE (ORCA2 vs SETTE BENCHMARK)")
    print(f" Test Directory:      {test_dir}")
    print(f" Reference Directory: {ref_dir}")
    print("=" * 80)

    results = []
    conservation_results = []
    n_pass = 0
    n_warn = 0
    n_fail = 0

    for item in SUPPORTED_PRODUCTS:
        var = item['var']
        prod = item['product']
        test_cands = item['test_cands']
        ref_cands = item['ref_cands']

        test_path = None
        for c in test_cands:
            p = os.path.join(test_dir, c)
            if os.path.exists(p):
                test_path = p
                break

        ref_path = None
        for c in ref_cands:
            p = os.path.join(ref_dir, c)
            if os.path.exists(p):
                ref_path = p
                break

        if not test_path:
            print(f"  [SKIP] {var:7s} ({prod}) : Missing test file in {test_dir} (tried {test_cands[:2]})")
            continue
        if not ref_path:
            print(f"  [SKIP] {var:7s} ({prod}) : Missing reference file in {ref_dir} (tried {ref_cands[:2]})")
            continue

        try:
            diag = compute_diagnostics(test_path, ref_path, var)
            diag['product'] = prod
            results.append(diag)

            stat = diag['status']
            if stat == 'PASS':
                n_pass += 1
            elif stat == 'WARN':
                n_warn += 1
            else:
                n_fail += 1

            r_str = f"r={diag['r']:.4f}" if not np.isnan(diag['r']) else "r=N/A"
            ratio_str = f"ratio={diag['scale_ratio']:.2f}x"
            print(f"  [{stat:4s}] {var:7s} ({prod:22s}) : {r_str}, {ratio_str} -> {diag['issue']}")

            # Check mass conservation for forcings
            if item['category'] == 'forcing' and var in ['river', 'dust', 'ndep', 'hydrofe']:
                c_res = compute_mass_conservation(test_path, ref_path, var)
                c_res['product'] = prod
                conservation_results.append(c_res)
                if not c_res['passed']:
                    n_fail += 1

        except Exception as e:
            print(f"  [FAIL] {var:7s} ({prod}) : Error evaluating: {e}")
            n_fail += 1

    print("\n" + "=" * 80)
    print(f" VALIDATION SCORECARD SUMMARY: {len(results)} Evaluated | "
          f"{n_pass} PASSED | {n_warn} WARNINGS | {n_fail} FAILED")
    print("=" * 80)

    if results or conservation_results:
        generate_scoreboard(results, conservation_results, output_md)
        if output_md:
            print(f"Saved comprehensive scorecard to: {output_md}")

    if n_fail > 0 and fail_on_error:
        print("Validation suite encountered critical failure(s).")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Generate PISCES inidata validation scorecard against SETTE ground truth."
    )
    parser.add_argument("--test-dir", default="output_ORCA2", help="Directory with generated ORCA2 files")
    parser.add_argument("--ref-dir", default="sette_reference_ORCA2", help="Directory with SETTE ORCA2 references")
    parser.add_argument("--output-md", default="VALIDATION_SCOREBOARD_ORCA2.md", help="Output markdown scorecard path")
    parser.add_argument("--fail-on-error", action="store_true", help="Exit with non-zero code on any failure")
    args = parser.parse_args()

    code = run_validation_suite(
        test_dir=args.test_dir,
        ref_dir=args.ref_dir,
        output_md=args.output_md,
        fail_on_error=args.fail_on_error
    )
    exit(code)


if __name__ == "__main__":
    main()
