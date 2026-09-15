# Quickstart Guide

This guide will walk you through installing `pisces-inidata` and generating a full set of PISCES initial conditions on ORCA2.

## Prerequisites
Ensure the following tools are available on your system:
- **Linux Environment** (Ubuntu, Debian, RHEL, CentOS, SUSE)
- **CDO** (Climate Data Operators, $\ge 2.0.0$)
- **NCO** (netCDF Operators: `ncks`, `ncrename`, `ncatted`)
- **Python** ($\ge 3.10$) with `pip`

On Ubuntu/Debian, install system dependencies via:
```bash
sudo apt-get update
sudo apt-get install -y cdo nco python3 python3-pip
```

## Installation

Clone the repository and install `pisces-inidata` in editable development mode:
```bash
git clone https://github.com/vlap/pisces-inidata.git
cd pisces-inidata
pip install -e .
```

Verify the installation and review default configuration:
```bash
pisces-inidata info
```

## Running the Pipeline

### 1. Configure Products
Inspect or edit `products.cfg` to select your preferred observational datasets for each tracer:
```bash
# Example: Select WOA23 for nutrients and Panaïotis 2024 for DOC
export PRODUCT_NO3="woa23"
export PRODUCT_PO4="woa23"
export PRODUCT_Si="woa23"
export PRODUCT_O2="woa23"
export PRODUCT_DOC="panaiotis2024"
export PRODUCT_TALK="glodap_v2_2016b"
export PRODUCT_TDIC="glodap_v2_2016b"
```

### 2. Download Raw Datasets
Run the automated downloader to fetch required raw datasets:
```bash
bash scripts/download_sources.sh
```

### 3. Generate Initial Conditions
Target ocean domain files (`domain_cfg.nc` and `maskutil.nc`) define the target NEMO curvilinear grid.
- **On BSC clusters:** Pre-installed domain files are automatically detected.
- **On external machines:** Download the official EC-Earth4 inidata package and point to it using `--domain-dir`:
  ```bash
  pisces-inidata run --orca ORCA2 --domain-dir /path/to/nemo/domain
  ```
  *(For instructions on obtaining official EC-Earth4 inidata, refer to the [EC-Earth4 Documentation](https://ec-earth-4-docs.readthedocs.io/).)*

The formatted NetCDF files will be saved in:
```
work_orca2/
├── inidata_3d_tracers_orca2.nc
├── surface_dust_forcing_orca2.nc
├── surface_ndep_forcing_orca2.nc
├── surface_par_forcing_orca2.nc
├── coastal_bathy_forcing_orca2.nc
├── hydrothermal_fe_forcing_orca2.nc
└── river_fluxes_forcing_orca2.nc
```

### 4. Run Statistical Validation
Evaluate the generated files against the official SETTE ORCA2 reference:
```bash
pisces-inidata validate
# Alternatively:
# bash scripts/run_validation_suite.sh
```

This generates `VALIDATION_SCOREBOARD_ORCA2.md` containing correlation, RMSE, NRMSE, and bias diagnostics across all 15 PISCES tracers and forcings.
