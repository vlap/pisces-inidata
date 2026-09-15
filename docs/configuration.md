# Configuration & CLI Reference

`pisces-inidata` provides a modular configuration system through `products.cfg` and a unified command-line interface.

---

## 1. Product Configuration (`products.cfg`)

Individual observational products can be configured per tracer in `products.cfg` (located at the repository root). The configuration file uses standard bash parameter expansion, allowing seamless command-line overrides via environment variables:

```bash
# Example overrides:
export PRODUCT_NO3="woa23"
export PRODUCT_TALK="glodap_v2_2016b"
export PRODUCT_DOC="panaiotis2024"
```

### 3D Biogeochemical Tracers

| Variable | Environment Variable | Supported Options | Default |
| :--- | :--- | :--- | :--- |
| Nitrate ($\text{NO}_3$) | `PRODUCT_NO3` | `woa23`, `woa2009`, `sette_nomask`, `ece3` | `woa23` |
| Phosphate ($\text{PO}_4$) | `PRODUCT_PO4` | `woa23`, `woa2009`, `sette_nomask`, `ece3` | `woa23` |
| Silicate ($\text{Si}$) | `PRODUCT_Si` | `woa23`, `woa2009`, `sette_nomask`, `ece3` | `woa23` |
| Dissolved Oxygen ($\text{O}_2$) | `PRODUCT_O2` | `woa23`, `woa2009`, `sette_nomask`, `ece3` | `woa23` |
| Total Alkalinity ($\text{TALK}$) | `PRODUCT_TALK` | `glodap_v2_2016b`, `glodap_v2_2023`, `glodap_v1`, `sette_nomask`, `ece3` | `glodap_v2_2016b` |
| Total Dissolved Inorganic Carbon ($\text{TDIC}$) | `PRODUCT_TDIC` | `glodap_v2_2016b`, `glodap_v2_2023`, `glodap_v1`, `sette_nomask`, `ece3` | `glodap_v2_2016b` |
| Pre-Industrial DIC ($\text{PiDIC}$) | `PRODUCT_PiDIC` | `glodap_v2_2016b`, `glodap_v2_2023`, `glodap_v1`, `sette_nomask`, `ece3` | `glodap_v2_2016b` |
| Dissolved Organic Carbon ($\text{DOC}$) | `PRODUCT_DOC` | `panaiotis2024`, `sette_nomask`, `ece3` | `panaiotis2024` |
| Dissolved Iron ($\text{Fer}$) | `PRODUCT_Fer` | `sette_nomask`, `ece3` | `sette_nomask` |

### Surface & Boundary Forcings

| Forcing | Environment Variable | Supported Options | Default |
| :--- | :--- | :--- | :--- |
| Atmospheric Dust | `PRODUCT_DUST` | `ece3`, `sette_orca2` | `ece3` |
| Nitrogen Deposition | `PRODUCT_NDEP` | `ece3`, `sette_orca2` | `ece3` |
| PAR Solar Fraction | `PRODUCT_PAR` | `ece3`, `sette_orca2` | `ece3` |
| Bathymetric Slope | `PRODUCT_BATHY` | `ece3`, `sette_orca2` | `ece3` |
| Hydrothermal Fe | `PRODUCT_HYDROFE` | `sette_orca2` | `sette_orca2` |
| River Nutrient Fluxes | `PRODUCT_RIVER` | `ece3`, `sette_orca2` | `ece3` |

---

## 2. Command-Line Interface (`pisces-inidata`)

### `pisces-inidata check`
Runs pre-flight integrity verification before launching remapping jobs:
```bash
pisces-inidata check --orca ORCA2
```
- Verifies system binaries (`cdo`, `ncks`, `ncap2`, `ncatted`).
- Confirms presence of target domain files (`domain_cfg.nc`, `maskutil.nc`).
- Checks raw input catalog and verifies filesystem storage capacity.

### `pisces-inidata run`
Executes end-to-end interpolation and formatting:
```bash
# Generate inidata on ORCA2 (or eORCA1, eORCA025)
pisces-inidata run --orca ORCA2 --domain-dir /path/to/nemo/domain
```

### `pisces-inidata validate`
Executes statistical procedure validation against official NEMO/SETTE ORCA2 benchmark:
```bash
pisces-inidata validate --test-dir output_ORCA2 --ref-dir sette_reference_ORCA2
# Enforce non-zero exit code in CI:
pisces-inidata validate --fail-on-error
```

### `pisces-inidata test-reproduction`
Executes pipeline reproduction benchmark against EC-Earth3 eORCA1 baseline:
```bash
pisces-inidata test-reproduction \
    --test-dir work_eORCA1/reproduction_test \
    --ref-dir /path/to/ece3_eORCA1_reference \
    --mask domain/eORCA1/maskutil.nc
```

### `pisces-inidata pad`
Standalone vertical depth padding utility:
```bash
pisces-inidata pad input.nc output_padded.nc --bottom-depth 6000.0
```

### `pisces-inidata info`
Displays current environment, resolved paths, and active product configurations:
```bash
pisces-inidata info
```
