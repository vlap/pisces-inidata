# Pipeline Architecture & Methodology

The `pisces-inidata` pipeline is organized as a decoupled, modular sequence of processing stages. Each stage has distinct responsibilities, fail-fast validation checks, and clear intermediate NetCDF representations.

```
 Stage 1: Download & Preprocessing
   ├── Fetch WOA23, GLODAP, DOC, etc.
   └── Standardize dimensions, coordinate names, and units
       │
 Stage 2: Target Grid Description & Weights
   ├── Extract target grid from NEMO mesh_mask or coordinates
   └── Generate CDO bilinear remapping weights (SCRIP format)
       │
 Stage 3: Abyssal Vertical Padding
   ├── Detect vertical depth coordinate
   └── Replicate surface (0m) and deepest level (6000m)
       │
 Stage 4: Horizontal & Vertical Remapping
   ├── CDO remap (bilinear horizontal interpolation)
   └── CDO intlevel (1D conservative vertical interpolation to NEMO levels)
       │
 Stage 5: Coastal Land-Sea Gap Filling
   ├── CDO setmisstonn (nearest-neighbor extrapolation across coastline)
   └── Apply target ocean land-sea mask
```

---

## Detailed Processing Stages

### Stage 1: Raw Data Ingestion & Standardization
Raw ocean observations arrive in heterogeneous coordinate conventions (e.g. `depth_surface`, `Depth`, `z`, differing units like $\mu\text{mol/kg}$ vs $\mu\text{mol/L}$).
- In this stage, data is converted into SI or standard PISCES units (e.g. converting DOC from $\mu\text{mol/kg}$ to $\mu\text{mol C/L}$ using local seawater density calculated via TEOS-10 or standard ocean density $\rho_0 \approx 1025\,\text{kg/m}^3$).
- Coordinate variables are standardized to `lon`, `lat`, and `depth`.

### Stage 2: Grid Generation & Weight Computation
NEMO ocean models operate on curvilinear, tripolar grids (such as the ORCA family).
- `scripts/gen_grid_and_weights.sh` uses CDO to generate a SCRIP-format grid description from the model's `coordinates.nc` and `mesh_mask.nc`.
- Bilinear interpolation weights (`weights_*.nc`) are precomputed once using `cdo genbil`, dramatically accelerating subsequent tracer remapping.

### Stage 3: Abyssal Depth Bracketing (`pisces_inidata.padding`)
Standard observational products typically terminate at 5500m depth, whereas deep ocean trenches and abyssal plains in NEMO L75 or L121 configurations reach depths between 5900m and 6000m.
If vertical interpolation (`cdo intlevel`) is performed without depth bracketing, all cells below 5500m will evaluate to missing values (`_FillValue`).
- `pisces_inidata.padding` evaluates the input vertical coordinates.
- If the shallowest level is $> 0\text{m}$, level 0 is added by replicating the surface layer.
- If the deepest level is $< 6000\text{m}$, level 6000m is appended by replicating the deepest valid layer.
- This guarantees stable extrapolation to abyssal waters while respecting abyssal homogeneity.

### Stage 4: 3D Horizontal & Vertical Remapping
- **Horizontal Remapping:** Performed using `cdo remap,target_grid,weights_file`.
- **Vertical Remapping:** Performed using `cdo intlevel,target_depths.txt`, mapping observational depths onto the NEMO target depths (`nav_lev` / $gdept$).

### Stage 5: Coastal Gap Filling & Mask Application
Because coastal bathymetry in model resolution (e.g. ORCA2, eORCA1) diverges from the $1^\circ \times 1^\circ$ observational land-sea mask, narrow straits, fjords, and shelves would otherwise exhibit missing values.
- `cdo setmisstonn` performs nearest-neighbor search to flood missing values from adjacent ocean waters.
- The official target ocean mask (`tmask` from `mesh_mask.nc`) is subsequently multiplied to ensure dry land cells remain masked to zero.

### Stage 6: Scientific Provenance & FAIR Metadata Stamping
Every generated initial condition and boundary forcing NetCDF file is automatically stamped with standardized CF global attributes via `stamp_provenance`:
- `title`: Target grid description (`NEMO/EC-Earth4 (${GRID_NAME})`).
- `source_pipeline`: Tool version and repository URL (`pisces-inidata`).
- `source_products`: Exact breakdown of selected input products (`NO3:woa23, TALK:glodap_v2_2016b, DOC:panaiotis2024, ...`).
- `git_commit`: Specific commit hash that generated the file.
- `generation_timestamp`: ISO 8601 UTC timestamp.
- `institution`: Barcelona Supercomputing Center (BSC), EC-Earth Consortium.
- `license`: Apache-2.0.

This guarantees complete traceability and scientific reproducibility for long-term EC-Earth4 climate simulations.
