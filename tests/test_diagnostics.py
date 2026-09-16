"""
Unit tests for pisces_inidata.diagnostics module.
"""

import numpy as np
from pisces_inidata.diagnostics import compute_array_stats, format_markdown_table


def test_compute_array_stats_basic():
    ref = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float64)
    test = np.array([12.0, 22.0, 32.0, 42.0], dtype=np.float64)

    stats = compute_array_stats(test, ref)
    assert np.isclose(stats['rmse'], 2.0)
    assert np.isclose(stats['mae'], 2.0)
    assert np.isclose(stats['mbe'], 2.0)
    assert np.isclose(stats['pearson_r'], 1.0)
    assert np.isclose(stats['mean_ref'], 25.0)
    assert np.isclose(stats['mean_test'], 27.0)
    assert np.isclose(stats['rel_rmse_pct'], (2.0 / 25.0) * 100.0)
    assert np.isclose(stats['scale_ratio'], 27.0 / 25.0)


def test_compute_array_stats_empty():
    empty = np.array([], dtype=np.float64)
    stats = compute_array_stats(empty, empty)
    assert np.isnan(stats['rmse'])
    assert np.isnan(stats['pearson_r'])


def test_format_markdown_table():
    headers = ["Col 1", "Col 2", "Col 3"]
    rows = [
        ["A", "B", "C"],
        ["D", "E", "F"]
    ]
    table = format_markdown_table(headers, rows)
    assert "| Col 1 | Col 2 | Col 3 |" in table
    assert "| :--- | :--- | :---: |" in table
    assert "| A | B | C |" in table
    assert "| D | E | F |" in table
