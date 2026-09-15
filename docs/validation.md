# Validation Metrics & Diagnostic Scoreboard

To ensure that generated initial conditions are scientifically rigorous, physically plausible, and numerically stable before launching multi-century climate integrations, `pisces-inidata` features an automated procedure validation engine.

---

## 1. Rationale: Why Validate on ORCA2 against SETTE?

1. **Procedure Verification Over Bitwise Identity:**
   Different observational products (e.g. WOA23 vs WOA2009, or machine-learning Panaïotis 2024 DOC vs legacy Hansell 2009) have genuine oceanographic differences. The primary goal of validation is to verify the **integrity of the interpolation procedure** and catch **major defects**:
   - **Unit Scaling Blunders:** Catches order-of-magnitude mistakes (e.g., $\times 1000$ or $\times 10^6$, $\text{mol/m}^3$ vs $\mu\text{mol/L}$, or annual vs per-second rates).
   - **Coordinate & Orientation Flips:** Detects inverted latitudes, shifted longitudes, or transposed dimensions ($r < 0$).
   - **Unphysical Values:** Detects negative concentrations in positive-definite biogeochemical tracers or NaN leakage into wet ocean cells.
   - **Mass Non-Conservation:** Verifies that horizontal remapping preserves global integrated nutrient and dust flux totals ($\Delta_{\text{mass}} \le 0.5\%$).

2. **Lightweight & Universal Portability:**
   NEMO's standard test environment (**SETTE**) uses the **ORCA2** tripolar grid. Because ORCA2 is compact and computationally lightweight, anyone can run the complete validation suite in seconds on a standard laptop or workstation without requiring high-performance computing clusters, multi-gigabyte domain files, or proprietary storage paths.

---

## 2. Mathematical Definitions

Let $x_i$ denote the test field value, $y_i$ denote the reference field value, and $N$ denote the total number of valid (unmasked ocean) grid cells across the 3D domain.

### Root Mean Square Error (RMSE)
Measures the overall magnitude of the point-by-point discrepancy:
$$\text{RMSE} = \sqrt{\frac{1}{N}\sum_{i=1}^N (x_i - y_i)^2}$$

### Normalized RMSE (NRMSE)
Expresses RMSE as a percentage of the reference field mean $\bar{y}$:
$$\text{NRMSE} = \frac{\text{RMSE}}{|\bar{y}|} \times 100\%$$

### Mean Bias Error (MBE / Bias)
Identifies systematic global over- or under-estimation:
$$\text{Bias} = \frac{1}{N}\sum_{i=1}^N (x_i - y_i)$$
$$\text{Relative Bias} = \frac{\text{Bias}}{|\bar{y}|} \times 100\%$$

### Pearson Correlation Coefficient ($r$)
Quantifies spatial linear agreement and verifies correct orientation:
$$r = \frac{\sum_{i=1}^N (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum_{i=1}^N (x_i - \bar{x})^2 \sum_{i=1}^N (y_i - \bar{y})^2}}$$

### Spearman Rank Correlation ($\rho$)
Assesses monotonic spatial relationships, insensitive to non-linearities and extreme values:
$$\rho = 1 - \frac{6 \sum_{i=1}^N d_i^2}{N(N^2 - 1)}$$
where $d_i = \text{rank}(x_i) - \text{rank}(y_i)$.

### Mass Conservation Verification (Boundary Forcings)
For surface and lateral boundary fluxes (river DIN/DIC/DIP, atmospheric dust, and soluble iron deposition), total global mass input into the ocean must be conserved during conservative spatial remapping:
$$\Phi = \sum_{i \in \text{Ocean}} F_i \cdot A_i$$
where $F_i$ is the local areal flux rate (e.g. $\text{g}\cdot\text{m}^{-2}\cdot\text{yr}^{-1}$) and $A_i$ is the target grid cell horizontal area ($\text{m}^2$). The relative mass divergence must satisfy:
$$\Delta_{\text{mass}} = \frac{|\Phi_{\text{target}} - \Phi_{\text{ref}}|}{\Phi_{\text{ref}}} \times 100\% \le \epsilon_{\text{tol}} \quad (\text{default: } 0.5\%)$$

---

## 3. Product Scorecard & Health Status

Every evaluated product receives a diagnostic scorecard entry with an automated health verdict:

| Status | Condition | Meaning |
| :--- | :--- | :--- |
| **`PASS`** | Mean ratio in $[0.2, 5.0]$, $r \ge 0.65$, non-negative, mass conserved | Procedure and product verified; physically sound. |
| **`WARN`** | Expected climatological shift (e.g. ML DOC vs Hansell baseline) | Oceanographic evolution noted; not a pipeline defect. |
| **`FAIL`** | Scale error ($> 10\times$ or $< 0.1\times$), $r < 0$, negative values, or mass leakage | Critical defect: inspect units, coordinates, or remapping weights. |

---

## 4. Running the Validation Suite

Execute validation using the CLI:
```bash
# Validate generated ORCA2 outputs against SETTE references
pisces-inidata validate --test-dir output_ORCA2 --ref-dir sette_reference_ORCA2

# Optionally enforce strict failure exit code for automated CI:
pisces-inidata validate --fail-on-error
```

Alternatively, invoke the driver script:
```bash
bash scripts/run_validation_suite.sh
```

The output markdown table is written to `VALIDATION_SCOREBOARD_ORCA2.md`.

---

## 5. Pipeline Precision Benchmark: EC-Earth3 Baseline Reproduction

To verify the mathematical accuracy and mass conservation of the interpolation pipeline independently of modern product differences, a dedicated reproduction benchmark is provided:

```bash
pisces-inidata test-reproduction --test-dir /path/to/reinterpolated_eORCA1 --ref-dir /path/to/ece3_eORCA1_reference
# or:
# bash scripts/test_pipeline_reproduction.sh
```

### Benchmark Criteria
This test takes original unmasked regular $1^\circ \times 1^\circ$ source fields (`data_*_nomask.nc` from WOA2009 and GLODAPv1.1) and re-interpolates them through the pipeline onto `eORCA1` 75-level grid. It asserts:
- **Spatial Pearson Correlation ($r$):** $\ge 0.998$ for nutrients and oxygen, proving that horizontal bilinear remapping faithfully positions water masses.
- **Global Inventory Difference ($|\Delta\text{Inv}|$):** $\le 0.2\%$, verifying that vertical spline interpolation and abyssal padding conserve global ocean mass.
- **Residual Smoothing:** Relative RMSE $< 3.5\%$, confirming that differences are solely due to bilinear smoothing eliminating nearest-neighbor staircase artifacts.
