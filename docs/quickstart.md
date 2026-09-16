# Quickstart & TL;DR: Inidata Production Guide

This guide enables researchers and modelers with machine access (BSC Nord4, MareNostrum 5, local workstations, or generic HPC clusters) to generate ready-to-use PISCES initial condition files in minutes.

---

## ⚡ TL;DR: Production Run (HPC / BSC Clusters)

On HPC systems where compute nodes lack direct internet access, data preparation and remapping are cleanly decoupled:

```
[Interactive Node: with Internet]           [Batch Nodes: Slurm Compute]
Download raw data & standardize             Parallel CDO interpolation
         (~2 minutes)                               (Batch jobs)
              │                                          │
              ▼                                          ▼
  ${PISCES_WORKSPACE}/shared/                ${PISCES_WORKSPACE}/grids/${GRID}/inidata/
    ├── raw/                                   ├── data_NO3_${GRID}.nc
    └── standardized/${PRESET}/                ├── data_DIC_${GRID}.nc
                                               └── ... (15 NetCDF files)
```

### 1. Ingest & Standardize (Interactive Node)
Log in to an interactive node with internet access (e.g. `hub04` at BSC):

```bash
git clone https://github.com/vlap/pisces-inidata.git && cd pisces-inidata
pip install -e .

# Download active datasets and generate standardized 1°x1° sources in one shot:
pisces-inidata download --prepare
```

> **Note on Environment Modules:**
> Ensure `cdo`, `nco`, and `python` are loaded in your shell (e.g., `module load CDO NCO python` or via conda). Cluster-specific Slurm settings and module defaults are configured declaratively in `platforms.yaml`.

---

### 2. Submit Parallel Remapping (Batch Slurm Cluster)
On batch compute nodes (e.g. `nord4` / `mn5`):

```bash
# For eORCA1 (standard 1-degree EC-Earth4 grid):
GRID_NAME=eORCA1 ./scripts/launcher_pisces_inidata.sh submit stage2

# For eORCA025 (0.25-degree eddy-permitting grid):
GRID_NAME=eORCA025 ./scripts/launcher_pisces_inidata.sh submit stage2
```

---

### 3. Verify Generated Outputs
Verify that all 15 NetCDF products were generated without blank or NaN fields:

```bash
pisces-inidata verify --grid eORCA1
```

All 15 target NetCDF files are ready in:
```text
${PISCES_WORKSPACE}/grids/${GRID_NAME}/inidata/
```

---

## 💻 Local Workstation & Interactive Run

To run the entire pipeline end-to-end on a local machine or standalone compute node:

```bash
# 1. Install
pip install -e .

# 2. Pre-flight sanity check
pisces-inidata check --grid ORCA2

# 3. Download & prepare sources
pisces-inidata download --prepare

# 4. Run end-to-end generation
pisces-inidata run --grid ORCA2

# 5. Verify outputs
pisces-inidata verify --grid ORCA2
```

---

## 🖥️ Declarative HPC Platforms (`platforms.yaml`)

Cluster accounts, partitions, and scratch paths are abstracted in `platforms.yaml`:

```bash
# View active and available platforms:
pisces-inidata platform-config

# Export shell variables for a specific platform:
pisces-inidata platform-config --platform nord4 --export
```

To configure a new cluster or custom account, simply edit `platforms.yaml` or set standard environment variables (`SLURM_ACCOUNT`, `SLURM_PARTITION`, `PISCES_WORKSPACE`).

---

## 🧭 Target Grids Cheatsheet (`grids.yaml`)

Inspect target grid resource requirements and vertical levels:

```bash
pisces-inidata grid-config
```

| Grid | Description | Dimensions ($N_x \times N_y$) | Levels | Memory | Slurm Time | Batch Weights |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`ORCA2`** | NEMO standard 2-degree tripolar grid | $182 \times 149$ (SETTE) | 31 | 8 GB | 00:30:00 | No (Inline) |
| **`eORCA1`** | Extended ORCA 1-degree global grid | Nominal $1^\circ$ (e.g. $360 \times 290$ / $362 \times 292$) | 75 | 16 GB | 01:00:00 | No (Inline) |
| **`eORCA025`** | Extended ORCA 0.25-degree eddy-permitting grid | $1440 \times 1206$ (NEMO 4/5) / $1442 \times 1207$ (legacy) | 75 | 64 GB | 02:00:00 | Yes (Batch Slurm) |
| **`eORCA12`** | Extended ORCA 1/12-degree eddy-resolving grid | Nominal $1/12^\circ$ (e.g. $4320 \times 3604$) | 75 | 128 GB | 04:00:00 | Yes (Batch Slurm) |

> [!NOTE]
> **NEMO Version Grid Dimensions & `domain_cfg.nc`:**
> Documented grid dimensions often differ between NEMO versions. Legacy NEMO 3.6 setups included 2 cyclic halo columns (e.g. $1442 \times 1207$ for `eORCA025`), whereas modern NEMO (NEMO 4 / NEMO 5 / EC-Earth4) uses the true global computational grid without duplicate halos (e.g. **$1440 \times 1206$** in `eORCA025/domain_cfg.nc`).
> `pisces-inidata` is completely version-agnostic: spatial dimensions and curvilinear coordinates (`glamt`, `gphit`) are dynamically parsed directly from the target grid's `domain_cfg.nc` via CDO, never hardcoded in scripts.

---

## 🎛️ Presets Cheatsheet (`sources.yaml`)

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

## 📦 What Files Are Produced?

Each run produces 15 standard PISCES initial condition NetCDFs in `${PISCES_WORKSPACE}/grids/${GRID_NAME}/inidata/`:

| File Name | Physical Variable | Timesteps | Dimensions |
| :--- | :--- | :---: | :---: |
| `data_NO3_${GRID}.nc` | Dissolved Nitrate ($\text{NO}_3$) | 12 monthly | $(12, Z, Y, X)$ |
| `data_PO4_${GRID}.nc` | Dissolved Phosphate ($\text{PO}_4$) | 12 monthly | $(12, Z, Y, X)$ |
| `data_Si_${GRID}.nc` | Dissolved Silicate ($\text{Si}$) | 12 monthly | $(12, Z, Y, X)$ |
| `data_O2_${GRID}.nc` | Dissolved Oxygen ($\text{O}_2$) | 12 monthly | $(12, Z, Y, X)$ |
| `data_TALK_${GRID}.nc` | Total Alkalinity (`Alkalini`) | Annual | $(1, Z, Y, X)$ |
| `data_TDIC_${GRID}.nc` | Total Dissolved Inorganic Carbon (`DIC`) | Annual | $(1, Z, Y, X)$ |
| `data_PiDIC_${GRID}.nc` | Pre-Industrial DIC | Annual | $(1, Z, Y, X)$ |
| `data_DOC_${GRID}.nc` | Dissolved Organic Carbon (`DOC`) | 12 monthly | $(12, Z, Y, X)$ |
| `data_Fer_${GRID}.nc` | Dissolved Iron (`Fer`) | Annual | $(1, Z, Y, X)$ |
| `dust.orca.nc` | Atmospheric Dust & Iron Flux | 12 monthly | $(12, Y, X)$ |
| `ndeposition.orca.nc` | Nitrogen Deposition Flux | 12 monthly | $(12, Y, X)$ |
| `par.orca.nc` | Photosynthetically Active Radiation | 365 daily | $(365, Y, X)$ |
| `bathy.orca.nc` | Continental Shelf Slope Fraction | Static 2D | $(Y, X)$ |
| `hydrofe.orca.nc` | Hydrothermal Vent Iron Injection | Static 2D | $(Y, X)$ |
| `river.orca.nc` | River Nutrient Inflow Discharges | 12 monthly | $(12, Y, X)$ |
