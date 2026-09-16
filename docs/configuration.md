# Configuration & CLI Reference

`pisces-inidata` provides a transparent, declarative configuration system through presets (`ece4`, `ece3`, `official_sette`), `sources.yaml`, and a unified command-line interface.

---

## 1. Configuration Presets

Instead of selecting sources variable-by-variable, users can choose curated configuration presets designed for specific modeling purposes:

| Preset | Purpose | Nutrients & Oxygen | Carbon Chemistry | DOC | Iron & Boundary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ece4`** *(Default)* | Modern observational datasets for **EC-Earth4** production runs | WOA23 (102 levels) | GLODAPv2.2016b | Panaïotis et al. 2024 (ML) | Tagliabue (2012) & SETTE |
| **`ece3`** | Observational sources originally used in **EC-Earth3** (baseline reproduction) | WOA2009 | GLODAPv1.1 | Hansell (2009) | Tagliabue (2012) & SETTE |
| **`official_sette`** | Official regular unmasked **NEMO/PISCES SETTE** reference (all vars from SETTE, pure interpolation) | `sette_nomask` | `sette_nomask` | `sette_nomask` | `sette_nomask` & `sette_orca2` |

Presets can be selected in three ways:

1. **In `sources.yaml`:**
   ```yaml
   preset: ece4  # Options: ece4 (default) | ece3 | official_sette
   ```
2. **Via dedicated preset files:**
   Preset template files are available in the `presets/` directory:
   - `presets/sources_ece4.yaml`
   - `presets/sources_ece3.yaml`
   - `presets/sources_official_sette.yaml`
3. **Via the `--preset` CLI flag or `PRESET` environment variable:**
   ```bash
   pisces-inidata info --preset ece3
   pisces-inidata run --orca eORCA1 --preset ece3
   pisces-inidata config --preset official_sette --export
   ```

---

## 2. Observational Source Configuration (`sources.yaml`)

Individual observational source datasets can be customized on top of any preset in `sources.yaml`. Explicit variable entries in the file or environment variables (`PRODUCT_*`) override the preset defaults:

```bash
# Example overrides:
export PRODUCT_NO3="woa23"
export PRODUCT_TALK="glodap_v2_2016b"
export PRODUCT_DOC="panaiotis2024"
```

> [!IMPORTANT]
> **EC-Earth3 Inidata is strictly a verification benchmark:**
> EC-Earth3 inidata cannot be selected as an input source for generating inidata. Inidata generation must proceed from primary observational climatologies. EC-Earth3 inidata is reserved exclusively as reference ground truth in the pipeline reproduction test (`pisces-inidata test-reproduction`).

### 3D Biogeochemical Tracers

| Variable | Environment Variable | Supported Options | Default |
| :--- | :--- | :--- | :--- |
| Nitrate ($\text{NO}_3$) | `PRODUCT_NO3` | `woa23`, `woa2009`, `sette_nomask` | `woa23` |
| Phosphate ($\text{PO}_4$) | `PRODUCT_PO4` | `woa23`, `woa2009`, `sette_nomask` | `woa23` |
| Silicate ($\text{Si}$) | `PRODUCT_Si` | `woa23`, `woa2009`, `sette_nomask` | `woa23` |
| Dissolved Oxygen ($\text{O}_2$) | `PRODUCT_O2` | `woa23`, `woa2009`, `sette_nomask` | `woa23` |
| Total Alkalinity ($\text{TALK}$) | `PRODUCT_TALK` | `glodap_v2_2016b`, `glodap_v2_2023`, `glodap_v1`, `sette_nomask` | `glodap_v2_2016b` |
| Total Dissolved Inorganic Carbon ($\text{TDIC}$) | `PRODUCT_TDIC` | `glodap_v2_2016b`, `glodap_v2_2023`, `glodap_v1`, `sette_nomask` | `glodap_v2_2016b` |
| Pre-Industrial DIC ($\text{PiDIC}$) | `PRODUCT_PiDIC` | `glodap_v2_2016b`, `glodap_v2_2023`, `glodap_v1`, `sette_nomask` | `glodap_v2_2016b` |
| Dissolved Organic Carbon ($\text{DOC}$) | `PRODUCT_DOC` | `panaiotis2024`, `sette_nomask` | `panaiotis2024` |
| Dissolved Iron ($\text{Fer}$) | `PRODUCT_Fer` | `sette_nomask` | `sette_nomask` |

### Surface & Boundary Forcings

| Forcing | Environment Variable | Supported Options | Default |
| :--- | :--- | :--- | :--- |
| Atmospheric Dust | `PRODUCT_DUST` | `sette_orca2` | `sette_orca2` |
| Nitrogen Deposition | `PRODUCT_NDEP` | `sette_orca2` | `sette_orca2` |
| PAR Solar Fraction | `PRODUCT_PAR` | `sette_orca2` | `sette_orca2` |
| Bathymetric Slope | `PRODUCT_BATHY` | `sette_orca2` | `sette_orca2` |
| Hydrothermal Fe | `PRODUCT_HYDROFE` | `sette_orca2` | `sette_orca2` |
| River Nutrient Fluxes | `PRODUCT_RIVER` | `sette_orca2` | `sette_orca2` |

---

## 3. Command-Line Interface (`pisces-inidata`)

### `pisces-inidata check`
Runs pre-flight integrity verification before launching remapping jobs:
```bash
pisces-inidata check --orca ORCA2
# Check against specific preset:
pisces-inidata check --orca eORCA1 --preset ece3
```
- Verifies system binaries (`cdo`, `ncks`, `ncap2`, `ncatted`).
- Confirms presence of target domain files (`domain_cfg.nc`, `maskutil.nc`).
- Checks raw input catalog and verifies filesystem storage capacity.

### `pisces-inidata run`
Executes end-to-end interpolation and formatting:
```bash
# Generate inidata on ORCA2 (or eORCA1, eORCA025)
pisces-inidata run --orca ORCA2 --domain-dir /path/to/nemo/domain

# Run with specific preset:
pisces-inidata run --orca eORCA1 --preset ece3
```

### `pisces-inidata validate`
Executes statistical procedure validation against official NEMO/SETTE ORCA2 benchmark:
```bash
# Validate generated ORCA2 outputs (default preset: official_sette)
pisces-inidata validate --preset official_sette --test-dir output_ORCA2 --ref-dir sette_reference_ORCA2
# Enforce non-zero exit code in CI:
pisces-inidata validate --fail-on-error
```

### `pisces-inidata test-reproduction`
Executes pipeline reproduction benchmark against EC-Earth3 eORCA1 baseline:
```bash
# Validate reproduction against EC-Earth3 baseline (default preset: official_sette)
pisces-inidata test-reproduction --preset official_sette
# Or with explicit paths:
pisces-inidata test-reproduction \
    --preset official_sette \
    --test-dir output_eORCA1 \
    --ref-dir /path/to/ece3_eORCA1_reference \
    --mask domain/eORCA1/maskutil.nc
```

### `pisces-inidata download`
Fetches and stages raw observational datasets:
```bash
pisces-inidata download
# Download raw datasets for a specific preset:
pisces-inidata download --preset ece3
```

### `pisces-inidata pad`
Standalone vertical depth padding utility:
```bash
pisces-inidata pad input.nc output_padded.nc --bottom-depth 6000.0
```

### `pisces-inidata info`
Displays current environment, active preset, resolved paths, and product configurations:
```bash
pisces-inidata info
# Preview configuration for a different preset:
pisces-inidata info --preset ece3
```
