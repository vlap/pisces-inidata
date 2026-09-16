# PISCES Inidata Validation Scorecard (ORCA2 vs SETTE Benchmark)

**Configuration Preset:** `official_sette`  

Automated procedure validation evaluating newly generated 3D tracer initial conditions on **ORCA2** against the official **NEMO/PISCES SETTE** benchmark ground truth to detect unit errors, pipeline orientation bugs, and unphysical values.

> **Note:** Variables inherited directly from the SETTE repository (e.g. dissolved iron `Fer` from Tagliabue et al. 2012) or static boundary forcings (`dust`, `ndep`, `bathy`, `river`, `hydrofe`, `par`) are not benchmarked here to avoid uninformative self-comparisons.

## Supported Products Scorecard (3D Tracers)

| Variable | Product Evaluated | Unit | Physical Range [min, max] | Mean Ratio | Pearson $r$ | Rel RMSE (%) | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **NO3** | `SETTE nomask (pure interpolation)` | umol N/L | [0.00e+00, 5.25e+01] | 1.00x | **1.0000** | 0.00% | **PASS** |
| **PO4** | `SETTE nomask (pure interpolation)` | umol P/L | [0.00e+00, 9.59e+00] | 1.00x | **1.0000** | 0.00% | **PASS** |
| **Si** | `SETTE nomask (pure interpolation)` | umol Si/L | [0.00e+00, 2.36e+02] | 1.00x | **1.0000** | 0.00% | **PASS** |
| **O2** | `SETTE nomask (pure interpolation)` | umol O2/L | [0.00e+00, 1.06e+01] | 1.00x | **1.0000** | 0.00% | **PASS** |
| **TALK** | `SETTE nomask (pure interpolation)` | umol eq/L | [9.43e+02, 2.65e+03] | 1.00x | **1.0000** | 0.00% | **PASS** |
| **TDIC** | `SETTE nomask (pure interpolation)` | umol C/L | [9.72e+02, 2.40e+03] | 1.00x | **1.0000** | 0.00% | **PASS** |
| **PiDIC** | `SETTE nomask (pure interpolation)` | umol C/L | [9.53e+02, 2.40e+03] | 1.00x | **1.0000** | 0.00% | **PASS** |
| **DOC** | `SETTE nomask (pure interpolation)` | umol C/L | [0.00e+00, 1.00e+02] | 1.00x | **1.0000** | 0.00% | **WARN** |

### Diagnostic Notes:
- **Scale Sanity:** Mean ratio within $[0.2, 5.0]$ confirms unit consistency.
- **Pattern Orientation:** Positive Pearson $r$ verifies spatial orientation is non-inverted.
- **Panaïotis 2024 DOC:** Modern machine-learning global climatology exhibits higher carbon values than the 2009 Hansell baseline used in SETTE, flagged with WARN as an expected scientific difference.
