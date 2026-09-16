# Quickstart & TL;DR: Inidata Production Guide

This guide is designed for climate researchers, modelers, and research engineers who have access to computing systems (such as BSC Nord4 / MareNostrum 5 / Hub04, institutional clusters, or local workstations) and want to generate ready-to-use PISCES initial conditions and surface boundary forcings with minimal friction.

---

## ⚡ TL;DR: BSC HPC Fast-Track (Hub04 + Nord4 / MN5)

On high-performance computing centers where compute nodes have no direct internet access, data preparation and interpolation are decoupled across machines:

```
[hub04: Internet Node]                      [nord4 / mn5: Batch Compute]
Download raw data & standardize             Parallel CDO interpolation on Slurm
      (1-2 minutes)                                    (Batch jobs)
            │                                               │
            ▼                                               ▼
${PISCES_WORKSPACE}/shared/                 ${PISCES_WORKSPACE}/grids/${GRID}/inidata/
  ├── raw/                                    ├── data_NO3_${GRID}.nc
  └── standardized/${PRESET}/                 ├── data_DIC_${GRID}.nc
                                              └── ... (15 NetCDF files)
```

### Step 1: Ingest & Standardize on `hub04` (Interactive Node)
Log in to `hub04` (has internet access), load environment modules, and run the combined download and Stage 1 standardization:

```bash
ssh hub04
cd /gpfs/scratch/bsc32/${USER}
git clone https://github.com/vlap/pisces-inidata.git
cd pisces-inidata

# Load environment modules (or activate conda env)
module load CDO/2.3.0-gompi-2020b NCO/5.1.0-foss-2020b netcdf4-python/1.5.7-foss-2020b-Python-3.8.6
pip install -e .

# Download active observational datasets and standardize Stage 1 sources in one shot:
pisces-inidata download --prepare
```
> **What this does:** Fetches raw WOA23, GLODAPv2.2016b, Panaïotis DOC, and atmospheric forcings into `${PISCES_WORKSPACE}/shared/raw`, executes abyssal depth padding (6000 m), and creates uniform $1^\circ \times 1^\circ$ standardized regular NetCDF files in `${PISCES_WORKSPACE}/shared/standardized/ece4/`. This step runs in ~2 minutes and is shared across all target resolutions.

---

### Step 2: Submit Batch Remapping on `nord4` (Slurm Compute)
Log in to `nord4`, where batch compute nodes run pure interpolation without network calls:

```bash
ssh nord4
cd /gpfs/scratch/bsc32/${USER}/pisces-inidata
module load CDO/2.3.0-gompi-2020b NCO/5.1.0-foss-2020b netcdf4-python/1.5.7-foss-2020b-Python-3.8.6

# Option A: Submit batch remapping for eORCA1 (1-degree global grid):
GRID_NAME=eORCA1 ./scripts/launcher_pisces_inidata.sh submit stage2

# Option B: Submit batch remapping for eORCA025 (0.25-degree eddy-permitting grid):
# (Automatically requests 64G memory and submits batch SCRIP weights computation)
GRID_NAME=eORCA025 ./scripts/launcher_pisces_inidata.sh submit stage2
```

> **Target Domain Files at BSC:**
> At BSC, the standard EC-Earth4 NEMO domain directory is automatically detected at:
> `/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain`
> No extra flags are needed.

---

### Step 3: Inspect & Verify Outputs
Once the Slurm jobs finish, run pre-flight verification on the generated inidata:

```bash
pisces-inidata verify --grid eORCA1
# or for eORCA025:
pisces-inidata verify --grid eORCA025
```

All 15 target NetCDF files are ready in:
```text
${PISCES_WORKSPACE}/grids/${GRID_NAME}/inidata/
```

---

## 💻 TL;DR: Local Workstation & Interactive Fat Node

For local development, testing, or running standalone on a fat node:

```bash
# 1. Install package:
git clone https://github.com/vlap/pisces-inidata.git
cd pisces-inidata
pip install -e .

# 2. Verify local environment (CDO, NCO, Python packages):
pisces-inidata check --grid ORCA2

# 3. Download & prepare Stage 1 standardized sources:
pisces-inidata download --prepare

# 4. Run end-to-end generation (Stage 1 + Stage 2):
pisces-inidata run --grid ORCA2

# 5. Verify outputs:
pisces-inidata verify --grid ORCA2
```

---

## 🧭 Target Grids Cheatsheet (`grids.yaml`)

Target grid dimensions, vertical levels, and HPC resource allocations are configured declaratively in `grids.yaml`. You can inspect available grid profiles anytime:

```bash
pisces-inidata grid-config
```

| Grid | Description | Dimensions | Levels | Memory | Slurm Time | Batch Weights |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`ORCA2`** | NEMO standard 2-degree tripolar grid | $148 \times 180$ | 31 | 8 GB | 00:30:00 | No (Interactive) |
| **`eORCA1`** | Extended ORCA 1-degree global grid | $362 \times 292$ | 75 | 16 GB | 01:00:00 | No (Interactive) |
| **`eORCA025`** | Extended ORCA 0.25-degree eddy-permitting grid | $1442 \times 1207$ | 75 | 64 GB | 02:00:00 | Yes (Batch Slurm) |
| **`eORCA12`** | Extended ORCA 1/12-degree eddy-resolving grid | $4322 \times 3606$ | 75 | 128 GB | 04:00:00 | Yes (Batch Slurm) |

### Adding a Custom Grid
To add any new resolution or regional domain (e.g. `MED16`), simply add an entry to `grids.yaml` without modifying any scripts:

```yaml
grids:
  MED16:
    description: "Mediterranean 1/16-degree regional grid"
    resources:
      time: "02:00:00"
      memory: "32G"
      cpus: 16
      batch_weights: true
    disk_space_gb: 20.0
    vertical_levels: 75
```

---

## 🎛️ Presets Cheatsheet (`sources.yaml`)

Switch source datasets globally using `--preset`:

| Preset | Target Simulation | Nutrients & Oxygen | Carbon Chemistry | DOC | Iron & Surface |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ece4`** *(Default)* | EC-Earth4 Production | WOA23 (102 levels) | GLODAPv2.2016b | Panaïotis et al. 2024 (ML) | Tagliabue (2012) & SETTE |
| **`ece3`** | EC-Earth3 Reproduction | WOA2009 | GLODAPv1.1 | Hansell (2009) | Tagliabue (2012) & SETTE |
| **`official_sette`** | SETTE Verification Benchmark | SETTE unmasked | SETTE unmasked | SETTE unmasked | SETTE regular reference |

To run with a non-default preset:
```bash
pisces-inidata download --preset ece3 --prepare
GRID_NAME=eORCA1 PRESET=ece3 ./scripts/launcher_pisces_inidata.sh submit stage2
```

---

## 🗄️ Storage Layout & HPC Guidelines (Nord4 / MareNostrum 5)

`pisces-inidata` follows strict HPC storage hygiene to prevent quota exhaustion and I/O bottlenecks:

```text
${PISCES_WORKSPACE}/               # Default: /gpfs/scratch/bsc32/${USER}/pisces_inidata
├── shared/
│   ├── raw/                       # Downloaded observational archives (WOA23, GLODAP, DOC)
│   └── standardized/              # Stage 1 regular 1°x1° NetCDFs (cached across all grids)
│       ├── ece4/
│       └── ece3/
└── grids/
    └── eORCA1/                    # Grid-specific products
        ├── weights/               # Bilinear SCRIP remapping weights
        ├── inidata/               # Final 15 target NetCDF initial condition files
        ├── jobs/                  # Generated Slurm job scripts
        └── logs/                  # Slurm execution log files
```

### Nord4 Fast Local Scratch (`$TMPDIR`)
On BSC Nord4 and MareNostrum 5 compute nodes, the pipeline automatically detects and utilizes:
```text
$TMPDIR -> /scratch/tmp/$SLURM_JOB_ID
```
All heavy intermediate CDO piping and temporary operations run on local node NVMe SSD storage and are automatically wiped upon job completion. Shared GPFS filesystems only receive final, verified NetCDF products.

---

## 📦 What Files Are Produced?

Each completed run populates `${PISCES_WORKSPACE}/grids/${GRID_NAME}/inidata/` with 15 standard PISCES files:

| File Name | Physical Quantity | Temporal Resolution | Dimensions |
| :--- | :--- | :--- | :--- |
| `data_NO3_${GRID}.nc` | Dissolved Nitrate ($\text{NO}_3$) | 12 monthly fields | $(12, Z, Y, X)$ |
| `data_PO4_${GRID}.nc` | Dissolved Phosphate ($\text{PO}_4$) | 12 monthly fields | $(12, Z, Y, X)$ |
| `data_Si_${GRID}.nc` | Dissolved Silicate ($\text{Si}$) | 12 monthly fields | $(12, Z, Y, X)$ |
| `data_O2_${GRID}.nc` | Dissolved Oxygen ($\text{O}_2$) | 12 monthly fields | $(12, Z, Y, X)$ |
| `data_TALK_${GRID}.nc` | Total Alkalinity (`Alkalini`) | Annual climatology | $(1, Z, Y, X)$ |
| `data_TDIC_${GRID}.nc` | Total Dissolved Inorganic Carbon (`DIC`) | Annual climatology | $(1, Z, Y, X)$ |
| `data_PiDIC_${GRID}.nc` | Pre-Industrial Dissolved Inorganic Carbon | Annual climatology | $(1, Z, Y, X)$ |
| `data_DOC_${GRID}.nc` | Dissolved Organic Carbon (`DOC`) | 12 monthly fields | $(12, Z, Y, X)$ |
| `data_Fer_${GRID}.nc` | Dissolved Iron (`Fer`) | Annual climatology | $(1, Z, Y, X)$ |
| `dust.orca.nc` | Atmospheric Dust & Bioavailable Iron Flux | 12 monthly fields | $(12, Y, X)$ |
| `ndeposition.orca.nc` | Atmospheric Oxidized & Reduced Nitrogen Flux | 12 monthly fields | $(12, Y, X)$ |
| `par.orca.nc` | Photosynthetically Active Radiation Fraction | 365 daily fields | $(365, Y, X)$ |
| `bathy.orca.nc` | Continental Shelf & Margin Slope Fraction | Static 2D field | $(Y, X)$ |
| `hydrofe.orca.nc` | Hydrothermal Vent Iron Injection Flux | Static 2D field | $(Y, X)$ |
| `river.orca.nc` | River Nutrient Inflow Discharges | 12 monthly fields | $(12, Y, X)$ |

All output files are stamped with FAIR global metadata attributes (source URL, DOI, Git commit, executing user, and timestamp) conforming to CF-1.8 conventions.
