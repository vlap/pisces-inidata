# Validation Metrics & Diagnostic Scoreboard

To ensure that generated initial conditions are scientifically rigorous, physically plausible, and numerically stable before launching long-term climate integrations, `pisces-inidata` features an automated validation suite.

The tool compares interpolated fields against the official **NEMO/PISCES SETTE** benchmark suite on the ORCA2 grid.

---

## 1. Mathematical Definitions

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
Quantifies spatial linear agreement:
$$r = \frac{\sum_{i=1}^N (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum_{i=1}^N (x_i - \bar{x})^2 \sum_{i=1}^N (y_i - \bar{y})^2}}$$

### Spearman Rank Correlation ($\rho$)
Assesses monotonic spatial relationships, insensitive to non-linearities and extreme values:
$$\rho = 1 - \frac{6 \sum_{i=1}^N d_i^2}{N(N^2 - 1)}$$
where $d_i = \text{rank}(x_i) - \text{rank}(y_i)$.

---

## 2. Running the Validation Suite

Execute the validation script:
```bash
pisces-inidata validate
# or:
# bash scripts/run_validation_suite.sh
```

The output markdown table is written to `VALIDATION_SCOREBOARD_ORCA2.md`.

---

## 3. Interpreting Scoreboard Results

- **Near-Zero Errors ($r > 0.999$, $\text{NRMSE} < 0.1\%$):** Indicates numerical identity (e.g. boundary forcings or identical source data).
- **Physical Climatology Evolution ($r \approx 0.96 - 0.98$, $\text{NRMSE} \approx 6 - 8\%$):** Observed when comparing WOA23 against WOA2009. Reflects actual oceanographic improvements and decadal changes (e.g. deoxygenation, adjusted nutrient stoichiometry).
- **High Discrepancy ($r < 0.50$):** Signals an architectural divergence in raw source data, such as comparing modern machine-learning DOC (Panaïotis et al. 2024) against legacy Hansell (2009) estimates.
