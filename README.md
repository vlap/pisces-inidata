# PISCES Inidata Processing Tool (`pisces-inidata`)

[![CI](https://github.com/vlap/pisces-inidata/actions/workflows/ci.yml/badge.svg)](https://github.com/vlap/pisces-inidata/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/pisces-inidata/badge/?version=latest)](https://pisces-inidata.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)

A generic, modular, and reproducible tool to generate, interpolate, and validate **PISCES** biogeochemical initial condition and boundary forcing files (`inidata`) for any **NEMO** ocean grid (`ORCA2`, `eORCA1`, `eORCA025`).

Built for **EC-Earth4** and the broader ocean modeling community.

---

## Key Features

- **Per-Variable Product Selection:** Choose observational, reanalysis, or model products independently for each tracer via `products.cfg`.
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
├── python/                      # Python library and CLI package
│   └── pisces_inidata/
│       ├── __init__.py
│       ├── cli.py               # CLI: pisces-inidata (check, run, validate, pad, ...)
│       ├── check.py             # Pre-flight system & data integrity verifier
│       ├── config.py            # Configuration parser & validator
│       ├── padding.py           # Abyssal depth padding algorithm
│       ├── woa23.py             # WOA23 12-month depth profile builder
│       ├── doc.py               # Panaïotis et al. (2024) DOC NetCDF generator
│       ├── scoreboard.py        # Validation scoreboard generator
│       ├── reproduction.py      # EC-Earth3 baseline precision benchmark
│       └── utils.py             # NetCDF inspection & FAIR metadata stamping
├── scripts/                     # Modular Bash execution pipeline
│   ├── config.sh                # Environment, paths, and module configuration
│   ├── download_sources.sh      # Automated raw dataset downloader
│   ├── gen_grid_and_weights.sh  # Grid description and CDO remapping weights
│   ├── format_tracers_3d.sh     # 3D tracers formatting and interpolation
│   ├── format_surface_forcings.sh # Atmospheric dust, N-dep, PAR forcings
│   ├── format_bathy_hydrofe.sh  # Bathymetric shelf factor & hydrothermal iron
│   ├── format_rivers.sh         # River nutrient discharge
│   ├── launcher_pisces_inidata.sh # End-to-end master pipeline driver
│   └── run_validation_suite.sh  # Automated validation suite
├── tests/                       # Unit tests (pytest)
├── products.cfg                 # Per-variable product configuration
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

### 2. Download Data
```bash
bash scripts/download_sources.sh
```

### 3. Generate Initial Conditions
```bash
pisces-inidata run --orca ORCA2
```

### 4. Validate Against SETTE Reference
```bash
pisces-inidata validate
```

View the generated validation metrics in `VALIDATION_SCOREBOARD_ORCA2.md`.

---

## Documentation

Full documentation is hosted on **Read the Docs**:  
👉 [**https://pisces-inidata.readthedocs.io/en/latest/**](https://pisces-inidata.readthedocs.io/en/latest/)

- [Quickstart Guide](docs/quickstart.md)
- [Pipeline Architecture](docs/architecture.md)
- [Supported Products Catalog](docs/products.md)
- [Gridded vs. Discrete Data Guide](docs/gridded_vs_discrete.md)
- [Configuration Reference](docs/configuration.md)
- [HPC Execution (BSC MareNostrum 5 / Nord3)](docs/hpc_execution.md)
- [Validation Scoreboard & Metrics](docs/validation.md)
- [API & CLI Reference](docs/api.md)

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
