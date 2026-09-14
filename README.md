# PISCES Inidata Processing Tool (`pisces-inidata`)

A generic, modular, and parallel tool to generate, interpolate, and validate PISCES biogeochemical initial condition and boundary forcing files (`inidata`) for any NEMO ocean grid (e.g. `eORCA025`, `eORCA1`, `ORCA1`, `ORCA2`).

Supports **modern observational products** (**WOA23** for nutrients, **GLODAPv2.2016b** for carbon) as well as exact bitwise reproduction of historical baselines (**EC-Earth3 / SHACONEMO**).

---

## Directory Structure

```text
pisces-inidata/
├── config.sh                   # Central configuration (grid, paths, Slurm, module environment)
├── download_sources.sh         # Downloads and stages raw datasets (WOA23, GLODAPv2, SETTE)
├── gen_grid_and_weights.sh     # Extracts curvilinear coordinates, cell areas (e1t*e2t), and CDO weights
├── prepare_woa23_tracer.py     # Assembles WOA23 12-month upper + annual deep profiles with 6000m padding
├── pad_abyssal_depth.py        # Generic utility to replicate deepest level to 6000m for deep L75 bracketing
├── format_tracers_3d.sh        # Formats 3D tracers (NO3, PO4, Si, O2, TALK, TDIC, PiDIC, DOC, Fer)
├── format_rivers.sh            # Strictly mass-conserving remapping for river nutrients (Global NEWS 2)
├── format_surface_forcings.sh  # Remaps dust, Fe solubility, N-deposition, and daily PAR fraction
├── format_bathy_hydrofe.sh     # Remaps bathymetric shelf slope fraction and hydrothermal Fe sources
├── launcher_pisces_inidata.sh  # Generates and submits parallel Slurm worker jobs on Nord4
├── evaluate_closeness.py       # High-performance validation utility (RMSE, MAE, Pearson r, Inventory)
├── run_validation_suite.sh     # Automated end-to-end test and validation harness
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

## Operating Modes (`SOURCE_MODE`)

Configured via `SOURCE_MODE` in `config.sh`:

1. **`modern` (Default & Recommended):**
   - **Nutrients ($NO_3, PO_4, Si, O_2$):** NOAA NCEI **WOA23** (World Ocean Atlas 2023, 102 vertical levels).
   - **Carbon System ($TAlk, TDIC, PiDIC$):** NOAA OCADS **GLODAPv2.2016b** (incorporating CARINA Arctic data and modern anthropogenic $CO_2$ accumulation).
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
