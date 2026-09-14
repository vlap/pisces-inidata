# PISCES Inidata Processing Tool (`pisces-inidata`)

A modular, CDO-based tool to generate and interpolate PISCES biogeochemical input datasets (`inidata`) for any NEMO ocean grid (e.g. `eORCA025`, `eORCA1`, `ORCA1`, `ORCA2`).

The tool follows the parallel batch processing architecture established in `/esarchive/scratch/vlapin/scripts/projects/wmo2025_gcp`: decoupled bash processors, CDO multithreading (`-P`), and parallel Slurm (`sbatch`) worker jobs on **Nord4**.

---

## Directory Structure

```text
code/pisces/
├── config.sh                   # Central configuration (grid, paths, Slurm, modules)
├── download_sources.sh         # Downloads and stages raw datasets (run on hub02 analysis)
├── gen_grid_and_weights.sh     # Builds target curvilinear grid NetCDF and CDO remap weights
├── format_tracers_3d.sh        # Processes 3D tracers (NO3, PO4, Si, O2, ALK, DIC, DOC, Fer)
├── format_rivers.sh            # Mass-conserving remapping for river nutrient fluxes (Global NEWS 2)
├── format_surface_forcings.sh  # Remaps dust, Fe solubility, N-deposition, and PAR daily fraction
├── format_bathy_hydrofe.sh     # Remaps bathymetric shelf fraction and hydrothermal Fe sources
├── launcher_pisces_inidata.sh  # Generates and submits parallel Slurm jobs on Nord4
└── README.md                   # This documentation
```

---

## Prerequisites & Inputs

### Required Input Files (provided by user)
Set their location in `config.sh`:
- `domain_cfg.nc`: Domain geometry file containing horizontal coordinates (`glamt`, `gphit`), cell scale factors (`e1t`, `e2t`), and vertical metrics.
  - Default BSC path: `/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain/${GRID_NAME}/domain_cfg.nc`
- `maskutil.nc`: Land-sea mask containing `tmaskutil`.
  - Default BSC path: `/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain/${GRID_NAME}/maskutil.nc`

### Software Requirements
- **CDO** (v2.0+) with NetCDF-4 / HDF5 support.
- **NCO** (`ncks`, `ncatted`, `ncrename`).
- HPC modules loaded automatically via `config.sh`:
  ```bash
  module load CDO/2.1.1-foss-2019b NCO/5.1.3-foss-2019b
  ```

---

## Workflow

### Step 1: Configuration (`config.sh`)
Edit `config.sh` to adjust target grid or machine paths if needed:
```bash
# Target grid resolution
GRID_NAME="eORCA025"   # eORCA025, eORCA1, ORCA1, etc.

# Scratch directory (Nord4 / hub02 default)
SCRATCH_ROOT="/esarchive/scratch/vlapin/tmp"
```

### Step 2: Sync to Cluster & Download Sources (`download_sources.sh`)
From your local machine, copy the tool to your cluster workspace:
```bash
# Sync scripts from local workstation to cluster scratch:
rsync -av /home/volant/code/pisces/ nord4:/esarchive/scratch/vlapin/tmp/pisces-inidata/
```

Log in to **`hub02 analysis`** (which has external internet access) to download and stage the datasets:
```bash
ssh hub02
cd /esarchive/scratch/vlapin/tmp/pisces-inidata
./download_sources.sh
```
This downloads and unpacks the raw/baseline inputs into `${SCRATCH_ROOT}/pisces_inidata_${GRID_NAME}/raw_sources/`.

### Step 3: Launch Parallel Processing on Nord4 (`launcher_pisces_inidata.sh`)
Log in to **`nord4`** and submit the formatting jobs to Slurm:
```bash
ssh nord4
cd /esarchive/scratch/vlapin/tmp/pisces-inidata

# Dry-run preview:
./launcher_pisces_inidata.sh dry-run

# Submit to Slurm:
./launcher_pisces_inidata.sh submit
```

The launcher will:
1. Synchronously extract the target curvilinear grid and precompute bilinear and distance-weighted remapping weights (`weights_r360x180_to_${GRID_NAME}_bilin.nc`).
2. Submit 9 separate parallel jobs for 3D tracers (`NO3`, `PO4`, `Si`, `O2`, `TALK`, `TDIC`, `PiDIC`, `DOC`, `Fer`).
3. Submit a dedicated job for strictly mass-conserved river nutrient mapping.
4. Submit jobs for surface forcings (`dust`, `ndep`, `par`).
5. Submit jobs for topography and hydrothermal vent iron (`bathy`, `hydrofe`).

Monitor jobs with:
```bash
squeue -u $USER
```

---

## Scientific Implementation Details

### 1. 3D Tracers (`format_tracers_3d.sh`)
- Supports **Offline Mode** (remaps 3D fields directly to target curvilinear grid using precomputed bilinear weights) and **Online Mode** (prepares unmasked regular grid files `data_*_nomask.nc` accompanied by the online SCRIP weights `weights_3D_r360x180_bilin.nc`).

### 2. Conservative River Nutrient Remapping (`format_rivers.sh`)
- River mouth inputs (`riverdin`, `riverdip`, `riverdon`, `riverdop`, `riverdoc`, `riverdsi`, `riverdic`) from Global NEWS 2 are areal fluxes ($\text{Mg} \cdot \text{m}^{-2} \cdot \text{yr}^{-1}$).
- When going from low-resolution ($2^\circ$) to high-resolution ($1/4^\circ$), naive interpolation dilutes or multiplies the mass flux.
- The tool multiplies by source cell area, remaps the total nutrient mass rate ($\text{Mg}/\text{yr}$), applies coastal wet cell masking (`tmaskutil`), converts back to areal flux on the target grid, and scales by the exact ratio:
  $$\alpha = \frac{\sum M_{\text{source}}}{\sum M_{\text{target}}}$$
  guaranteeing exact global mass conservation down to machine precision.

### 3. Dust and Atmospheric Deposition (`format_surface_forcings.sh`)
- Surface dust and iron fluxes are remapped onto the target grid and masked against coastal land points.

---

## Portability & Sharing
To use on another machine or cluster:
1. Clone / copy the `pisces-inidata` folder.
2. In `config.sh`, update `DOMAIN_BASE_DIR`, `SCRATCH_ROOT`, and the Slurm partition/account variables (`SLURM_ACCOUNT`, `SLURM_PARTITION`).
