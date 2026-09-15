# PISCES Inidata: Comprehensive Inventory of Raw Data Sources & Processing

This document provides an exhaustive reference for all observational, atmospheric, terrestrial, and bathymetric data sources used to construct initial conditions and surface boundary forcings for the **PISCES** (Pelagic Interactions Scheme for Carbon and Ecosystem Studies) biogeochemical model across arbitrary NEMO curvilinear ocean grids (`eORCA1`, `eORCA025`, `ORCA1`, `ORCA2`).

---

## 1. Summary Catalog Table

| Inidata Component | Target Output File(s)<br>(NEMO Standard / ECE4 Alias) | Target Grid & Time Dimensions | Modern Observational Product<br>(`SOURCE_MODE="modern"`) | Baseline / Fallback Source<br>(`official_regular` / `ece3_baseline`) | Remapping & Conservation Methodology |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Nitrate ($NO_3$)** | `data_NO3_${GRID}.nc`<br>$\rightarrow$ `NO3_WOA23_monthly_${GRID}.nc` | 12 monthly climatology<br>75 vertical levels (L75)<br>Curvilinear ($ny \times nx$) | **NOAA NCEI WOA23**<br>(NetCDF-4, $1^\circ \times 1^\circ$, 102 levels) | WOA2009 / SETTE `data_NO3_nomask.nc` | Upper 43 monthly levels dynamically blended with annual deep levels (850–5500m); coordinate extended to 6000m; horizontal bilinear remap (`remap`); vertical linear interpolation (`intlevel`) to exact L75 depths. |
| **Phosphate ($PO_4$)** | `data_PO4_${GRID}.nc`<br>$\rightarrow$ `PO4_WOA23_monthly_${GRID}.nc` | 12 monthly climatology<br>75 vertical levels (L75)<br>Curvilinear ($ny \times nx$) | **NOAA NCEI WOA23**<br>(NetCDF-4, $1^\circ \times 1^\circ$, 102 levels) | WOA2009 / SETTE `data_PO4_nomask.nc` | Same as $NO_3$. Upper 43 monthly levels + deep annual + 6000m abyssal padding; bilinear horizontal remap + `intlevel` to L75. |
| **Silicate ($Si$)** | `data_Si_${GRID}.nc`<br>$\rightarrow$ `Si_WOA23_monthly_${GRID}.nc` | 12 monthly climatology<br>75 vertical levels (L75)<br>Curvilinear ($ny \times nx$) | **NOAA NCEI WOA23**<br>(NetCDF-4, $1^\circ \times 1^\circ$, 102 levels) | WOA2009 / SETTE `data_SIL_nomask.nc` | Same as $NO_3$. Upper 43 monthly levels + deep annual + 6000m abyssal padding; bilinear horizontal remap + `intlevel` to L75. |
| **Dissolved Oxygen ($O_2$)** | `data_O2_${GRID}.nc`<br>$\rightarrow$ `O2_WOA23_monthly_${GRID}.nc` | 12 monthly climatology<br>75 vertical levels (L75)<br>Curvilinear ($ny \times nx$) | **NOAA NCEI WOA23**<br>(NetCDF-4, $1^\circ \times 1^\circ$, 102 levels) | WOA2009 / SETTE `data_OXY_nomask.nc` | Upper 57 monthly levels (0–1500m) dynamically detected and stitched with deep annual (to 5500m) + 6000m abyssal padding; bilinear remap + `intlevel` to L75. |
| **Total Alkalinity ($TAlk$)** | `data_TALK_${GRID}.nc`<br>$\rightarrow$ `Alkalini_GLODAP_annual_${GRID}.nc` | 1 annual mean timestep<br>75 vertical levels (L75)<br>Curvilinear ($ny \times nx$) | **GLODAPv2.2016b** (NOAA OCADS)<br>(NetCDF-4, $1^\circ \times 1^\circ$, 33 levels, 0–5500m) | GLODAPv1.1 / SETTE `data_ALK_nomask.nc` | `cdo fillmiss` (nearest-neighbor extrapolation of unmapped marginal/inland seas); bilinear remap; 6000m abyssal padding; `intlevel` to L75. Variable renamed to `Alkalini`. |
| **Total Dissolved Inorganic Carbon ($TDIC$)** | `data_TDIC_${GRID}.nc`<br>$\rightarrow$ `DIC_GLODAP_annual_${GRID}.nc` | 1 annual mean timestep<br>75 vertical levels (L75)<br>Curvilinear ($ny \times nx$) | **GLODAPv2.2016b** (`TCO2.nc`)<br>(NetCDF-4, $1^\circ \times 1^\circ$, 33 levels, 0–5500m) | GLODAPv1.1 / SETTE `data_DIC_nomask.nc` | Same as $TAlk$. `cdo fillmiss` $\rightarrow$ bilinear remap $\rightarrow$ 6000m abyssal padding $\rightarrow$ `intlevel` to L75. Variable renamed to `DIC`. Captures modern accumulated anthropogenic carbon. |
| **Pre-industrial Dissolved Inorganic Carbon ($PiDIC$)** | `data_PiDIC_${GRID}.nc`<br>$\rightarrow$ `PiDIC_GLODAP_annual_${GRID}.nc` | 1 annual mean timestep<br>75 vertical levels (L75)<br>Curvilinear ($ny \times nx$) | **GLODAPv2.2016b** (`PI_TCO2.nc`)<br>(NetCDF-4, $1^\circ \times 1^\circ$, 33 levels, 0–5500m) | Baseline ECE3 / PISCES v3.3.3 | Same as $TDIC$. Pre-industrial natural carbon distribution for transient climate simulations. |
| **Dissolved Organic Carbon ($DOC$)** | `data_DOC_${GRID}.nc`<br>$\rightarrow$ `DOC_PISCES_monthly_${GRID}.nc` | 12 monthly climatology<br>75 vertical levels (L75)<br>Curvilinear ($ny \times nx$) | **SETTE Official NOMASK** (`data_DOC_nomask.nc`) | SETTE v5.0.0 / ECE3 `data_DOC_orca1.nc` | Global observational synthesis (Hansell et al.); 31 levels (0–5250m); bilinear remapped $\rightarrow$ 6000m abyssal padding $\rightarrow$ `intlevel` to L75. |
| **Dissolved Iron ($Fer$)** | `data_Fer_${GRID}.nc`<br>$\rightarrow$ `Fer_PISCES_monthly_${GRID}.nc` | 12 monthly climatology<br>75 vertical levels (L75)<br>Curvilinear ($ny \times nx$) | **SETTE Official NOMASK** (`data_FER_nomask.nc`) | SETTE v5.0.0 / ECE3 `data_FER_orca1.nc` | Global dissolved iron synthesis (Tagliabue et al.); units $\mu\text{mol/L}$; bilinear remapped $\rightarrow$ 6000m abyssal padding $\rightarrow$ `intlevel` to L75. |
| **River Nutrient Exports** ($DIN, DIP, DON, DOP, DOC, DSi, DIC$) | `river.orca.nc`<br>$\rightarrow$ `river_global_news_${GRID}.nc` | 12 monthly climatology<br>1 surface level<br>Curvilinear ($ny \times nx$, 7 variables) | **Global NEWS 2 / Seitzinger et al.**<br>(SETTE `river.orca.nc`, ORCA2 2D) | Same | **Strict mass conservation:** Multiplies source flux by source cell area ($\text{Mass}_{\text{src}} = \text{Flux}_{\text{src}} \times \text{Area}_{\text{src}}$); distance-weighted remap (`gendis`); coastal wet masking (`tmaskutil`); divided by target cell area; scaled by $\alpha = \sum M_{\text{src}} / \sum M_{\text{tgt}}$ to enforce **100.000% global mass rate conservation**. |
| **Atmospheric Dust & Iron Solubility** | `dust.orca.nc`<br>$\rightarrow$ `dust_INCA_${GRID}.nc`<br>$\rightarrow$ `Solubility_T62_Mahowald_${GRID}.nc` | 12 monthly climatology<br>1 surface level<br>Curvilinear ($ny \times nx$, 5 variables) | **INCA / Mahowald T62 Climatology**<br>(SETTE `dust.orca.nc`) | Same | Bilinear remapped from atmospheric Gaussian grid to target curvilinear coordinates (`genbil`). Variables: `dust`, `dustfer`, `dustpo4`, `dustsi`, `solubility2`. |
| **Atmospheric Nitrogen Deposition** | `ndeposition.orca.nc`<br>$\rightarrow$ `ndeposition_Duce_${GRID}.nc` | 12 monthly climatology<br>1 surface level<br>Curvilinear ($ny \times nx$, 2 variables) | **Duce et al. / Dentener et al.**<br>(SETTE `ndeposition.orca.nc`) | Same | Oxidized and reduced nitrogen deposition ($NH_x, NO_y$); bilinear remapped from regular grid to target curvilinear coordinates. |
| **Photosynthetically Available Radiation (PAR)** | `par.orca.nc`<br>$\rightarrow$ `par_fraction_gewex_clim90s00s_${GRID}.nc` | 365 daily timesteps<br>1 surface level<br>Curvilinear ($ny \times nx$) | **GEWEX Surface Radiation Budget**<br>(SETTE `par.orca.nc`, 1990s–2000s climatology) | Same | Daily penetrative shortwave solar radiation fraction (`fr_par`); bilinear remapped from regular grid to target curvilinear coordinates. |
| **Bathymetric Shelf Slope Fraction** | `bathy.orca.nc`<br>$\rightarrow$ `pmarge_etopo_${GRID}.nc` | 1 static 2D field<br>Curvilinear ($ny \times nx$) | **ETOPO2 / ETOPO1 Bathymetry**<br>(SETTE `bathy.orca.nc`) | Same | High-resolution shelf and slope area fraction used to parameterize subgrid sediment iron reduction flux; bilinear remapped. |
| **Hydrothermal Vent Iron Injection** | `hydrofe.orca.nc` | 1 static 2D field<br>Curvilinear ($ny \times nx$) | **Ridge 2000 / Beaulieu et al.**<br>(SETTE `hydrofe.orca.nc`) | Same | Deep ocean ridge hydrothermal vent iron injection locations and flux rates; bilinear remapped. |
| **NEMO Online Remapping Weights** | `weights_3D_r360x180_bilin.nc` | SCRIP NetCDF format | **CDO `genbil` Engine** | Same | Precomputed bilinear remapping weights from $1^\circ \times 1^\circ$ regular spherical grid to target curvilinear grid; provided for optional runtime NEMO online remapping. |
| **Atmospheric $CO_2$ Time Series** | `atcco2.txt` | 1D ASCII time series (Year vs ppmv) | **NOAA ESRL / CMIP6 Historical + SSP** | Same | Grid-independent 1D forcing file specifying atmospheric dry air mole fraction of $CO_2$. |

---

## 2. Detailed Data Source Profiles

### 2.1 World Ocean Atlas 2023 (WOA23)
* **Distributor:** NOAA National Centers for Environmental Information (NCEI)
* **Accession:** NOAA Atlas NESDIS 89–92 (2023 Release)
* **URL:** `https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA/`
* **Format:** NetCDF-4 (CF-1.8 compliant), 102 standard depth levels (0–5500 m), $1^\circ \times 1^\circ$ global resolution.
* **Analyzed Fields Used:**
  - Nitrate ($NO_3$): `woa23_all_n[00-12]_01.nc` (Variable: `n_an`, units: $\mu\text{mol/L}$)
  - Phosphate ($PO_4$): `woa23_all_p[00-12]_01.nc` (Variable: `p_an`, units: $\mu\text{mol/L}$)
  - Silicate ($Si$): `woa23_all_i[00-12]_01.nc` (Variable: `i_an`, units: $\mu\text{mol/L}$)
  - Dissolved Oxygen ($O_2$): `woa23_all_o[00-12]_01.nc` (Variable: `o_an`, units: $\mu\text{mol/L}$, converted to $\text{ml/L}$ via $1\text{ ml/L} = 44.661\,\mu\text{mol/L}$)
* **Vertical Structure & Assembly:**
  - Nutrients ($N, P, Si$) have 43 monthly upper levels (0–800 m) and 102 annual deep levels (850–5500 m).
  - Oxygen ($O_2$) has 57 monthly upper levels (0–1500 m) and 102 annual deep levels (1550–5500 m).
  - Assembled dynamically by `prepare_woa23_tracer.py`, streaming slice-by-slice into 12-month NetCDF-4 files.

### 2.2 Global Ocean Data Analysis Project v2 (GLODAPv2.2016b)
* **Distributor:** NOAA Ocean Carbon and Acidification Data System (OCADS)
* **Accession:** 0162565 / Lauvset et al. (Earth Syst. Sci. Data, 2016)
* **URL:** `https://www.ncei.noaa.gov/data/oceans/ncei/ocads/data/0162565/mapped/`
* **Format:** NetCDF-4, 33 vertical depth levels (0–5500 m), $1^\circ \times 1^\circ$ global resolution.
* **Fields Used:**
  - Total Alkalinity ($TAlk$): `GLODAPv2.2016b.TAlk.nc` (Variable: `TAlk`, renamed to `Alkalini`, units: $\mu\text{mol/kg}$)
  - Total Dissolved Inorganic Carbon ($TDIC$): `GLODAPv2.2016b.TCO2.nc` (Variable: `TCO2`, renamed to `DIC`, units: $\mu\text{mol/kg}$)
  - Pre-industrial DIC ($PiDIC$): `GLODAPv2.2016b.PI_TCO2.nc` (Variable: `PI_TCO2`, renamed to `DIC`, units: $\mu\text{mol/kg}$)
* **Key Enhancements over GLODAPv1.1:**
  - Includes CARINA Arctic data capturing Siberian shelf river freshwater dilution.
  - Updates $CO_2$ storage for modern anthropogenic accumulation.

### 2.3 Dissolved Organic Carbon & Dissolved Iron (NOMASK Baseline)
* **Distributor:** NEMO Consortium / SETTE input repository (`ORCA2_INPUTS_PISCES_v5.0.0`)
* **Sources:**
  - **DOC:** Global observational climatology synthesized by Hansell et al. (31 depth levels, 0–5250 m).
  - **Fer:** Global dissolved iron compilation by Tagliabue et al. (Biogeosciences, 2012) incorporating GEOTRACES transects (31 depth levels, 0–5250 m, units: $\mu\text{mol/L}$).

### 2.4 River Nutrient Inputs (Global NEWS 2)
* **Distributor:** Global Nutrient Export from Watersheds 2 (Seitzinger et al., Global Biogeochem. Cycles, 2010)
* **Input File:** `river.orca.nc` (ORCA2 $2^\circ$ resolution, monthly climatology)
* **Nutrient Species:**
  - Dissolved Inorganic Nitrogen (`riverdin`, $\text{Mg N/yr}$)
  - Dissolved Inorganic Phosphorus (`riverdip`, $\text{Mg P/yr}$)
  - Dissolved Organic Nitrogen (`riverdon`, $\text{Mg N/yr}$)
  - Dissolved Organic Phosphorus (`riverdop`, $\text{Mg P/yr}$)
  - Dissolved Organic Carbon (`riverdoc`, $\text{Mg C/yr}$)
  - Dissolved Silicate (`riverdsi`, $\text{Mg Si/yr}$)
  - Dissolved Inorganic Carbon (`riverdic`, $\text{Mg C/yr}$)

### 2.5 Surface Forcings & Bathymetry
* **Dust & Fe Solubility:** INCA atmospheric chemistry model / Mahowald et al. (2005) T62 Gaussian grid.
* **Nitrogen Deposition:** Duce et al. (Science, 2008) / Dentener et al. (Global Biogeochem. Cycles, 2006).
* **Photosynthetically Available Radiation:** GEWEX Surface Radiation Budget (SRB) 3-hourly climatology (1990–2000), processed into 365 daily shortwave fraction fractions.
* **Sediment Iron Release Margin:** ETOPO global topographic/bathymetric dataset slope index.
* **Hydrothermal Vents:** Ridge 2000 hydrothermal vent database (Beaulieu et al., 2013).

---

## 3. Mathematical & Algorithmic Methodologies

### 3.1 Abyssal Coordinate Extension (6000 m Padding)
Standard 1D vertical interpolation (`cdo -intlevel`) does not extrapolate beyond the deepest source observation layer:
- WOA23 and GLODAP end at $5500\,\text{m}$.
- NOMASK ends at $5250\,\text{m}$.
- NEMO L75 discretization extends to $5902.04\,\text{m}$ (Levels 71–74: $5291.65\,\text{m}$, $5494.55\,\text{m}$, $5698.04\,\text{m}$, $5902.04\,\text{m}$).

To guarantee that deep ocean wet cells contain finite, physical values rather than `NaN` missing values, `pad_abyssal_depth.py` appends a boundary layer at $6000.0\,\text{m}$ replicating the concentration of the deepest observation ($5500\,\text{m}$ or $5250\,\text{m}$). The vertical interpolation brackets all L75 depths, ensuring smooth, continuous concentrations to the ocean floor.

### 3.2 Strict River Mass Conservation
River nutrient inputs are given as surface fluxes ($F$, in $\text{Mg} \cdot \text{m}^{-2} \cdot \text{yr}^{-1}$). When remapping from coarse resolution (ORCA2) to fine resolution (`eORCA1` or `eORCA025`), naive remapping leads to severe mass dissipation or artificial amplification.

The pipeline implements an exact two-step conservation budget:
1. **Source Mass Rate Integration:**
   $$M_{\text{src}} = \sum_{i, j} F_{\text{src}}(i, j) \cdot A_{\text{src}}(i, j)$$
2. **Target Remapping and Ocean Masking:**
   $$F_{\text{tgt, raw}} = \text{remap}_{\text{dis}}(M_{\text{src}}) \cdot \frac{t_{\text{maskutil}}}{A_{\text{tgt}}}$$
3. **Exact Rescaling:**
   $$\alpha = \frac{M_{\text{src}}}{\sum_{i, j} F_{\text{tgt, raw}}(i, j) \cdot A_{\text{tgt}}(i, j)}$$
   $$F_{\text{final}}(i, j) = \alpha \cdot F_{\text{tgt, raw}}(i, j)$$

This guarantees **100.000% machine-precision conservation** of river nutrient inputs across any target grid resolution.
