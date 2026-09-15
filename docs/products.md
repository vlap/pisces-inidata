# Supported Products Catalog

`pisces-inidata` supports a wide array of observational, machine-learning, and reanalysis products. Each tracer and boundary condition can be configured individually in `products.cfg`.

---

## 1. 3D Biogeochemical Tracers

### Nitrate ($\text{NO}_3$), Phosphate ($\text{PO}_4$), Silicate ($\text{Si}$), Dissolved Oxygen ($\text{O}_2$)
- **`woa23` (Recommended Default):** World Ocean Atlas 2023 (NOAA NCEI). 102 standard depth levels, $1^\circ \times 1^\circ$ resolution. Incorporates thousands of modern profiling floats and WOCE/GO-SHIP cruises.
- **`woa2009`:** World Ocean Atlas 2009. 33 standard depth levels. Used in legacy EC-Earth3 / CMIP6 configurations.
- **`sette_nomask`:** Extrapolated reference field from the official NEMO/PISCES SETTE validation package.
- **`ece3`:** Historical initial conditions used in EC-Earth3-CC simulations.

### Total Alkalinity ($\text{TALK}$) & Total Dissolved Inorganic Carbon ($\text{TDIC}$)
- **`glodap_v3` (Recommended Default):** Uses GLODAPv3 mapping with expanded observational coverage (1,181 cruises, 1.5 million bottle samples).
- **`glodap_v2_2016b`:** Official 3D objectively mapped climatology (Lauvset et al. 2016). Standard $1^\circ \times 1^\circ$ grid with 33 vertical depth levels (0m to 5500m).
- **`glodap_v2_2023`:** Updated GLODAP synthesis.
- **`cmems`:** Gridded carbon extraction from Copernicus Marine Service (`INSITU_GLO_BGC_CARBON_DISCRETE_MY_013_050` / `013_046`).
- **`sette_nomask`:** Standard SETTE reference fields.

### Pre-Industrial Dissolved Inorganic Carbon ($\text{PiDIC}$)
- **`glodap_v3` / `glodap_v2_2016b`:** Derived by subtracting anthropogenic carbon ($\text{C}_{\text{ant}}$) estimates from total dissolved inorganic carbon.

### Dissolved Organic Carbon ($\text{DOC}$)
- **`panaiotis2024` (Recommended Default):** State-of-the-art machine learning dissolved organic carbon climatology (Panaïotis et al. 2024, SEANOE, [doi:10.17882/101170](https://doi.org/101170)). Trained on global in situ DOC observations with environmental predictors (temperature, salinity, depth, nutrients, primary production) at $1^\circ \times 1^\circ$ and 102 vertical depths.
- **`sette_nomask`:** Hansell et al. (2009) global DOC compilation.

### Dissolved Iron ($\text{Fer}$)
- **`sette_nomask` (Default):** Tagliabue et al. (2012) global dissolved iron compilation and model synthesis.
- **`ece3`:** Historical EC-Earth3 dissolved iron fields.

---

## 2. Atmospheric & Boundary Forcings

### Atmospheric Dust Deposition
- **`ece3` (Default):** INCA/Mahowald aerosol chemical transport model climatology. Provides soluble and bioavailable iron deposition flux.
- **`sette_orca2`:** Standard SETTE ORCA2 monthly climatology.

### Atmospheric Nitrogen Deposition
- **`ece3` (Default):** Duce et al. global atmospheric nitrogen deposition fields ($\text{NO}_y$ and $\text{NH}_x$).
- **`sette_orca2`:** SETTE ORCA2 monthly forcing.

### Photosynthetically Available Radiation ($\text{PAR}$)
- **`ece3` (Default):** Satellite-derived GEWEX surface radiation climatology (1990–2000).
- **`sette_orca2`:** SETTE ORCA2 solar radiation fraction.

### Coastal Bathymetric Shelf Slope
- **`ece3` (Default):** Shelf slope and sediment interaction factor derived from high-resolution ETOPO bathymetry.
- **`sette_orca2`:** SETTE ORCA2 reference bathymetry factor.

### Hydrothermal Iron Source
- **`sette_orca2` (Default):** Deep ridge hydrothermal iron injection fluxes along ocean spreading centers.

### Riverine Nutrient Influx
- **`ece3` (Default):** Global NEWS 2 (Nutrient Export from WaterSheds 2) model discharge for dissolved inorganic/organic nitrogen, phosphorus, carbon, and silicate.
- **`sette_orca2`:** SETTE ORCA2 riverine input fluxes.
