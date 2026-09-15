# PISCES Inidata Processing Tool (`pisces-inidata`)

A generic, modular, and parallel tool to generate, interpolate, and validate PISCES biogeochemical initial condition and boundary forcing files (`inidata`) for any NEMO ocean grid (e.g. `eORCA025`, `eORCA1`, `ORCA1`, `ORCA2`).

Supports **modern observational products** (**WOA23** for nutrients, **GLODAPv3** [July 2026, NCEI Accession 0315582] as default with multi-version fallback to `v2.2023`, `v2.2016b`, and `v1.1` for carbon chemistry), as well as exact bitwise reproduction of historical baselines (**EC-Earth3 / SHACONEMO**).

---

## Directory Structure

```text
pisces-inidata/
├── config.sh                   # Central configuration (grid, paths, Slurm, GLODAP version)
├── download_sources.sh         # Downloads raw datasets (WOA23, GLODAPv3/v2, SETTE)
├── gen_grid_and_weights.sh     # Extracts curvilinear coordinates, cell areas (e1t*e2t), and CDO weights
├── prepare_woa23_tracer.py     # Assembles WOA23 12-month profile with 6000m padding
├── pad_abyssal_depth.py        # Generic utility to replicate deepest level to 6000m for deep L75 bracketing
├── format_tracers_3d.sh        # Formats 3D tracers (NO3, PO4, Si, O2, TALK, TDIC, PiDIC, DOC, Fer)
├── format_rivers.sh            # Remapping for river nutrients (Global NEWS 2)
├── format_surface_forcings.sh  # Remaps dust, Fe solubility, N-deposition, and daily PAR fraction
├── format_bathy_hydrofe.sh     # Remaps bathymetric shelf slope fraction and hydrothermal Fe sources
├── launcher_pisces_inidata.sh  # Generates and submits parallel Slurm worker jobs on Nord4
├── evaluate_closeness.py       # High-performance validation utility (RMSE, MAE, Pearson r, Inventory)
├── run_validation_suite.sh     # Automated end-to-end test and validation harness
├── DATA_CATALOG.md             # Detailed dataset provenance catalog and download URLs
├── COMPREHENSIVE_INVENTORY.md  # Comprehensive inventory of all 15 PISCES inidata files
├── VALIDATION_REPORT.md        # Comprehensive verification report against official ECE4 references
└── README.md                   # This documentation
```

---

## Prerequisites & Inputs

### Required Input Files (per target grid)
The pipeline automatically locates domain definitions in `${DOMAIN_BASE_DIR}/${GRID_NAME}/`:
- `domain_cfg.nc`: Curvilinear horizontal coordinates (`glamt`, `gphit`), cell scale factors (`e1t`, `e2t`), and vertical levels (`nav_lev`).
  - BSC path for `eORCA1`: `/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain/eORCA1/domain_cfg.nc`
  - BSC path for `eORCA025`: `/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain/eORCA025/domain_cfg.nc`
- `maskutil.nc`: Land-sea mask containing `tmaskutil`.

### Software Environment
- **CDO** (v2.0+) with NetCDF-4 / HDF5 support.
- **NCO** (`ncks`, `ncatted`, `ncrename`, `ncwa`).
- **Python 3** with `netCDF4` and `numpy`.
- Automatically loaded on Nord4 / BSC interactive nodes via `config.sh`:
  ```bash
  module load CDO/2.3.0-gompi-2020b NCO/5.1.0-foss-2020b netcdf4-python/1.6.1-foss-2020b-Python-3.8.6
  ```

---

## Operating Modes & Carbon Climatologies

Configured via `SOURCE_MODE` and `GLODAP_VERSION` in `config.sh`:

1. **`modern` (Default & Recommended):**
   - **Nutrients ($NO_3, PO_4, Si, O_2$):** NOAA NCEI **WOA23** (World Ocean Atlas 2023, 102 vertical levels).
   - **Carbon System ($TAlk, TDIC, PiDIC$):** **GLODAPv3** (Default; Lange et al., 2026, NCEI Accession 0315582, 1,181 cruises from 1972–2023). Multi-version resolution dynamically supports `GLODAP_VERSION="v3"`, `"v2.2023"`, `"v2.2016b"`, or `"v1.1"`.
   - **Organic Carbon & Iron ($DOC, Fer$):** Global observational climatologies (Hansell et al., Tagliabue et al.).
   - **Abyssal Padding:** Extends deep ocean coordinates to 6000 m by replicating bottom observations, eliminating missing values across NEMO L75 levels (down to 5902 m).

2. **`official_regular`:**
   - Uses SETTE official $1^\circ \times 1^\circ$ unmasked regular fields (`data_*_nomask.nc`) with 3D interpolation to the target grid.

3. **`ece3_baseline`:**
   - Direct nearest-neighbor remapping from the historical EC-Earth3 baseline (`v3.3.3/inidata/pisces`).
   - Achieves **100.000% exact bitwise identity** against `/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/pisces/`.

---

## Quickstart Workflow

### 1. Download / Verify Raw Sources
On an interactive node with outgoing internet access (e.g., `hub04` / `hub02`):
```bash
./download_sources.sh
```
This fetches the 52 NOAA NCEI WOA23 NetCDF-4 files, GLODAPv2 mapped climatology, and SETTE official package into `${RAW_DIR}`.

### 2. Run for Any Grid (e.g., `eORCA1` or `eORCA025`)
On **Nord4**, execute batch generation with Slurm:
```bash
# Generate for eORCA1 (default):
./launcher_pisces_inidata.sh submit

# Generate for eORCA025:
GRID_NAME=eORCA025 ./launcher_pisces_inidata.sh submit
```

To preview the generated Slurm job scripts without submitting:
```bash
GRID_NAME=eORCA025 ./launcher_pisces_inidata.sh dry-run
```

Or run interactively in sequential mode:
```bash
export GRID_NAME=eORCA025
./gen_grid_and_weights.sh
for trc in NO3 PO4 Si O2 TALK TDIC PiDIC DOC Fer; do
    ./format_tracers_3d.sh "${trc}"
done
./format_rivers.sh
./format_surface_forcings.sh all
./format_bathy_hydrofe.sh all
```

### 3. Verify Output
Run the closeness validation harness against ground truth references:
```bash
./run_validation_suite.sh
```
Metrics are computed strictly over valid ocean wet cells (`tmaskutil > 0`) across all 75 vertical levels and 12 timesteps.

---

## Output Catalog

Outputs and standard compatibility symlinks are placed in `${WORK_DIR}/output_${GRID_NAME}/`:

| Component | Primary Generated File | Standard NEMO / ECE4 Symlink |
| :--- | :--- | :--- |
| **Nitrate** | `data_NO3_${GRID_NAME}.nc` | `NO3_WOA23_monthly_${GRID_NAME}.nc` |
| **Phosphate** | `data_PO4_${GRID_NAME}.nc` | `PO4_WOA23_monthly_${GRID_NAME}.nc` |
| **Silicate** | `data_Si_${GRID_NAME}.nc` | `Si_WOA23_monthly_${GRID_NAME}.nc` |
| **Oxygen** | `data_O2_${GRID_NAME}.nc` | `O2_WOA23_monthly_${GRID_NAME}.nc` |
| **Total Alkalinity** | `data_TALK_${GRID_NAME}.nc` | `Alkalini_GLODAP_annual_${GRID_NAME}.nc` |
| **Dissolved Inorganic Carbon** | `data_TDIC_${GRID_NAME}.nc` | `DIC_GLODAP_annual_${GRID_NAME}.nc` |
| **Pre-industrial DIC** | `data_PiDIC_${GRID_NAME}.nc` | `PiDIC_GLODAP_annual_${GRID_NAME}.nc` |
| **Dissolved Organic Carbon** | `data_DOC_${GRID_NAME}.nc` | `DOC_PISCES_monthly_${GRID_NAME}.nc` |
| **Dissolved Iron** | `data_Fer_${GRID_NAME}.nc` | `Fer_PISCES_monthly_${GRID_NAME}.nc` |
| **River Nutrients** | `river.orca.nc` | `river_global_news_${GRID_NAME}.nc` |
| **Atmospheric Dust & Fe** | `dust.orca.nc` | `dust_INCA_${GRID_NAME}.nc`, `Solubility_T62_Mahowald_${GRID_NAME}.nc` |
| **Atmospheric N-Deposition** | `ndeposition.orca.nc` | `ndeposition_Duce_${GRID_NAME}.nc` |
| **PAR Radiation Fraction** | `par.orca.nc` | `par_fraction_gewex_clim90s00s_${GRID_NAME}.nc` |
| **Bathy Shelf Slope Fraction** | `bathy.orca.nc` | `pmarge_etopo_${GRID_NAME}.nc` |
| **Hydrothermal Iron** | `hydrofe.orca.nc` | — |
| **Online Remap Weights** | `weights_3D_r360x180_bilin.nc` | — |

---

## Scientific Implementation Highlights

### 1. Strict River Mass Conservation (`format_rivers.sh`)
River nutrient fluxes ($DIN, DIP, DON, DOP, DOC, DSi, DIC$) from Global NEWS 2 are expressed in areal rates ($\text{Mg} \cdot \text{m}^{-2} \cdot \text{yr}^{-1}$). Remapping between varying grid resolutions requires mass integration:
$$\text{Mass}_{\text{src}} = \text{Flux}_{\text{src}} \times \text{Area}_{\text{src}}$$
After remapping total mass to target coastal wet cells (`tmaskutil`), target fluxes are scaled by:
$$\alpha = \frac{\sum M_{\text{src}}}{\sum M_{\text{tgt}}}$$
guaranteeing **100.000% exact global mass rate conservation** across arbitrary target grid resolutions.

### 2. Abyssal Coordinate Extension (`pad_abyssal_depth.py`)
Observational datasets frequently terminate above the deepest abyssal ocean depths (WOA23 and GLODAP stop at 5500 m; NOMASK stops at 5250 m), while NEMO L75 vertical discretization extends to 5902 m (levels 71–74).
The pipeline pre-pads the vertical coordinate to 6000 m by replicating bottom observations. CDO 1D vertical interpolation (`cdo -intlevel`) then brackets all deep target levels, preventing missing values (`NaN`) in the ocean abyss.

### 3. Objective Analysis & Extrapolation of Non-Gridded Products (e.g., GLODAP)
Raw observational datasets like GLODAP (Global Ocean Data Analysis Project) originate as **discrete, non-gridded, non-synoptic bottle casts and CTD transects** gathered across hundreds of research expeditions over decades (e.g., 1,181 cruises across 1972–2023 in GLODAPv3). To transform these irregular points into spatially continuous climatological fields for ocean biogeochemical models (PISCES), a formal mathematical and physical processing sequence is applied:

1. **Secondary Quality Control & Inversion:**
   Because cruises span decades with varying sensor calibrations and analytical methods, deep-water crossover analysis (typically below 1500–2000 m where natural variability is minimal) calculates cruise-to-cruise systematic offsets. In GLODAPv3, a **Furthest-First (FF) inversion algorithm** minimizes regional biases compared to earlier weighted least-squares (WLSQ) approaches, generating an internally consistent point dataset.

2. **Variational Objective Analysis (DIVA):**
   Point measurements are mapped onto standard horizontal surfaces ($1^\circ \times 1^\circ$) using **DIVA** (Data-Interpolating Variational Analysis) based on the finite-element method (Lauvset et al., 2016). DIVA minimizes a continuous variational cost function:
   $$J[\varphi] = \sum_{i=1}^N \mu_i \left( \varphi(x_i, y_i) - d_i \right)^2 + \int_{\Omega} \left( \alpha_1 (\nabla \varphi)^2 + \alpha_2 (\nabla^2 \varphi)^2 + \alpha_0 \varphi^2 \right) d\Omega$$
   - The first term penalizes deviations from discrete bottle observations $d_i$ weighted by error variance $\mu_i$.
   - The second term enforces spatial regularity (gradient and curvature smoothness penalties).
   - **Physical Boundary Masking:** Unlike isotropic Gaussian objective analysis, DIVA uses finite elements that respect complex coastlines, peninsulas, and submarine ridges—preventing artificial leakage across land barriers (e.g., between the Atlantic and Pacific across Central America, or across island arcs).

3. **Decoupling Temporal Trends (Reference Year Normalization):**
   To create a steady-state initial condition, transient tracers (such as anthropogenic total dissolved inorganic carbon, $C_{\text{ant}}$) are normalized to a specific reference epoch (e.g., 2002 for GLODAPv2, or modern CMIP baseline) using extended Multiple Linear Regression (eMLR) or chlorofluorocarbon (CFC-11/12) / $SF_6$ transit-time distributions. Natural pre-industrial DIC ($\text{PI\_TCO2}$) is separated by subtracting $C_{\text{ant}}$ from measured total DIC.

4. **Downstream Grid Extrapolation & Boundary Filling (`cdo fillmiss`):**
   Mapped climatologies may still contain gaps in isolated, semi-enclosed marginal seas (e.g., Mediterranean Sea, Red Sea, Black Sea, high Arctic fjords) where cruise transects are sparse or excluded by the global analysis mask.
   - The pipeline applies **Poisson/Laplacian iterative boundary relaxation** via `cdo fillmiss` on standard surfaces, propagating surrounding oceanic property gradients smoothly into unobserved coastal/enclosed basins without creating artificial step discontinuities.
   - Pre-computed bilinear remapping weights then project the continuous regular field onto the target NEMO curvilinear tripolar mesh ($eORCA1$, $eORCA025$).
