# PISCES Inidata Validation Scorecard (ORCA2 vs SETTE Benchmark)

**Configuration Preset:** `official_sette`  

Automated procedure validation evaluating newly generated 3D tracer initial conditions on **ORCA2** against the official **NEMO/PISCES SETTE** benchmark ground truth to detect unit errors, pipeline orientation bugs, and unphysical values.

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

## Boundary Forcing Conservation (River Nutrient Discharges)

Evaluation of global integrated nutrient mass inputs from river discharge to ensure nutrient inputs into the marine ecosystem remain invariant across grid remapping.

| Variable | Description | Unit | Total Flux (Test) | Total Flux (Ref) | Ratio (Test/Ref) | Pearson $r$ | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **riverdin** | Dissolved Inorganic Nitrogen (DIN) | MgN/m2/yr | 2.4577e+07 | 2.4577e+07 | 1.00x | **1.0000** | **PASS** |
| **riverdip** | Dissolved Inorganic Phosphorus (DIP) | MgP/m2/yr | 1.9586e+06 | 1.9586e+06 | 1.00x | **1.0000** | **PASS** |
| **riverdon** | Dissolved Organic Nitrogen (DON) | MgN/m2/yr | 1.1564e+07 | 1.1564e+07 | 1.00x | **1.0000** | **PASS** |
| **riverdop** | Dissolved Organic Phosphorus (DOP) | MgP/m2/yr | 6.1999e+05 | 6.1999e+05 | 1.00x | **1.0000** | **PASS** |
| **riverdoc** | Dissolved Organic Carbon (DOC) | MgC/m2/yr | 1.7155e+08 | 1.7155e+08 | 1.00x | **1.0000** | **PASS** |
| **riverdsi** | Dissolved Silicate (DSi) | MgSi/m2/yr | 1.5549e+08 | 1.5549e+08 | 1.00x | **1.0000** | **PASS** |
| **riverdic** | Dissolved Inorganic Carbon (DIC) | MgC/m2/yr | 4.2146e+08 | 4.2146e+08 | 1.00x | **1.0000** | **PASS** |

### Diagnostic Notes:
- **Scale Sanity:** Mean ratio within $[0.2, 5.0]$ confirms unit consistency.
- **Pattern Orientation:** Positive Pearson $r$ verifies spatial orientation is non-inverted.
- **Panaïotis 2024 DOC:** Modern machine-learning global climatology exhibits higher carbon values than the 2009 Hansell baseline used in SETTE, flagged with WARN as an expected scientific difference.
- **River Nutrient Conservation:** Integrated river nutrient inputs should conserve mass within 2% when remapped, avoiding artificial nutrient dilution or enrichment.
