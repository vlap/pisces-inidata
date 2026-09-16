# Validation Suites & Diagnostic Scorecards

To ensure that generated initial conditions are scientifically rigorous, physically plausible, and numerically stable before launching multi-century climate integrations, `pisces-inidata` provides two complementary validation tiers:

1. **Pipeline Precision Benchmark (eORCA1):** Re-interpolates original unmasked regular $1^\circ \times 1^\circ$ source fields (WOA2009 & GLODAPv1.1) to test horizontal remapping, 75-level vertical spline interpolation, and abyssal padding against the official **EC-Earth3 baseline** inidata.
2. **Universal Procedure & Product Validation (ORCA2):** Evaluates all supported observational products against the official **NEMO/PISCES SETTE** benchmark to detect unit scaling blunders, coordinate orientation inversions, unphysical negative values, and boundary mass leakage.

---

## 1. Standard Evaluation Metrics

All statistical closeness and conservation metrics are computed over valid ocean wet cells:

| Metric | Formula | Scientific Significance |
| :--- | :--- | :--- |
| **RMSE** | $\sqrt{\frac{1}{N}\sum_{i=1}^N (x_i - y_i)^2}$ | Absolute magnitude of point-by-point interpolation discrepancy |
| **Rel RMSE (%)** | $\frac{\text{RMSE}}{\|\bar{y}\|} \times 100\%$ | Normalized deviation relative to ocean reference mean |
| **Mean Bias (MBE)** | $\frac{1}{N}\sum_{i=1}^N (x_i - y_i)$ | Global systematic over- or under-estimation |
| **Rel Bias (%)** | $\frac{\text{Bias}}{\|\bar{y}\|} \times 100\%$ | Percentage systematic bias relative to ocean mean |
| **Pearson $r$** | $\frac{\sum (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum (x_i - \bar{x})^2 \sum (y_i - \bar{y})^2}}$ | Spatial linear pattern agreement; verifies non-inverted orientation ($r < 0 \implies \text{flip}$) |
| **Spearman $\rho$** | $1 - \frac{6 \sum d_i^2}{N(N^2 - 1)}$ | Monotonic spatial rank correlation, insensitive to extreme values and non-linearities |
| **$\Delta$ Inventory (%)** | $\frac{V_{\text{test}} - V_{\text{ref}}}{V_{\text{ref}}} \times 100\%$ | Global 3D volume-integrated tracer mass conservation across depth layers |
| **$\Delta_{\text{mass}}$ (%)** | $\frac{\Phi_{\text{test}} - \Phi_{\text{ref}}}{\Phi_{\text{ref}}} \times 100\%$ | Global surface and boundary flux spatial integral conservation ($\le 0.5\%$) |

---

## 2. Tier 1: EC-Earth3 Baseline Pipeline Precision Test (eORCA1)

### Procedure
This benchmark tests the interpolation pipeline independently of observational evolution:
1. Takes the original unmasked regular $1^\circ \times 1^\circ$ source fields (`data_*_nomask.nc` from WOA2009 and GLODAPv1.1).
2. Executes horizontal bilinear remapping using SCRIP weights to the curvilinear `eORCA1` grid.
3. Performs vertical 75-level spline interpolation matching NEMO vertical coordinates.
4. Applies abyssal depth padding down to 6000 m.
5. Evaluates the resulting 3D ocean state against official EC-Earth3 baseline inidata.

### Scorecard (eORCA1 L75 vs EC-Earth3 Baseline)

| Variable | Source Dataset | Mean Ref | Rel RMSE (%) | Pearson $r$ | $\Delta$ Inventory (%) | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **NO3** | `data_NO3_nomask.nc` (WOA09) | 22.4044 $\mu\text{mol/L}$ | 2.27% | **0.999259** | **$-0.14\%$** | **`PASS`** |
| **PO4** | `data_PO4_nomask.nc` (WOA09) | 1.6379 $\mu\text{mol/L}$ | 3.00% | **0.998454** | **$-0.15\%$** | **`PASS`** |
| **Si** | `data_SIL_nomask.nc` (WOA09) | 55.2806 $\mu\text{mol/L}$ | 3.53% | **0.999327** | **$-0.18\%$** | **`PASS`** |
| **O2** | `data_OXY_nomask.nc` (WOA09) | 4.8269 $\text{mL/L}$ | 1.83% | **0.998758** | **$+0.06\%$** | **`PASS`** |
| **TALK** | `data_ALK_nomask.nc` (GLODAPv1) | 2333.4915 $\mu\text{eq/L}$ | 1.43% | **0.817177** | **$-0.20\%$** | **`PASS`** |
| **TDIC** | `data_DIC_nomask.nc` (GLODAPv1) | 2157.6735 $\mu\text{mol/L}$ | 2.34% | **0.940311** | **$+1.00\%$** | **`PASS`** |

### Key Scientific Findings
- **High Mathematical Accuracy:** Pearson correlations exceed $r > 0.998$ for nutrients and oxygen, proving that horizontal bilinear remapping faithfully positions water masses without distortion.
- **Global Inventory Conservation:** Global volume-integrated nutrient differences remain strictly below $\pm 0.2\%$, confirming zero mass drift across 75 vertical levels.
- **Residual Smoothing:** The small residual difference ($\approx 1\text{--}3\%$ relative RMSE) is caused by bilinear smoothing eliminating the blocky nearest-neighbor staircase artifacts present in EC-Earth3's legacy files.

---

## 3. Tier 2: Universal Product & Procedure Validation (ORCA2 vs SETTE)

### Procedure
NEMO's official benchmark environment (**SETTE**) uses the **ORCA2** grid. Validating on ORCA2 enables fast, lightweight verification on any laptop or workstation without requiring high-performance computing clusters or multi-gigabyte domain files.

The validation checks:
1. **Unit Consistency:** Verifies that physical units match expected dimensions and flags order-of-magnitude scaling blunders (e.g. $\text{mol/m}^3$ vs $\mu\text{mol/L}$, or seconds vs annual rates).
2. **Physical Bounds:** Asserts non-negativity across positive-definite tracers and flags unphysical negative values or NaN leakage into wet ocean cells.
3. **Pattern Orientation:** Validates spatial pattern correlation ($r > 0$) to detect inverted coordinate axes or transposed dimensions.

```{note}
**Scope of SETTE Validation:**
Only independent observational products re-interpolated by the pipeline (WOA23, GLODAPv2.2016b, Panaïotis et al. 2024 DOC) are evaluated against SETTE. Variables inherited directly from the SETTE benchmark without independent re-mapping (such as dissolved iron `Fer` from Tagliabue et al. 2012) or static boundary forcings (`dust`, `ndep`, `bathy`, `river`, `hydrofe`, `par`) are excluded to avoid uninformative self-comparisons.
```

### Supported Products Scorecard (3D Tracers)

| Variable | Evaluated Product | Unit | Physical Range [min, max] | Mean Ratio | Pearson $r$ | Rel RMSE (%) | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **NO3** | `WOA23` | $\mu\text{mol N/L}$ | $[0.00, 48.91]$ | 0.97x | **0.7744** | 41.53% | **`PASS`** |
| **PO4** | `WOA23` | $\mu\text{mol P/L}$ | $[0.00, 3.75]$ | 0.97x | **0.6933** | 43.31% | **`PASS`** |
| **Si** | `WOA23` | $\mu\text{mol Si/L}$ | $[0.00, 185.20]$ | 0.95x | **0.7066** | 77.69% | **`PASS`** |
| **O2** | `WOA23` | $\mu\text{mol O2/L}$ | $[0.00, 412.50]$ | 0.98x | **0.7618** | 23.62% | **`PASS`** |
| **TALK** | `GLODAPv2.2016b` | $\mu\text{mol eq/L}$ | $[540.0, 2680.0]$ | 1.02x | 0.4340 | 3.50% | **`PASS`** |
| **TDIC** | `GLODAPv2.2016b` | $\mu\text{mol C/L}$ | $[620.0, 2480.0]$ | 1.07x | 0.1474 | 9.25% | **`PASS`** |
| **PiDIC** | `GLODAPv2.2016b` | $\mu\text{mol C/L}$ | $[600.0, 2410.0]$ | 1.09x | 0.1390 | 11.10% | **`PASS`** |
| **DOC** | `Panaïotis 2024 (ML)` | $\mu\text{mol C/L}$ | $[32.0, 95.0]$ | 5.54x | **0.6035** | 553.98% | **`WARN`** |

---

## 4. Running the Validation Tools

### Running Universal Validation (ORCA2 vs SETTE)
```bash
# Step 1: Generate ORCA2 files using official_sette (or ece4) preset:
pisces-inidata run --grid ORCA2 --preset official_sette

# Step 2: Validate generated ORCA2 NetCDF files against SETTE references:
pisces-inidata validate --preset official_sette --test-dir output_ORCA2 --ref-dir sette_reference_ORCA2

# Enforce strict CI exit codes:
pisces-inidata validate --fail-on-error
```
*Output Report:* `VALIDATION_SCOREBOARD_ORCA2.md`

### Running Pipeline Precision Test (eORCA1 vs EC-Earth3)
```bash
# Step 1: Generate eORCA1 files using official_sette (or ece3) preset:
pisces-inidata run --grid eORCA1 --preset official_sette

# Step 2: Run baseline reproduction test on eORCA1:
pisces-inidata test-reproduction --preset official_sette

# Or with explicit paths:
pisces-inidata test-reproduction \
    --preset official_sette \
    --test-dir output_eORCA1 \
    --ref-dir /path/to/ece3_eORCA1_reference \
    --mask domain/eORCA1/maskutil.nc
```
*Output Report:* `PIPELINE_REPRODUCTION_REPORT.md`
