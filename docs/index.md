# PISCES Inidata Documentation

**Global Biogeochemical Initial Conditions Generator for PISCES and EC-Earth4**

`pisces-inidata` is an open-source, modular, and fully reproducible pipeline designed to generate 3D ocean biogeochemical initial condition fields and boundary forcings for the **PISCES** biogeochemical model (integrated within **NEMO** and **EC-Earth4**).

The pipeline interpolates global observational and reanalysis climatologies (e.g. World Ocean Atlas 2023, GLODAP, Panaïotis et al. 2024 DOC, atmospheric deposition, and riverine nutrient fluxes) onto arbitrary tripolar NEMO grids (ORCA2, eORCA1, eORCA025), pads abyssal depth boundaries, fills coastal land-sea mask gaps, and evaluates quality metrics against official references.

```
                    ┌─────────────────────────┐
                    │ Raw Climatologies / Obs │
                    │ (WOA23, GLODAP, DOC, …) │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Abyssal Padding (6000m) │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Horizontal & Vertical   │
                    │ CDO/NCO Interpolation   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Coastal Fill & Masking  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Target NEMO Inidata     │
                    │ + Diagnostic Scoreboard │
                    └─────────────────────────┘
```

```{toctree}
:maxdepth: 2
:caption: User Guide

quickstart
architecture
products
gridded_vs_discrete
configuration
hpc_execution
validation
api
```

## Key Highlights
- **EC-Earth4 Open Source Ready:** Standalone, clean Python and Bash codebase with zero private dependencies.
- **Per-Variable Product Selection:** Configure independent datasets for each tracer (`NO3`, `PO4`, `Si`, `O2`, `TALK`, `TDIC`, `PiDIC`, `DOC`, `Fer`, dust, N-deposition, PAR, bathymetry, hydrothermal Fe, rivers) via `products.cfg`.
- **Modern Observational Data Ingestion:** Supports latest World Ocean Atlas (WOA23), GLODAP (v2.2016b, v2.2023, v3), and state-of-the-art machine-learning dissolved organic carbon (Panaïotis et al. 2024, SEANOE).
- **Abyssal Bracketing:** Automatically extends 5500m data down to 6000m abyssal depth, preventing missing ocean values when interpolating to deep NEMO vertical levels (L75, L121).
- **Automated Closeness & Diagnostic Scoreboard:** Computes Pearson $r$, Spearman $\rho$, RMSE, NRMSE, and Mean Bias across all valid ocean cells against official SETTE ORCA2 references.

## Citation
If you use `pisces-inidata` in your scientific studies or climate simulations, please cite:
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
