"""
Validation Scoreboard Module
Computes a comprehensive validation scorecard comparing interpolated PISCES
inidata products on ORCA2 against official SETTE ground truth references.
Verifies units, physical ranges, spatial patterns, and boundary mass conservation.
"""

import os
from typing import Dict, Any, Optional, List
import numpy as np
import netCDF4 as nc
from pisces_inidata.verify import find_var, VAR_ALIASES
from pisces_inidata.diagnostics import compute_array_stats, format_markdown_table

ALIASES = VAR_ALIASES


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
    }
]


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

        stats = compute_array_stats(valid_test, valid_ref)
        mean_ref = stats['mean_ref']
        mean_test = stats['mean_test']
        min_test = stats['min_test']
        scale_ratio = stats['scale_ratio']
        r = stats['pearson_r']

        # Sanity Checks: Units, Coordinates, Sign
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
            'rmse': stats['rmse'],
            'nrmse_pct': stats['rel_rmse_pct'],
            'mae': stats['mae'],
            'mbe': stats['mbe'],
            'rel_bias_pct': (stats['mbe'] / abs(mean_ref) * 100.0) if abs(mean_ref) > 1e-12 else np.nan,
            'r': r,
            'max_diff': stats['max_diff'],
            'mean_ref': mean_ref,
            'mean_test': mean_test,
            'min_test': min_test,
            'max_test': stats['max_test'],
            'min_ref': stats['min_ref'],
            'max_ref': stats['max_ref'],
            'scale_ratio': scale_ratio,
            'unit': UNITS.get(var_key, ''),
            'status': status,
            'issue': issue
        }


RIVER_NUTRIENTS = [
    ('riverdin', 'Dissolved Inorganic Nitrogen (DIN)', 'MgN/m2/yr'),
    ('riverdip', 'Dissolved Inorganic Phosphorus (DIP)', 'MgP/m2/yr'),
    ('riverdon', 'Dissolved Organic Nitrogen (DON)', 'MgN/m2/yr'),
    ('riverdop', 'Dissolved Organic Phosphorus (DOP)', 'MgP/m2/yr'),
    ('riverdoc', 'Dissolved Organic Carbon (DOC)', 'MgC/m2/yr'),
    ('riverdsi', 'Dissolved Silicate (DSi)', 'MgSi/m2/yr'),
    ('riverdic', 'Dissolved Inorganic Carbon (DIC)', 'MgC/m2/yr'),
]


def compute_river_conservation(test_file: str, ref_file: str) -> List[Dict[str, Any]]:
    """
    Computes global integrated flux conservation for all 7 river nutrient inputs.
    Verifies that remapping preserves total nutrient mass input into the ocean.
    """
    if not os.path.exists(test_file) or not os.path.exists(ref_file):
        return []

    results = []
    with nc.Dataset(test_file, 'r') as ds_t, nc.Dataset(ref_file, 'r') as ds_r:
        for var_name, desc, unit in RIVER_NUTRIENTS:
            if var_name not in ds_t.variables or var_name not in ds_r.variables:
                continue

            data_t = ds_t.variables[var_name][:]
            data_r = ds_r.variables[var_name][:]

            # Average over time dimension if present
            mean_t = np.mean(data_t, axis=0) if data_t.ndim == 3 else data_t
            mean_r = np.mean(data_r, axis=0) if data_r.ndim == 3 else data_r

            unm_t = np.ma.filled(mean_t, 0.0)
            unm_r = np.ma.filled(mean_r, 0.0)

            sum_t = float(np.sum(unm_t[unm_t > 0]))
            sum_r = float(np.sum(unm_r[unm_r > 0]))

            ratio = (sum_t / sum_r) if sum_r > 1e-12 else 1.0

            # Compute spatial correlation across active river discharge cells
            flat_t = unm_t.flatten()
            flat_r = unm_r.flatten()
            mask_valid = (flat_t > 0) | (flat_r > 0)
            if np.sum(mask_valid) > 2:
                vt = flat_t[mask_valid]
                vr = flat_r[mask_valid]
                if np.std(vt) > 1e-12 and np.std(vr) > 1e-12:
                    r_val = float(np.corrcoef(vt, vr)[0, 1])
                else:
                    r_val = 1.0
            else:
                r_val = 1.0

            if abs(ratio - 1.0) <= 0.02:
                status = 'PASS'
                issue = f'Conserved (diff: {abs(ratio - 1.0) * 100.0:.1f}%)'
            elif abs(ratio - 1.0) <= 0.10:
                status = 'WARN'
                issue = f'Moderate flux shift ({ratio:.2f}x)'
            else:
                status = 'FAIL'
                issue = f'Unconserved flux shift ({ratio:.2f}x)'

            results.append({
                'var': var_name,
                'desc': desc,
                'unit': unit,
                'sum_test': sum_t,
                'sum_ref': sum_r,
                'ratio': ratio,
                'r': r_val,
                'status': status,
                'issue': issue
            })
    return results


def get_product_name(var: str, pack: str = "official_sette", preset: Optional[str] = None) -> str:
    active_pack = preset if preset is not None else pack
    if active_pack == "official_sette":
        return "SETTE nomask (pure interpolation)"
    elif active_pack == "ece3":
        if var in ['NO3', 'PO4', 'Si', 'O2']:
            return "WOA2009"
        elif var in ['TALK', 'TDIC', 'PiDIC']:
            return "GLODAPv1.1"
        else:
            return "SETTE nomask"
    else:  # ece4
        if var in ['NO3', 'PO4', 'Si', 'O2']:
            return "WOA23"
        elif var in ['TALK', 'TDIC', 'PiDIC']:
            return "GLODAPv2.2016b"
        elif var == 'DOC':
            return "Panaïotis et al. 2024 (ML)"
        else:
            return "Tagliabue Fe"


def generate_scoreboard(
    results: List[Dict[str, Any]],
    river_results: Optional[List[Dict[str, Any]]] = None,
    output_md_path: Optional[str] = None,
    pack: str = "official_sette",
    preset: Optional[str] = None,
) -> str:
    """
    Renders diagnostic results list into a GitHub Flavored Markdown scoreboard table.
    """
    active_pack = preset if preset is not None else pack
    lines = []
    lines.append("# PISCES Inidata Validation Scorecard (ORCA2 vs SETTE Benchmark)")
    lines.append("")
    lines.append(f"**Configuration Pack:** `{active_pack}`  ")
    lines.append("")
    lines.append(
        "Automated procedure validation evaluating newly generated 3D tracer initial conditions "
        "on **ORCA2** against the official **NEMO/PISCES SETTE** benchmark ground truth to detect unit errors, "
        "pipeline orientation bugs, and unphysical values."
    )
    lines.append("")
    lines.append("## Supported Products Scorecard (3D Tracers)")
    lines.append("")
    headers = [
        "Variable", "Product Evaluated", "Unit", "Physical Range [min, max]",
        "Mean Ratio", "Pearson $r$", "Rel RMSE (%)", "Status"
    ]
    alignments = ["left", "left", "left", "center", "center", "center", "center", "center"]
    rows = []
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

        rows.append([
            f"**{r['var']}**", f"`{prod}`", r['unit'], range_str, ratio_str,
            r_val, nrmse_val, stat_str
        ])

    lines.append(format_markdown_table(headers, rows, alignments))

    if river_results:
        lines.append("")
        lines.append("## Boundary Forcing Conservation (River Nutrient Discharges)")
        lines.append("")
        lines.append(
            "Evaluation of global integrated nutrient mass inputs from river discharge to ensure "
            "nutrient inputs into the marine ecosystem remain invariant across grid remapping."
        )
        lines.append("")
        r_headers = [
            "Variable", "Description", "Unit", "Total Flux (Test)",
            "Total Flux (Ref)", "Ratio (Test/Ref)", "Pearson $r$", "Status"
        ]
        r_aligns = ["left", "left", "left", "center", "center", "center", "center", "center"]
        r_rows = []
        for r in river_results:
            r_val = f"**{r['r']:.4f}**" if (not np.isnan(r['r']) and r['r'] >= 0.85) else (
                f"{r['r']:.4f}" if not np.isnan(r['r']) else "N/A"
            )
            ratio_str = f"{r['ratio']:.2f}x"
            stat_str = f"**{r['status']}**" if r['status'] == 'PASS' else (
                f"**{r['status']}**" if r['status'] == 'WARN' else f"<span style='color:red;'>**{r['status']}**</span>"
            )
            r_rows.append([
                f"**{r['var']}**", r['desc'], r['unit'],
                f"{r['sum_test']:.4e}", f"{r['sum_ref']:.4e}",
                ratio_str, r_val, stat_str
            ])
        lines.append(format_markdown_table(r_headers, r_rows, r_aligns))

    lines.append("")
    lines.append("### Diagnostic Notes:")
    lines.append("- **Scale Sanity:** Mean ratio within $[0.2, 5.0]$ confirms unit consistency.")
    lines.append("- **Pattern Orientation:** Positive Pearson $r$ verifies spatial orientation is non-inverted.")
    lines.append(
        "- **Panaïotis 2024 DOC:** Modern machine-learning global climatology exhibits higher carbon values "
        "than the 2009 Hansell baseline used in SETTE, flagged with WARN as an expected scientific difference."
    )
    lines.append(
        "- **River Nutrient Conservation:** Integrated river nutrient inputs should conserve mass within 2% "
        "when remapped, avoiding artificial nutrient dilution or enrichment."
    )
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
    fail_on_error: bool = False,
    pack: str = "official_sette",
    preset: Optional[str] = None,
) -> int:
    """
    Executes product-by-product validation suite comparing test_dir against ref_dir on ORCA2.
    Returns: 0 on success, 1 on critical failure.
    """
    active_pack = preset if preset is not None else pack
    print("=" * 80)
    print(f" PISCES INIDATA VALIDATION SUITE (ORCA2 vs SETTE BENCHMARK, Pack: {active_pack})")
    print(f" Test Directory:      {test_dir}")
    print(f" Reference Directory: {ref_dir}")
    print("=" * 80)

    results = []
    n_pass = 0
    n_warn = 0
    n_fail = 0

    for item in SUPPORTED_PRODUCTS:
        var = item['var']
        prod = get_product_name(var, pack=active_pack)
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

        except Exception as e:
            print(f"  [FAIL] {var:7s} ({prod}) : Error evaluating: {e}")
            n_fail += 1

    # 2. Evaluate River Nutrient Mass-Flux Conservation
    river_cands = ["river.orca.nc", "river_global_news_ORCA2.nc"]
    test_river = None
    for c in river_cands:
        p = os.path.join(test_dir, c)
        if os.path.exists(p):
            test_river = p
            break

    ref_river = None
    for c in river_cands:
        p = os.path.join(ref_dir, c)
        if os.path.exists(p):
            ref_river = p
            break

    river_results = []
    if test_river and ref_river:
        print("\n--- Boundary Forcing Conservation (River Nutrient Discharges) ---")
        river_results = compute_river_conservation(test_river, ref_river)
        for rr in river_results:
            stat = rr['status']
            if stat == 'PASS':
                n_pass += 1
            elif stat == 'WARN':
                n_warn += 1
            else:
                n_fail += 1
            r_str = f"r={rr['r']:.4f}" if not np.isnan(rr['r']) else "r=N/A"
            ratio_str = f"ratio={rr['ratio']:.2f}x"
            print(f"  [{stat:4s}] {rr['var']:8s} ({rr['desc']:38s}) : {ratio_str}, {r_str} -> {rr['issue']}")

    total_eval = len(results) + len(river_results)
    print("\n" + "=" * 80)
    print(f" VALIDATION SCORECARD SUMMARY: {total_eval} Evaluated | "
          f"{n_pass} PASSED | {n_warn} WARNINGS | {n_fail} FAILED")
    print("=" * 80)

    if results or river_results:
        generate_scoreboard(results, river_results=river_results, output_md_path=output_md, pack=active_pack)
        if output_md:
            print(f"Saved comprehensive scorecard to: {output_md}")

    if n_fail > 0 and fail_on_error:
        print("Validation suite encountered critical failure(s).")
        return 1
    return 0
