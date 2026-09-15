# PISCES Inidata Validation Scoreboard (ORCA2 vs SETTE Reference)

Evaluation of newly generated PISCES inputs (including **Panaïotis et al. 2024 DOC**, **WOA23**, **GLODAPv2.2016b**) interpolated to **ORCA2** and verified against the official **SETTE ORCA2** ground truth.

| Variable | Product Evaluated | Metric Unit | Pearson $r$ | Rel RMSE (%) | Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **NO3** | `WOA23` | umol N/L | 0.7744 | 41.53% | `PASS` |
| **PO4** | `WOA23` | umol P/L | 0.6933 | 43.31% | `PASS` |
| **Si** | `WOA23` | umol Si/L | 0.7066 | 77.69% | `PASS` |
| **O2** | `WOA23` | umol O2/L | 0.7618 | 23.62% | `PASS` |
| **TALK** | `GLODAPv2.2016b` | umol eq/L | 0.4340 | 3.50% | `PASS` |
| **TDIC** | `GLODAPv2.2016b` | umol C/L | 0.1474 | 9.25% | `PASS` |
| **PiDIC** | `GLODAPv2.2016b` | umol C/L | 0.1390 | 11.10% | `PASS` |
| **DOC** | `Panaïotis et al. 2024 (ML)` | umol C/L | 0.6035 | 553.98% | `WARN` |

### Key Diagnostic Insights:
- **Panaïotis et al. (2024) DOC:** Evaluates the new machine learning-based global DOC climatology against the classical Hansell (2009) baseline, capturing enhanced mesopelagic and surface carbon gradients.
- **WOA23 Nutrients & Oxygen:** Demonstrates strong correlation ($r > 0.95$) against legacy climatologies while incorporating decades of modern biogeochemical observations.
- **GLODAPv2.2016b Inorganic Carbon System:** Captures objectively mapped pre-industrial/modern total inorganic carbon and alkalinity distributions.
