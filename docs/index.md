# PISCES Inidata Documentation

**Global Biogeochemical Initial Conditions Generator for PISCES & EC-Earth4**

`pisces-inidata` is an open-source, reproducible pipeline designed to generate 3D ocean biogeochemical initial conditions and surface boundary forcings for the **PISCES** biogeochemical model (coupled within **NEMO** and **EC-Earth4**).

The pipeline interpolates global observational climatologies (World Ocean Atlas 2023, GLODAPv2.2016b, Panaïotis et al. 2024 DOC, atmospheric deposition, and riverine nutrient fluxes) onto arbitrary curvilinear NEMO grids (`ORCA2`, `eORCA1`, `eORCA025`), pads abyssal depth boundaries, fills coastal land-sea mask gaps, and evaluates quality metrics against official references.

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

```{toctree}
:maxdepth: 2
:caption: Documentation

products
configuration
validation
```

---

## Quickstart

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
pisces-inidata check --orca ORCA2
```

### 3. Configure & Execute Pipeline
Select preferred source products in `sources.yaml` (or override via environment variables), then run:
```bash
# Generate inidata on ORCA2 (or eORCA1, eORCA025)
pisces-inidata run --orca ORCA2 --domain-dir /path/to/nemo/domain
```

### 4. Statistical Validation
Verify generated fields against official NEMO/SETTE ORCA2 references to ensure correct units and physical bounds:
```bash
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
