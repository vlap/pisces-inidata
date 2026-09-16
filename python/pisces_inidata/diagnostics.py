"""
Diagnostics and Tabular Formatting Utilities for PISCES Inidata.
Provides reusable array statistics (RMSE, MAE, MBE, Pearson r, min, max, mean)
and a GitHub Flavored Markdown table generator.
"""

from typing import Dict, List, Optional
import numpy as np


def compute_array_stats(
    test_vals: np.ndarray,
    ref_vals: np.ndarray
) -> Dict[str, float]:
    """
    Computes statistical verification metrics comparing test and reference arrays.

    Parameters:
        test_vals: 1D NumPy array of valid test values
        ref_vals: 1D NumPy array of corresponding valid reference values

    Returns:
        Dict containing rmse, mae, mbe, pearson_r, rel_rmse_pct, mean_test,
        mean_ref, min_test, max_test, min_ref, max_ref, max_diff, scale_ratio.
    """
    n = len(test_vals)
    if n == 0:
        return {
            'rmse': np.nan,
            'mae': np.nan,
            'mbe': np.nan,
            'pearson_r': np.nan,
            'rel_rmse_pct': np.nan,
            'mean_test': np.nan,
            'mean_ref': np.nan,
            'min_test': np.nan,
            'max_test': np.nan,
            'min_ref': np.nan,
            'max_ref': np.nan,
            'max_diff': np.nan,
            'scale_ratio': np.nan,
        }

    diff = test_vals - ref_vals
    abs_diff = np.abs(diff)

    mean_ref = float(np.mean(ref_vals))
    mean_test = float(np.mean(test_vals))
    min_test = float(np.min(test_vals))
    max_test = float(np.max(test_vals))
    min_ref = float(np.min(ref_vals))
    max_ref = float(np.max(ref_vals))

    rmse = float(np.sqrt(np.mean(diff ** 2)))
    mae = float(np.mean(abs_diff))
    mbe = float(np.mean(diff))
    max_diff = float(np.max(abs_diff))

    rel_rmse_pct = (rmse / abs(mean_ref) * 100.0) if abs(mean_ref) > 1e-12 else np.nan
    scale_ratio = (mean_test / mean_ref) if abs(mean_ref) > 1e-12 else 1.0

    std_test = float(np.std(test_vals))
    std_ref = float(np.std(ref_vals))
    if std_test > 1e-12 and std_ref > 1e-12:
        r = float(np.corrcoef(test_vals, ref_vals)[0, 1])
        r = float(np.clip(r, -1.0, 1.0))
    else:
        r = 1.0 if rmse < 1e-6 else np.nan

    return {
        'rmse': rmse,
        'mae': mae,
        'mbe': mbe,
        'pearson_r': r,
        'rel_rmse_pct': rel_rmse_pct,
        'mean_test': mean_test,
        'mean_ref': mean_ref,
        'min_test': min_test,
        'max_test': max_test,
        'min_ref': min_ref,
        'max_ref': max_ref,
        'max_diff': max_diff,
        'scale_ratio': scale_ratio,
    }


def format_markdown_table(
    headers: List[str],
    rows: List[List[str]],
    alignments: Optional[List[str]] = None
) -> str:
    """
    Renders a GitHub Flavored Markdown table.

    Parameters:
        headers: List of column header titles
        rows: List of row data, where each row is a list of strings
        alignments: Optional list of alignments ('left', 'center', 'right').
                    Defaults to 'left' for the first two columns, 'center' thereafter.

    Returns:
        Formatted Markdown table string.
    """
    ncols = len(headers)
    if alignments is None:
        alignments = ['left' if i < 2 else 'center' for i in range(ncols)]

    align_map = {
        'left': ':---',
        'center': ':---:',
        'right': '---:',
    }
    separators = [align_map.get(a.lower(), ':---') for a in alignments]

    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join(separators) + " |"
    row_lines = ["| " + " | ".join(r) + " |" for r in rows]

    return "\n".join([header_line, sep_line] + row_lines)
