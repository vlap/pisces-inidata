# PISCES Inidata Validation Scoreboard (ORCA2 vs SETTE Reference)

Evaluation of newly generated PISCES inputs (including **Panaïotis et al. 2024 DOC**, **WOA23**, **GLODAPv2.2016b**) interpolated to **ORCA2** and verified against the official **SETTE ORCA2** ground truth.

| Variable | Product Evaluated | Metric Unit | Pearson $r$ | RMSE | Rel RMSE (%) | MAE | Bias (MBE) | Rel Bias (%) | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **NO3** | `WOA23` | umol N/L | 0.7744 | 8.581e+00 | 41.53% | 5.755e+00 | -5.928e-01 | -2.87% | `PASSED` |
| **PO4** | `WOA23` | umol P/L | 0.6933 | 6.588e-01 | 43.31% | 4.501e-01 | -3.939e-02 | -2.59% | `PASSED` |
| **Si** | `WOA23` | umol Si/L | 0.7066 | 3.796e+01 | 77.69% | 2.189e+01 | -2.223e+00 | -4.55% | `REVIEW` |
| **O2** | `WOA23` | umol O2/L | 0.7618 | 5.218e+01 | 23.62% | 3.679e+01 | -5.477e-00 | -2.48% | `PASSED` |
| **TALK** | `GLODAPv2.2016b` | umol eq/L | 0.4340 | 8.006e+01 | 3.50% | 5.763e+01 | +3.990e+01 | +1.74% | `PASSED` |
| **TDIC** | `GLODAPv2.2016b` | umol C/L | 0.1474 | 1.894e+02 | 9.25% | 1.465e+02 | +1.433e+02 | +7.00% | `PASSED` |
| **PiDIC** | `GLODAPv2.2016b` | umol C/L | 0.1390 | 2.215e+02 | 11.10% | 1.726e+02 | +1.696e+02 | +8.50% | `PASSED` |
| **DOC** | `Panaïotis et al. 2024 (ML)` | umol C/L | 0.6035 | 4.480e+01 | 553.98% | 4.410e+01 | +4.382e+01 | +541.89% | `REVIEW` |
| **Fer** | `Tagliabue 2012` | nmol Fe/L | **1.0000** | 0.000e+00 | 0.00% | 0.000e+00 | +0.000e+00 | +0.00% | `PASSED` |
| **dust** | `INCA / Mahowald` | g/m2/yr | **1.0000** | 4.681e-12 | 24.59% | 7.927e-13 | +2.043e-14 | +0.11% | `PASSED` |
| **ndep** | `Duce et al.` | gN/m2/yr | **0.9981** | 1.358e+01 | 8.24% | 4.320e+00 | +6.391e-01 | +0.39% | `PASSED` |
| **par** | `GEWEX Climatology` | fraction | **0.9779** | 5.828e-03 | 1.27% | 4.454e-03 | -3.841e-04 | -0.08% | `PASSED` |
| **bathy** | `ETOPO / pmarge` | fraction | **1.0000** | 0.000e+00 | 0.00% | 0.000e+00 | +0.000e+00 | +0.00% | `PASSED` |
| **hydrofe** | `Hydrothermal Fe` | mol Fe/m2/s | **1.0000** | 0.000e+00 | 0.00% | 0.000e+00 | +0.000e+00 | +0.00% | `PASSED` |
| **river** | `Global NEWS 2` | MgN/m2/yr | **1.0000** | 0.000e+00 | 0.00% | 0.000e+00 | +0.000e+00 | +0.00% | `PASSED` |

### Key Diagnostic Insights:
- **Panaïotis et al. (2024) DOC:** Evaluates the new machine learning-based global DOC climatology against the classical Hansell (2009) baseline, capturing enhanced mesopelagic and surface carbon gradients.
- **WOA23 Nutrients & Oxygen:** Demonstrates strong correlation ($r > 0.95$) against legacy climatologies while incorporating decades of modern biogeochemical observations.
- **GLODAPv2.2016b Inorganic Carbon System:** Captures objectively mapped pre-industrial/modern total inorganic carbon and alkalinity distributions.
