# PISCES Inidata Processing Tool (`pisces-inidata`)

[![CI](https://github.com/vlap/pisces-inidata/actions/workflows/ci.yml/badge.svg)](https://github.com/vlap/pisces-inidata/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/pisces-inidata/badge/?version=latest)](https://pisces-inidata.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)

A generic, modular, and reproducible tool to generate, interpolate, and validate **PISCES** biogeochemical initial condition and boundary forcing files (`inidata`) for any **NEMO** ocean grid (`ORCA2`, `eORCA1`, `eORCA025`).

Built for **EC-Earth4** and the broader ocean modeling community.

---

## Key Features

- **Per-Variable Source Selection:** Choose observational climatologies independently for each tracer via `sources.yaml`.
- **Modern Gridded Datasets:**
  - **Nutrients & Oxygen:** World Ocean Atlas 2023 (**WOA23**, 102 depth levels) or WOA2009.
  - **Carbon Chemistry:** **GLODAP** (3D mapped climatology v2.2016b [default], or Copernicus Marine Service). *Only 3D gridded products are supported; discrete bottle master files are unsupported.*
  - **Dissolved Organic Carbon:** State-of-the-art machine-learning DOC climatology (**Panaïotis et al. 2024**, SEANOE) or Hansell (2009).
  - **Dissolved Iron:** Tagliabue et al. (2012) global compilation.
  - **Boundary & Surface Forcings:** Dust deposition (INCA/Mahowald), Nitrogen deposition (Duce et al.), PAR fraction (GEWEX), bathymetric shelf slope factor (ETOPO), hydrothermal Fe injection, and river nutrient discharge (Global NEWS 2).
- **Abyssal Depth Bracketing:** Automatically extends deep ocean profiles to 6000m to bracket NEMO deep levels (L75 down to 5902m, L121), eliminating abyssal missing values.
- **Tripolar Remapping & Coastal Flood:** Precomputes CDO SCRIP bilinear weights for curvilinear ORCA grids and flood-fills narrow coastal straits using `setmisstonn`.
- **Automated Validation Scoreboard:** Generates point-by-point statistical diagnostics (Pearson $r$, Spearman $\rho$, RMSE, NRMSE, Mean Bias) against the official NEMO/PISCES SETTE ORCA2 reference.

---

## Directory Structure

```text
pisces-inidata/
├── docs/                        # ReadTheDocs Sphinx documentation (MyST Markdown)
│   ├── index.md                 # Documentation homepage
│   ├── products.md              # Supported observational products catalog
│   ├── configuration.md         # Per-variable configuration (sources.yaml) reference
│   └── validation.md            # Statistical scoreboards and validation suites
├── python/                      # Python library and CLI package
│   └── pisces_inidata/
│       ├── __init__.py
│       ├── cli.py               # CLI: pisces-inidata (produce, remap, prepare-sources, check, ...)
│       ├── catalog.py           # Single-source-of-truth metadata & conventions catalog
│       ├── weights.py           # Target grid coordinates & SCRIP remapping weights
│       ├── etl.py               # Stage 1: Grid-agnostic source data standardization
│       ├── remap.py             # Stage 2: Target-centric vertical/horizontal remapping
│       ├── launcher.py          # Pipeline orchestration & Slurm Job Array generator
│       ├── reference.py         # Ground-truth SETTE benchmark assembly on ORCA2
│       ├── nco_util.py          # Configured python-cdo interface with threading options
│       ├── check.py             # Pre-flight system & data integrity verifier
│       ├── config/              # Bundled package configurations & templates
│       │   ├── catalog.yaml     # Metadata catalog & data conventions
│       │   ├── grids.yaml       # Declarative target grid specifications & HPC profiles
│       │   ├── platforms.yaml   # Declarative HPC platform profiles (Slurm accounts, scratch)
│       │   ├── sources.yaml     # Default template source configuration
│       │   └── packs/           # Curated source configuration packs
│       │       ├── sources_ece4.yaml
│       │       ├── sources_ece3.yaml
│       │       └── sources_official_sette.yaml
│       ├── download.py          # Selective raw dataset downloader & staging
│       ├── glodap.py            # GLODAP vertical coordinate standardizer & padder
│       ├── padding.py           # Abyssal depth padding algorithm (up to 6000m)
│       ├── woa23.py             # WOA23 12-month depth profile builder
│       ├── doc.py               # Panaïotis et al. (2024) DOC NetCDF generator
│       ├── scoreboard.py        # Validation scoreboard generator
│       ├── reproduction.py      # EC-Earth3 baseline precision benchmark
│       └── verify.py            # Non-blank output inspection & bounds checker
├── tests/                       # Unit tests (pytest)
├── legacy/                      # Preserved legacy Bash pipeline scripts
├── sources.yaml                 # Active/local source dataset configuration override
├── pyproject.toml               # Modern PEP 517/621 package metadata
├── LICENSE                      # Apache-2.0 License
├── CITATION.cff                 # Citation metadata
└── README.md                    # This document
```

---

## ⚡ TL;DR: Production Run

```bash
# 1. Install & verify
pip install -e .

# 2. Download and prepare standardized 1°x1° sources (~2 min)
pisces-inidata download --pack ece4 --prepare

# 3. Produce inidata for eORCA1 (parallel Slurm batch jobs or local)
pisces-inidata produce --grid eORCA1 --pack ece4

# 4. Verify outputs
pisces-inidata verify --grid eORCA1
```

All 15 target NetCDF files will be ready in:
`${PISCES_WORKSPACE}/grids/${GRID_NAME}/inidata/`

> **Note on HPC Clusters:** Ensure `cdo`, `nco`, and `python` are available (`module load CDO NCO python` or via conda). Cluster accounts, partitions, and scratch paths are abstracted in `platforms.yaml` (bundled in `pisces_inidata/config/platforms.yaml`).

---

## Quickstart

### 1. Installation

Prerequisites: Linux, CDO ($\ge 2.0$), NCO, Python ($\ge 3.10$).

```bash
git clone https://github.com/vlap/pisces-inidata.git
cd pisces-inidata
pip install -e .
```

Verify your installation, active configuration, target grids, and HPC platforms in one command:
```bash
pisces-inidata info
```

### 2. Configure Sources & Packs (`sources.yaml`)

Choose a curated configuration pack or customize per-tracer sources:
- **`ece4`** *(Default)*: Modern observational climatologies for **EC-Earth4** (WOA23, GLODAPv2.2016b, Panaïotis DOC).
- **`ece3`**: Baseline observational sources originally used in **EC-Earth3** (WOA2009, GLODAPv1.1, Hansell DOC).
- **`official_sette`**: Official regular unmasked **NEMO/PISCES SETTE** reference fields (all vars from SETTE, pure interpolation).

Switch packs in `sources.yaml` (`pack: ece4`), load from `packs/`, or pass `--pack` (with `--preset` supported as an alias):
```bash
# Preview configuration for a pack:
pisces-inidata info --pack ece3

# Or export bash environment variables:
pisces-inidata config --pack ece3 --export
```

### 3. Download Raw Datasets
Fetch only the active datasets selected in `sources.yaml`:
```bash
# Download and immediately prepare Stage 1 standardized regular files:
pisces-inidata download --prepare

# Or dry-run preview:
pisces-inidata download --dry-run
```

### 4. Generate Initial Conditions
The pipeline cleanly decouples **Stage 1 (Source Standardization)** from **Stage 2 (Target Remapping)**:
```bash
# End-to-end production for eORCA1 (or ORCA2, eORCA025):
pisces-inidata produce --grid eORCA1

# Or for arbitrary grids with custom domain:
pisces-inidata produce --grid eORCA1 --domain-dir /path/to/nemo/domain

# Prepare Stage 1 regular standardized sources only (cached and shared across grids):
pisces-inidata prepare-sources

# Remap specific or all components to target grid:
pisces-inidata remap all --grid eORCA1
```
*(Note: `--orca <NAME>` is fully supported as an alias for `--grid <NAME>`.)*

### 5. Inspect & Verify Outputs
Inspect generated NetCDF files, verify shapes, and guarantee no blank/all-zero/NaN outputs:
```bash
pisces-inidata verify --grid eORCA025
```

### 6. Validate Against Reference
```bash
# Statistical validation against SETTE ORCA2 reference:
pisces-inidata validate --pack official_sette

# Or reproduction verification against EC-Earth3 baseline on eORCA1:
pisces-inidata test-reproduction --pack official_sette
```

---

## HPC Execution Workflow (BSC Hub04 & Nord4)

On high-performance computing clusters where compute nodes lack direct internet access (such as BSC Nord4 / MareNostrum 5), data preparation and remapping are decoupled across machines:

1. **Ingestion & Source Standardization (Interactive Node: `hub04`):**
   Formatting raw sources into regular NetCDF climatologies takes only 1–2 minutes and is executed directly on `hub04` alongside the download:
   ```bash
   ssh hub04
   cd /gpfs/scratch/bsc32/${USER}/pisces-inidata

   # Download raw sources and automatically standardize in one shot:
   pisces-inidata download --prepare
   ```
   *Standardized regular source files (`std_*.nc`) are cached in `${STANDARDIZED_DIR}` on the shared scratch filesystem and reused across all target grids.*

2. **Parallel Remapping via Slurm (Batch Node: `nord4`):**
   Batch compute nodes perform only pure interpolation to target curvilinear grids without data formatting overhead:
   ```bash
   ssh nord4
   cd /gpfs/scratch/bsc32/${USER}/pisces-inidata

   # Submit batch remapping for eORCA1:
   pisces-inidata produce --grid eORCA1

   # Submit batch remapping for eORCA025:
   pisces-inidata produce --grid eORCA025

   # Inspect and verify all 15 output products:
   pisces-inidata verify --grid eORCA025
   ```

3. **Storage Hierarchy & Nord4 Guidelines:**
   - **Unified Workspace (`PISCES_WORKSPACE`):** Defaults to `/gpfs/scratch/bsc32/${USER}/pisces_inidata` or `/esarchive/scratch/${USER}/pisces_inidata`.
     - `shared/raw/`: Downloaded observational archives.
     - `shared/standardized/<pack>/`: Stage 1 regular $1^\circ \times 1^\circ$ standardized NetCDFs.
     - `grids/<grid>/`: Target mesh products (`weights/`, `inidata/`, `jobs/`, `logs/`).
   - **Node-Local Scratch (`$TMPDIR`):** On Nord4/MN5 compute nodes, `$TMPDIR` points to `/scratch/tmp/$SLURM_JOB_ID` (local NVMe SSD). All intermediate CDO pipeline operations execute on local NVMe and are automatically cleaned on job termination, keeping GPFS free of temporary files. System `/tmp` is strictly avoided per BSC acceptable use policy.

---

## Documentation

Full documentation is hosted on **Read the Docs**:  
[**https://pisces-inidata.readthedocs.io/en/latest/**](https://pisces-inidata.readthedocs.io/en/latest/)

- [Primary Observational Data Sources](docs/products.md)
- [Configuration Reference (`sources.yaml`)](docs/configuration.md)
- [Validation Suites & Diagnostic Scorecards](docs/validation.md)

---

## Citation

If you use `pisces-inidata` in your work, please cite:

```bibtex
@software{lapin_pisces_inidata_2026,
  author       = {Vladimir Lapin},
  title        = {pisces-inidata: Global Biogeochemical Initial Conditions Generator for PISCES and EC-Earth4},
  year         = {2026},
  publisher    = {GitHub},
  journal      = {GitHub repository},
  howpublished = {\url{https://github.com/vlap/pisces-inidata}}
}
```

---

## License

This project is licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.
