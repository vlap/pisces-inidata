# PISCES Inidata Documentation

**Global Biogeochemical Initial Conditions Generator for PISCES & EC-Earth4**

`pisces-inidata` is an open-source, reproducible pipeline designed to generate 3D ocean biogeochemical initial conditions and surface boundary forcings for the **PISCES** biogeochemical model (coupled within **NEMO** and **EC-Earth4**).

The pipeline interpolates global observational climatologies (World Ocean Atlas 2023, GLODAPv2.2016b, Panaïotis et al. 2024 DOC, atmospheric deposition, and riverine nutrient fluxes) onto arbitrary curvilinear NEMO grids (`ORCA2`, `eORCA1`, `eORCA025`, `eORCA12`, or custom grids via `grids.yaml`), pads abyssal depth boundaries, fills coastal land-sea mask gaps, and evaluates quality metrics against official references.

```
Raw Climatologies (WOA23, GLODAP, DOC, …)
                  │
                  ▼
       Abyssal Padding (6000m)
                  │
                  ▼
  Horizontal & Vertical Remapping (CDO)
                  │
                  ▼
     Coastal NN Flood Fill & Masking
                  │
                  ▼
     Target NEMO Inidata (NetCDF-4)
         + Validation Scorecard
```

## TL;DR: Generate Inidata in 2 Steps

For users with access to BSC machines (or any HPC cluster), producing inidata takes two commands:

1. **On `hub04` (interactive node with internet access):**
   ```bash
   pisces-inidata download --preset ece4 --prepare
   ```
2. **On `nord4` (batch Slurm cluster):**
   ```bash
   pisces-inidata produce --grid eORCA1
   # Or for high-res eORCA025:
   pisces-inidata produce --grid eORCA025
   ```

All 15 target NetCDF files will be ready in `${PISCES_WORKSPACE}/grids/${GRID_NAME}/inidata/`.

See the complete [Quickstart & TL;DR Guide](quickstart.md) for full details, local workstation instructions, and target grid options.

```{toctree}
:maxdepth: 2
:caption: User Guide

quickstart
configuration
products
validation
```

---

## Standalone Quickstart

### 1. Prerequisites & Installation
Prerequisites: Linux, CDO ($\ge 2.0$), NCO, Python ($\ge 3.10$).

```bash
git clone https://github.com/vlap/pisces-inidata.git
cd pisces-inidata
pip install -e .
```

### 2. Pre-Flight Verification
Verify required binaries (CDO, NCO), Python dependencies, domain files, and disk space:
```bash
pisces-inidata check --grid ORCA2
```

### 3. Configure & Execute Pipeline
Select preferred source products in `sources.yaml` (or override via environment variables), then run:
```bash
# Generate inidata on ORCA2 (or eORCA1, eORCA025)
pisces-inidata run --grid ORCA2 --domain-dir /path/to/nemo/domain
```

### 4. Verify & Validate
Inspect generated NetCDF files for complete ocean coverage, then validate against references:
```bash
# Ensure no blank/NaN variables:
pisces-inidata verify --grid ORCA2

# Statistical validation against SETTE ORCA2 reference:
pisces-inidata validate
```

---

## Citation

If you use `pisces-inidata` in climate simulations or scientific publications, please cite:

```bibtex
@software{lapin_pisces_inidata_2026,
  author       = {Vladimir Lapin},
  title        = {pisces-inidata: Global Biogeochemical Initial Conditions Generator for PISCES and EC-Earth4},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/vlap/pisces-inidata}
}
```
