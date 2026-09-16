# Quickstart & TL;DR: Inidata Production Guide

This guide enables researchers and modelers with machine access (BSC Nord4, MareNostrum 5, local workstations, or generic HPC clusters) to generate ready-to-use PISCES initial condition files in minutes.

---

## TL;DR: Production Run (HPC / BSC Clusters)

On HPC systems where compute nodes lack direct internet access, data preparation and remapping are decoupled:

```text
[Interactive Node: with Internet]           [Batch Nodes: Slurm Compute]
Download raw data & standardize             Parallel CDO interpolation
         (~2 minutes)                               (Batch jobs)
              │                                          │
              ▼                                          ▼
  ${PISCES_WORKSPACE}/shared/                ${PISCES_WORKSPACE}/grids/eORCA1/inidata/
    ├── raw/                                   ├── data_NO3_eORCA1.nc
    └── standardized/${PRESET}/                ├── data_DIC_eORCA1.nc
                                               └── ... (15 NetCDF files)
```

### 1. Ingest & Standardize (Interactive Node)
Log in to an interactive node with internet access (e.g., `hub04` at BSC):

```bash
git clone https://github.com/vlap/pisces-inidata.git && cd pisces-inidata
pip install -e .

# Download active datasets and generate standardized 1°x1° sources in one shot:
pisces-inidata download --prepare
```

> **Note on Environment Modules:**
> Ensure `cdo`, `nco`, and `python` are available in your shell environment (e.g., via module load or conda). Cluster-specific Slurm parameters and module commands are declared in `platforms.yaml`.

---

### 2. Submit Parallel Remapping (Batch Slurm Cluster)
On batch compute nodes (e.g., `nord4` / `mn5`):

```bash
# Submit parallel remapping jobs for eORCA1 (standard 1-degree EC-Earth4 grid):
GRID_NAME=eORCA1 ./scripts/launcher_pisces_inidata.sh submit stage2
```

---

### 3. Verify Generated Outputs
Verify that all 15 NetCDF products were generated without blank or NaN fields:

```bash
pisces-inidata verify --grid eORCA1
```

All 15 target NetCDF files are ready in:
```text
${PISCES_WORKSPACE}/grids/eORCA1/inidata/
```

---

## Local Workstation & Interactive Run

To run the pipeline end-to-end on a local workstation or standalone compute node:

```bash
# 1. Install package
pip install -e .

# 2. Pre-flight sanity check
pisces-inidata check --grid eORCA1

# 3. Download & prepare sources
pisces-inidata download --prepare

# 4. Run end-to-end generation
pisces-inidata run --grid eORCA1

# 5. Verify outputs
pisces-inidata verify --grid eORCA1
```

---

## Declarative HPC Platforms (`platforms.yaml`)

Cluster accounts, partitions, scratch paths, and CDO threading are abstracted in `platforms.yaml`:

```bash
# View active and available platforms:
pisces-inidata platform-config

# Export shell variables for a specific platform:
pisces-inidata platform-config --platform nord4 --export
```

To configure a new cluster or custom account, edit `platforms.yaml` or set environment variables (`SLURM_ACCOUNT`, `SLURM_PARTITION`, `PISCES_WORKSPACE`).

---

## Target Grids Cheatsheet (`grids.yaml`)

Inspect target grid resource requirements and vertical levels:

```bash
pisces-inidata grid-config
```

| Grid | Description | Levels | Memory | Slurm Time | Batch Weights |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`ORCA2`** | NEMO standard 2-degree tripolar grid | 31 | 8 GB | 00:30:00 | No (Inline) |
| **`eORCA1`** | Extended ORCA 1-degree global grid | 75 | 16 GB | 01:00:00 | No (Inline) |
| **`eORCA025`** | Extended ORCA 0.25-degree eddy-permitting grid | 75 | 64 GB | 02:00:00 | Yes (Batch Slurm) |
| **`eORCA12`** | Extended ORCA 1/12-degree eddy-resolving grid | 75 | 128 GB | 04:00:00 | Yes (Batch Slurm) |

---

## Presets Cheatsheet (`sources.yaml`)

| Preset | Target Simulation | Nutrients & Oxygen | Carbon Chemistry | DOC | Iron & Surface |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ece4`** *(Default)* | EC-Earth4 Production | WOA23 (102 levels) | GLODAPv2.2016b | Panaïotis et al. 2024 (ML) | Tagliabue (2012) & SETTE |
| **`ece3`** | EC-Earth3 Reproduction | WOA2009 | GLODAPv1.1 | Hansell (2009) | Tagliabue (2012) & SETTE |
| **`official_sette`** | SETTE Verification Benchmark | SETTE unmasked | SETTE unmasked | SETTE unmasked | SETTE regular reference |

To select a preset:
```bash
pisces-inidata download --preset ece3 --prepare
GRID_NAME=eORCA1 PRESET=ece3 ./scripts/launcher_pisces_inidata.sh submit stage2
```

---

## Produced Output Files

Each run produces 15 standard PISCES initial condition NetCDFs in `${PISCES_WORKSPACE}/grids/eORCA1/inidata/`:

| File Name | Physical Variable | Timesteps | Dimensions |
| :--- | :--- | :---: | :---: |
| `data_NO3_eORCA1.nc` | Dissolved Nitrate ($\text{NO}_3$) | 12 monthly | $(12, Z, Y, X)$ |
| `data_PO4_eORCA1.nc` | Dissolved Phosphate ($\text{PO}_4$) | 12 monthly | $(12, Z, Y, X)$ |
| `data_Si_eORCA1.nc` | Dissolved Silicate ($\text{Si}$) | 12 monthly | $(12, Z, Y, X)$ |
| `data_O2_eORCA1.nc` | Dissolved Oxygen ($\text{O}_2$) | 12 monthly | $(12, Z, Y, X)$ |
| `data_TALK_eORCA1.nc` | Total Alkalinity (`Alkalini`) | Annual | $(1, Z, Y, X)$ |
| `data_TDIC_eORCA1.nc` | Total Dissolved Inorganic Carbon (`DIC`) | Annual | $(1, Z, Y, X)$ |
| `data_PiDIC_eORCA1.nc` | Pre-Industrial DIC | Annual | $(1, Z, Y, X)$ |
| `data_DOC_eORCA1.nc` | Dissolved Organic Carbon (`DOC`) | 12 monthly | $(12, Z, Y, X)$ |
| `data_Fer_eORCA1.nc` | Dissolved Iron (`Fer`) | Annual | $(1, Z, Y, X)$ |
| `dust.orca.nc` | Atmospheric Dust & Iron Flux | 12 monthly | $(12, Y, X)$ |
| `ndeposition.orca.nc` | Nitrogen Deposition Flux | 12 monthly | $(12, Y, X)$ |
| `par.orca.nc` | Photosynthetically Active Radiation | 365 daily | $(365, Y, X)$ |
| `bathy.orca.nc` | Continental Shelf Slope Fraction | Static 2D | $(Y, X)$ |
| `hydrofe.orca.nc` | Hydrothermal Vent Iron Injection | Static 2D | $(Y, X)$ |
| `river.orca.nc` | River Nutrient Inflow Discharges | 12 monthly | $(12, Y, X)$ |
