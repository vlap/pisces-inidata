# Gridded vs. Discrete Ocean Data Guide

A foundational concept in ocean modeling initial conditions is the distinction between **discrete observational compilations** and **gridded continuous climatologies**.

---

## 1. Discrete Cruise & Bottle Observations

### What They Are
Datasets such as `GLODAPv3_Merged_Master_File.nc` or `GLODAPv2.2023_Merged_Master_File.nc` represent **discrete in situ measurements**.
- Each record corresponds to a specific water sample collected from a CTD/Rosette bottle at a discrete latitude, longitude, depth, and timestamp during a research cruise.
- GLODAPv3 aggregates over **1.5 million discrete bottle samples** from 1,181 cruises spanning 1972 to 2026.

```
Cruise Track Observation (Non-Gridded):
Cruise A: (lon_1, lat_1, z_1) -> DIC = 2150.2 umol/kg
Cruise A: (lon_1, lat_1, z_2) -> DIC = 2210.5 umol/kg
... (Sparse tracks separated by hundreds of nautical miles of empty ocean)
```

### Why Ocean Models Cannot Directly Ingest Master Files
Ocean circulation and biogeochemical models (NEMO, PISCES) solve discretized 3D partial differential equations over structured or unstructured meshes. They require:
1. Every interior wet ocean cell $(i, j, k)$ to have an initial numerical state.
2. Complete spatial coverage without data holes or missing ocean sectors.

If a discrete bottle file were directly interpolated onto a model grid without objective analysis, 98% of the model grid cells would evaluate to `NaN` (no sample was taken in that specific grid box).

---

## 2. Gridded Objective Analyses & Climatologies

To transform discrete measurements into continuous 3D fields, scientific synthesis teams apply **objective mapping** or **machine-learning kriging**:

1. **Objective Analysis / Optimal Interpolation (e.g. DIVAnd, Barnes analysis):**
   - Correlated covariance functions and physical bathymetric barriers (preventing interpolation across landmasses or ridges) are used to weight and smooth measurements onto a regular $1^\circ \times 1^\circ$ grid across 33 standard depths.
   - **GLODAPv2.2016b Mapped Climatology** (Lauvset et al. 2016) is the official 3D objectively mapped product created by the GLODAP consortium.
2. **Machine-Learning Supervised Climatologies:**
   - E.g., **Panaïotis et al. (2024)** for DOC. Neural networks or random forests are trained to predict chemical concentrations from co-located physical predictors (temperature, salinity, density, oxygen, nutrients) available globally at high density.
3. **Copernicus Marine Service (CMEMS):**
   - Products like `INSITU_GLO_BGC_CARBON_DISCRETE_MY_013_050` provide access to both discrete observations and the derived binned/gridded climatologies.
   - CMEMS is transitioning its carbon distribution to `INSITU_GLO_BGC_DISCRETE_MY_013_046` and pointing users to official host repositories (NOAA NCEI OCADS and GLODAP.info) for 3D mapped NetCDF files.

---

## 3. How `pisces-inidata` Resolves and Extrapolates Data

```
┌────────────────────────────────────────────────────────┐
│ 1. Start with Standard 3D Gridded Climatology           │
│    (GLODAPv2.2016b, WOA23, Panaïotis 2024 DOC)        │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. Vertical Abyssal Bracketing (pad_abyssal_depth)     │
│    Extend 5500m bottom level to 6000m depth            │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. CDO Bilinear Remapping to Tripolar NEMO Mesh        │
│    Maps regular 1°x1° to ORCA curvilinear coordinates  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 4. Coastal Land-Sea Gap Filling (setmisstonn)          │
│    Floods narrow straits and coastlines via NN search  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 5. Model Mask Application                              │
│    Strictly zeros out land cells using mesh_mask.nc    │
└────────────────────────────────────────────────────────┘
```

By strictly consuming continuous gridded products at Stage 1, `pisces-inidata` ensures:
- Full global conservation and physical consistency.
- Zero spurious missing values or uninitialized ocean boxes.
- Reproducibility across multiple grid resolutions (ORCA2, eORCA1, eORCA025).
