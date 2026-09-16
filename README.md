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
├── presets/                     # Curated source configuration presets
│   ├── sources_ece4.yaml        # Modern observational climatologies for EC-Earth4 [Default]
│   ├── sources_ece3.yaml        # Baseline observational sources originally used in EC-Earth3
│   └── sources_official_sette.yaml # Official regular unmasked NEMO/PISCES SETTE reference
├── python/                      # Python library and CLI package
│   └── pisces_inidata/
│       ├── __init__.py
│       ├── cli.py               # CLI: pisces-inidata (check, download, run, validate, ...)
│       ├── check.py             # Pre-flight system & data integrity verifier
│       ├── config.py            # Configuration parser & validator (sources.yaml, presets)
│       ├── download.py          # Selective raw dataset downloader & staging
│       ├── glodap.py            # GLODAP vertical coordinate standardizer & padder
│       ├── padding.py           # Abyssal depth padding algorithm (up to 6000m)
│       ├── woa23.py             # WOA23 12-month depth profile builder
│       ├── doc.py               # Panaïotis et al. (2024) DOC NetCDF generator
│       ├── scoreboard.py        # Validation scoreboard generator
│       └── reproduction.py      # EC-Earth3 baseline precision benchmark
├── scripts/                     # Modular Bash execution pipeline
│   ├── config.sh                # Environment, paths, and module configuration
│   ├── download_sources.sh      # Thin wrapper calling pisces-inidata download
│   ├── gen_grid_and_weights.sh  # Grid description and CDO remapping weights
│   ├── format_tracers_3d.sh     # 3D tracers formatting and interpolation
│   ├── format_surface_forcings.sh # Atmospheric dust, N-dep, PAR forcings
│   ├── format_bathy_hydrofe.sh  # Bathymetric shelf factor & hydrothermal iron
│   ├── format_rivers.sh         # Mass-conserving river nutrient discharge
│   ├── launcher_pisces_inidata.sh # End-to-end Slurm master pipeline driver
│   ├── run_validation_suite.sh  # Automated validation suite
│   └── verify_outputs.py        # Output files integrity & statistical bounds checker
├── tests/                       # Unit tests (pytest)
├── sources.yaml                 # Active source dataset configuration (preset: ece4)
├── pyproject.toml               # Modern PEP 517/621 package metadata
├── LICENSE                      # Apache-2.0 License
├── CITATION.cff                 # Citation metadata
└── README.md                    # This document
```

---

## Quickstart

### 1. Installation

Prerequisites: Linux, CDO ($\ge 2.0$), NCO, Python ($\ge 3.10$).

```bash
git clone https://github.com/vlap/pisces-inidata.git
cd pisces-inidata
pip install -e .
```

Verify your installation:
```bash
pisces-inidata info
```

### 2. Configure Sources & Presets (`sources.yaml`)

Choose a curated configuration preset or customize per-tracer sources:
- **`ece4`** *(Default)*: Modern observational climatologies for **EC-Earth4** (WOA23, GLODAPv2.2016b, Panaïotis DOC).
- **`ece3`**: Baseline observational sources originally used in **EC-Earth3** (WOA2009, GLODAPv1.1, Hansell DOC).
- **`official_sette`**: Official regular unmasked **NEMO/PISCES SETTE** reference fields (all vars from SETTE, pure interpolation).

Switch presets in `sources.yaml` (`preset: ece4`), load from `presets/`, or pass `--preset`:
```bash
# Preview configuration for a preset:
pisces-inidata info --preset ece3

# Or export bash environment variables:
pisces-inidata config --preset ece3 --export
```

### 3. Download Raw Datasets
Fetch only the active datasets selected in `sources.yaml`:
```bash
# Using the CLI:
pisces-inidata download

# Or dry-run preview:
pisces-inidata download --dry-run
```

### 4. Generate Initial Conditions
```bash
# Generate for ORCA2:
pisces-inidata run --orca ORCA2

# Or for arbitrary grids (eORCA1, eORCA025) with custom domain:
pisces-inidata run --orca eORCA1 --domain-dir /path/to/nemo/domain
```

### 5. Validate Against Reference
```bash
# Statistical validation against SETTE ORCA2 reference:
pisces-inidata validate --preset official_sette

# Or reproduction verification against EC-Earth3 baseline on eORCA1:
pisces-inidata test-reproduction --preset official_sette
```

---

## HPC Execution Workflow (BSC Hub04 & Nord4)

On high-performance computing clusters where compute nodes lack direct internet access (such as BSC Nord4 / MareNostrum 5):

1. **Dataset Ingestion (Interactive / Internet Node: `hub04`):**
   ```bash
   ssh hub04
   cd /esarchive/scratch/${USER}/scripts/pisces_inidata
   pisces-inidata download
   ```
2. **Parallel Generation via Slurm (Batch Node: `nord4`):**
   ```bash
   ssh nord4
   cd /esarchive/scratch/${USER}/scripts/pisces_inidata

   # Submit batch generation for eORCA1:
   ./scripts/launcher_pisces_inidata.sh submit

   # Submit batch generation for eORCA025:
   GRID_NAME=eORCA025 ./scripts/launcher_pisces_inidata.sh submit
   ```

---

## Documentation

Full documentation is hosted on **Read the Docs**:  
👉 [**https://pisces-inidata.readthedocs.io/en/latest/**](https://pisces-inidata.readthedocs.io/en/latest/)

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
