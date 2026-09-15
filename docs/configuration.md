# Configuration Reference

The configuration system in `pisces-inidata` enables per-variable product selection without modifying pipeline code.

---

## The `products.cfg` File

The configuration file is located at the repository root as `products.cfg`. It uses bash-compatible parameter expansion syntax with environment variable overrides:

```bash
# Example syntax:
PRODUCT_NO3="${PRODUCT_NO3:-woa23}"
PRODUCT_TALK="${PRODUCT_TALK:-glodap_v2_2016b}"
PRODUCT_DOC="${PRODUCT_DOC:-panaiotis2024}"
```

### Tracer Product Options

| Variable Name | Environment Variable | Supported Values | Default |
| :--- | :--- | :--- | :--- |
| Nitrate | `PRODUCT_NO3` | `woa23`, `woa2009`, `sette_nomask`, `ece3` | `woa23` |
| Phosphate | `PRODUCT_PO4` | `woa23`, `woa2009`, `sette_nomask`, `ece3` | `woa23` |
| Silicate | `PRODUCT_Si` | `woa23`, `woa2009`, `sette_nomask`, `ece3` | `woa23` |
| Dissolved Oxygen | `PRODUCT_O2` | `woa23`, `woa2009`, `sette_nomask`, `ece3` | `woa23` |
| Total Alkalinity | `PRODUCT_TALK` | `glodap_v2_2016b`, `glodap_v2_2023`, `glodap_v1`, `sette_nomask`, `ece3`, `cmems` | `glodap_v2_2016b` |
| Total Dissolved Inorganic Carbon | `PRODUCT_TDIC` | `glodap_v2_2016b`, `glodap_v2_2023`, `glodap_v1`, `sette_nomask`, `ece3`, `cmems` | `glodap_v2_2016b` |
| Pre-Industrial DIC | `PRODUCT_PiDIC` | `glodap_v2_2016b`, `glodap_v2_2023`, `glodap_v1`, `sette_nomask`, `ece3`, `cmems` | `glodap_v2_2016b` |
| Dissolved Organic Carbon | `PRODUCT_DOC` | `panaiotis2024`, `sette_nomask`, `ece3` | `panaiotis2024` |
| Dissolved Iron | `PRODUCT_Fer` | `sette_nomask`, `ece3` | `sette_nomask` |

### Boundary Forcing Options

| Boundary Forcing | Environment Variable | Supported Values | Default |
| :--- | :--- | :--- | :--- |
| Atmospheric Dust | `PRODUCT_DUST` | `ece3`, `sette_orca2` | `ece3` |
| Nitrogen Deposition | `PRODUCT_NDEP` | `ece3`, `sette_orca2` | `ece3` |
| PAR Fraction | `PRODUCT_PAR` | `ece3`, `sette_orca2` | `ece3` |
| Bathymetric Slope | `PRODUCT_BATHY` | `ece3`, `sette_orca2` | `ece3` |
| Hydrothermal Iron | `PRODUCT_HYDROFE` | `sette_orca2` | `sette_orca2` |
| River Nutrient Fluxes | `PRODUCT_RIVER` | `ece3`, `sette_orca2` | `ece3` |

---

## Overriding Configuration in Shell or Scripts

You can override any variable dynamically in your current terminal session:

```bash
# Run with WOA 2009 instead of WOA 2023:
export PRODUCT_NO3="woa2009"
export PRODUCT_PO4="woa2009"
pisces-inidata run --orca ORCA2
```

To verify the effective configuration at any time:
```bash
pisces-inidata info
```
