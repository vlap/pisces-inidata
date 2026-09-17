# Configuration & CLI Reference

`pisces-inidata` provides a transparent, declarative configuration system through inidata packs (`ece4`, `ece3`, `official_sette`), `sources.yaml`, and a unified command-line interface.

---

## 1. Configuration Packs (Inidata Packs)

Instead of selecting sources variable-by-variable, users can choose curated configuration packs designed for specific modeling purposes:

| Pack | Purpose | Nutrients & Oxygen | Carbon Chemistry | DOC | Iron & Boundary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ece4`** *(Default)* | Modern observational datasets for **EC-Earth4** production runs | WOA23 (102 levels) | GLODAPv2.2016b | Panaïotis et al. 2024 (ML) | Tagliabue (2012) & SETTE |
| **`ece3`** | Observational sources originally used in **EC-Earth3** (baseline reproduction) | WOA2009 | GLODAPv1.1 | Hansell (2009) | Tagliabue (2012) & SETTE |
| **`official_sette`** | Official regular unmasked **NEMO/PISCES SETTE** reference (all vars from SETTE, pure interpolation) | `sette_nomask` | `sette_nomask` | `sette_nomask` | `sette_nomask` & `sette_orca2` |
| **`<custom>`** | Any user-defined pack name (e.g. `my_experiment`) inheriting from `base_pack` | Configurable | Configurable | Configurable | Configurable |

Packs can be configured in multiple ways:

1. **In `sources.yaml` (Built-in or Custom):**
   ```yaml
   pack: my_experiment
   base_pack: ece4  # Inherits unspecified defaults from ece4 (legacy alias: base_preset)

   tracers_3d:
     DOC: sette_nomask     # Override Hansell 2009 baseline
     TALK: glodap_v2_2023  # Test modern GLODAP release
   ```
   Each pack isolates its Stage 1 standardized files into its own directory:
   `${WORKSPACE}/shared/standardized/${PACK}/`
   preventing cache collisions with standard baselines.

2. **Via dedicated pack files:**
   Place custom pack templates directly in `packs/sources_<name>.yaml`:
   - `packs/sources_ece4.yaml`
   - `packs/sources_ece3.yaml`
   - `packs/sources_official_sette.yaml`
   - `packs/sources_my_experiment.yaml`

   And invoke by name:
   ```bash
   pisces-inidata prepare-sources --pack my_experiment
   pisces-inidata remap all --pack my_experiment --grid eORCA1
   ```

3. **Via explicit `--config` flag:**
   Point any command directly to a standalone YAML configuration:
   ```bash
   pisces-inidata prepare-sources --config path/to/my_sources.yaml
   pisces-inidata remap all --config path/to/my_sources.yaml --grid eORCA1
   ```

4. **Via CLI `--pack` (or `--preset` alias) / `INIDATA_PACK` environment variable:**
   ```bash
   pisces-inidata info --pack ece3
   pisces-inidata produce --grid eORCA1 --pack my_experiment
   pisces-inidata config --pack official_sette --export
   ```
   *(Note: `--preset` and `INIDATA_PRESET` / `PRESET` are retained as fully backward-compatible aliases).*

---

## 2. Observational Source Configuration (`sources.yaml`)

Individual observational source datasets can be customized on top of any pack in `sources.yaml`. Explicit variable entries in the file or environment variables (`PRODUCT_*`) override the pack defaults:

```bash
# Example overrides:
export PRODUCT_NO3="woa23"
export PRODUCT_TALK="glodap_v2_2016b"
export PRODUCT_DOC="panaiotis2024"
```

> [!IMPORTANT]
> **EC-Earth3 Inidata is strictly a verification benchmark:**
> EC-Earth3 inidata cannot be selected as an input source for generating inidata. Inidata generation must proceed from primary observational climatologies. EC-Earth3 inidata is reserved exclusively as reference ground truth in the pipeline reproduction test (`pisces-inidata test-reproduction`).

### 3D Biogeochemical Tracers

| Variable | Environment Variable | Supported Options | Default |
| :--- | :--- | :--- | :--- |
| Nitrate ($\text{NO}_3$) | `PRODUCT_NO3` | `woa23`, `woa2009`, `sette_nomask` | `woa23` |
| Phosphate ($\text{PO}_4$) | `PRODUCT_PO4` | `woa23`, `woa2009`, `sette_nomask` | `woa23` |
| Silicate ($\text{Si}$) | `PRODUCT_Si` | `woa23`, `woa2009`, `sette_nomask` | `woa23` |
| Dissolved Oxygen ($\text{O}_2$) | `PRODUCT_O2` | `woa23`, `woa2009`, `sette_nomask` | `woa23` |
| Total Alkalinity ($\text{TALK}$) | `PRODUCT_TALK` | `glodap_v2_2016b`, `glodap_v2_2023`, `glodap_v1`, `sette_nomask` | `glodap_v2_2016b` |
| Total Dissolved Inorganic Carbon ($\text{TDIC}$) | `PRODUCT_TDIC` | `glodap_v2_2016b`, `glodap_v2_2023`, `glodap_v1`, `sette_nomask` | `glodap_v2_2016b` |
| Pre-Industrial DIC ($\text{PiDIC}$) | `PRODUCT_PiDIC` | `glodap_v2_2016b`, `glodap_v2_2023`, `glodap_v1`, `sette_nomask` | `glodap_v2_2016b` |
| Dissolved Organic Carbon ($\text{DOC}$) | `PRODUCT_DOC` | `panaiotis2024`, `sette_nomask` | `panaiotis2024` |
| Dissolved Iron ($\text{Fer}$) | `PRODUCT_Fer` | `sette_nomask` | `sette_nomask` |

### Surface & Boundary Forcings

| Forcing | Environment Variable | Supported Options | Default |
| :--- | :--- | :--- | :--- |
| Atmospheric Dust | `PRODUCT_DUST` | `sette_orca2` | `sette_orca2` |
| Nitrogen Deposition | `PRODUCT_NDEP` | `sette_orca2` | `sette_orca2` |
| PAR Solar Fraction | `PRODUCT_PAR` | `sette_orca2` | `sette_orca2` |
| Bathymetric Slope | `PRODUCT_BATHY` | `sette_orca2` | `sette_orca2` |
| Hydrothermal Fe | `PRODUCT_HYDROFE` | `sette_orca2` | `sette_orca2` |
| River Nutrient Fluxes | `PRODUCT_RIVER` | `sette_orca2` | `sette_orca2` |

---

## 3. Command-Line Interface (`pisces-inidata`)

> [!NOTE]
> All commands accept `--grid <NAME>` (e.g. `--grid eORCA1`). The legacy flag `--orca <NAME>` remains fully supported as a backwards-compatible alias.

### `pisces-inidata check`
Runs pre-flight integrity verification before launching remapping jobs:
```bash
pisces-inidata check --grid ORCA2
# Check against specific pack:
pisces-inidata check --grid eORCA1 --pack ece3
```
- Verifies system binaries (`cdo`, `ncks`, `ncap2`, `ncatted`).
- Confirms presence of target domain files (`domain_cfg.nc`, `maskutil.nc`).
- Checks raw input catalog and verifies filesystem storage capacity.

### `pisces-inidata produce`
Executes initial conditions generation pipeline (Stage 1 ETL followed by Stage 2 parallel remapping):
```bash
# Produce inidata on eORCA1 (or ORCA2, eORCA025)
pisces-inidata produce --grid eORCA1 --domain-dir /path/to/nemo/domain

# Produce with specific pack:
pisces-inidata produce --grid eORCA1 --pack ece3

# Run only Stage 1 source preparation:
pisces-inidata produce --grid eORCA1 --stage stage1

# Dry-run inspection of generated batch jobs:
pisces-inidata produce --grid eORCA025 --dry-run
```

### `pisces-inidata prepare-sources`
Executes Stage 1 (Grid-Agnostic ETL) to format, pad to 6000 m, fill ocean missing values (`cdo fillmiss`), and standardize observational sources into uniform regular NetCDF files:
```bash
# Prepare all 15 components for active pack:
pisces-inidata prepare-sources

# Prepare specific tracer:
pisces-inidata prepare-sources NO3

# Force regeneration:
pisces-inidata prepare-sources TALK --pack ece4 --force
```
Standardized files are cached in `${STANDARDIZED_DIR}` and reused across all target resolutions.

### `pisces-inidata remap`
Executes Stage 2 (Target Remapping) to interpolate a standardized regular source to the target NEMO mesh:
```bash
# Remap all variables onto eORCA1:
pisces-inidata remap all --grid eORCA1

# Remap specific forcing:
pisces-inidata remap dust --grid eORCA025
```

### `pisces-inidata verify`
Inspects all 15 expected NetCDF output files in an output directory, verifies shapes, calculates min/mean/max bounds, and ensures zero blank/NaN files:
```bash
# Verify outputs for eORCA025:
pisces-inidata verify --grid eORCA025

# Verify explicit directory:
pisces-inidata verify --grid eORCA1 --out-dir /path/to/output_eORCA1
```

### `pisces-inidata grid-config`
Inspects declarative target grid profiles from `grids.yaml` or generates shell exports:
```bash
# List all configured grids:
pisces-inidata grid-config

# Inspect a specific grid:
pisces-inidata grid-config --grid eORCA025

# Export environment variables for shell evaluation:
pisces-inidata grid-config --grid eORCA025 --export
```

### `pisces-inidata platform-config`
Inspects declarative HPC platform profiles from `platforms.yaml` or generates shell exports:
```bash
# List all configured platforms and detect current system:
pisces-inidata platform-config

# Inspect a specific platform profile:
pisces-inidata platform-config --platform nord4

# Export platform environment variables for shell sourcing:
eval "$(pisces-inidata platform-config --platform nord4 --export)"
```


### `pisces-inidata validate`
Executes statistical procedure validation against official NEMO/SETTE ORCA2 benchmark:
```bash
# Validate generated ORCA2 outputs (default pack: official_sette)
pisces-inidata validate --pack official_sette --test-dir output_ORCA2 --ref-dir sette_reference_ORCA2
# Enforce non-zero exit code in CI:
pisces-inidata validate --fail-on-error
```

### `pisces-inidata test-reproduction`
Executes pipeline reproduction benchmark against EC-Earth3 eORCA1 baseline:
```bash
# Validate reproduction against EC-Earth3 baseline (default pack: official_sette)
pisces-inidata test-reproduction --pack official_sette
# Or with explicit paths:
pisces-inidata test-reproduction \
    --pack official_sette \
    --test-dir output_eORCA1 \
    --ref-dir /path/to/ece3_eORCA1_reference \
    --mask domain/eORCA1/maskutil.nc
```

### `pisces-inidata download`
Fetches and stages raw observational datasets, with optional automatic Stage 1 source standardization:
```bash
# Download raw datasets:
pisces-inidata download

# Download and immediately run Stage 1 source standardization (ideal for hub04):
pisces-inidata download --prepare

# Download raw datasets for a specific pack:
pisces-inidata download --pack ece3
```

### `pisces-inidata pad`
Standalone vertical depth padding utility:
```bash
pisces-inidata pad input.nc output_padded.nc --bottom-depth 6000.0
```

### `pisces-inidata info`
Displays current environment, active pack, resolved paths, and product configurations:
```bash
pisces-inidata info
# Preview configuration for a different pack:
pisces-inidata info --pack ece3
```

---

## 4. Declarative Target Grid Configuration (`grids.yaml`)

Rather than hardcoding allowed grids or embedding resolution-specific conditionals (`if grid == ...`) in Python and Shell scripts, `pisces-inidata` defines target grids declaratively in `grids.yaml`.

### Structure of `grids.yaml`
```yaml
grids:
  ORCA2:
    description: "NEMO standard 2-degree tripolar grid (31 vertical levels)"
    resources:
      time: "00:30:00"
      memory: "8G"
      cpus: 8
      batch_weights: false
    disk_space_gb: 2.0
    vertical_levels: 31
    fallback_coords_source: "official_v5.0.0/bathy.orca.nc"

  eORCA1:
    description: "Extended ORCA 1-degree global grid (75 vertical levels)"
    resources:
      time: "01:00:00"
      memory: "16G"
      cpus: 16
      batch_weights: false
    disk_space_gb: 10.0
    vertical_levels: 75

  eORCA025:
    description: "Extended ORCA 0.25-degree eddy-permitting grid (1440x1206 in modern NEMO, 75 vertical levels)"
    resources:
      time: "02:00:00"
      memory: "64G"
      cpus: 16
      batch_weights: true
    disk_space_gb: 40.0
    vertical_levels: 75

  eORCA12:
    description: "Extended ORCA 1/12-degree eddy-resolving grid (75 vertical levels)"
    resources:
      time: "04:00:00"
      memory: "128G"
      cpus: 32
      batch_weights: true
    disk_space_gb: 120.0
    vertical_levels: 75
```

### Key Properties
- **`resources`**: Configures Slurm execution parameters (`time`, `memory`, `cpus`).
  - `batch_weights: true`: For high-resolution meshes (like `eORCA025` or `eORCA12`), precomputes SCRIP remapping weights as an asynchronous batch Slurm job before launching parallel field remapping.
  - `batch_weights: false`: For coarser grids (`ORCA2`, `eORCA1`), weights are computed inline in minutes.
- **`disk_space_gb`**: Verified by `pisces-inidata check` to ensure target filesystem has enough headroom before running heavy jobs.
- **`vertical_levels`**: Target vertical resolution (e.g. 31 or 75 levels).
- **`fallback_coords_source`**: Fallback coordinates file when `domain_cfg.nc` is omitted (e.g. SETTE `bathy.orca.nc` for ORCA2).

### Dynamic Dimension Handling & NEMO Versions
Exact horizontal grid dimensions $(N_x \times N_y)$ vary across NEMO versions depending on how cyclic halos and north boundary foldings are packaged in the domain files:
- **`eORCA025`**: Modern NEMO (NEMO 4 / NEMO 5 / EC-Earth4) uses **$1440 \times 1206$** in `eORCA025/domain_cfg.nc`. Legacy NEMO 3.6 domain files included 2 cyclic halo columns and extra boundary points resulting in $1442 \times 1207$.
- **`eORCA1`**: Nominal $1^\circ$ global mesh, typically $360 \times 290$ (modern NEMO) or $362 \times 292$ (legacy NEMO 3.6 / EC-Earth3).
- **`ORCA2`**: Nominal $2^\circ$ tripolar mesh (e.g. $182 \times 149$ in NEMO SETTE benchmark).

`pisces-inidata` **never hardcodes spatial dimensions** for remapping or validation. The pipeline dynamically extracts the exact coordinate matrices (`glamt`, `gphit`) directly from your target grid's `domain_cfg.nc` (or `coordinates.nc`) using CDO (`cdo griddes`), ensuring seamless compatibility with whichever domain configuration is provided.

### Adding a New Grid
Adding a new grid requires zero changes to shell scripts or Python code. Simply append your grid specification to `grids.yaml`, or point to a custom file using `PISCES_GRIDS_CONFIG=/path/to/custom_grids.yaml`.

---

## 5. Declarative HPC Platform Configuration (`platforms.yaml`)

Cluster-specific settings (Slurm accounts, queues/partitions, environment module loading, scratch storage roots, and central model domain directories) are maintained declaratively in `platforms.yaml`. The Python pipeline (`launcher.py`, `produce`) and CLI read these settings dynamically to generate Slurm Job Arrays or configure local execution, isolating platform quirks from core remapping logic.

### Structure of `platforms.yaml`
```yaml
platforms:
  nord4:
    description: "BSC Nord4 Cluster (Intel Xeon Platinum 8480+)"
    slurm:
      account: "bsc32"
      partition: "bsc_es"
    module_load: "module load CDO NCO 2>/dev/null || true"
    scratch_root: "/gpfs/scratch/bsc32/${USER}"
    domain_dir: "/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain"

  mn5:
    description: "BSC MareNostrum 5 (GPP)"
    slurm:
      account: "bsc32"
      partition: "gpp"
    module_load: "module load cdo nco 2>/dev/null || true"
    scratch_root: "/gpfs/scratch/bsc32/${USER}"
    domain_dir: "/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain"

  generic:
    description: "Generic Linux Workstation or Cluster"
    slurm:
      account: ""
      partition: ""
    module_load: ""
    scratch_root: "${HOME}/scratch"
    domain_dir: ""
```

### Environment Variable Overrides
All platform defaults can be overridden at runtime via standard environment variables:
- `PLATFORM` or `PISCES_PLATFORM`: Choose platform profile (`nord4`, `mn5`, `generic`). Defaults to auto-detection (e.g. detects `nord` or `mn5` in hostname) or `generic`.
- `SLURM_ACCOUNT`: Override Slurm project/account (e.g. `export SLURM_ACCOUNT=bsc32`).
- `SLURM_PARTITION`: Override Slurm partition/queue.
- `PISCES_WORKSPACE`: Override top-level scratch directory root.
- `DOMAIN_DIR` / `DOMAIN_BASE_DIR`: Override location of NEMO domain files.
- `CDO_OPTS`: Override CDO threading and locking flags (default: `-L -P <threads>`).
- `CDO_COMPRESS`: Override NetCDF4 compression options (default: `-f nc4 -z zip_4`).
- `PISCES_INSTITUTION`: Override CF-1.8 institution provenance metadata (default: `EC-Earth Consortium`).

---

## 6. Declarative Metadata Catalog & Conventions (`catalog.yaml`)

Rather than hardcoding raw input package paths (e.g. `official_v5.0.0`), filenames (`data_DOC_nomask.nc`), or internal NetCDF variable names (`epsdb`, `fr_par`, `Alkalini`, `DIC`) across codebase modules, `pisces-inidata` decouples data provider conventions and target model expectations in `catalog.yaml`.

### Decoupled Schema Architecture
- **`packages`**: External data packages, default subdirectories, archive names, and URLs. Supports environment variable override `OFFICIAL_INPUTS_DIR`.
- **`sources`**: Observational and benchmark source products (e.g. `woa23`, `glodap_v2_2016b`, `panaiotis2024`, `sette_nomask`, `sette_orca2`), specifying raw file names, internal variable names, abyssal padding depths, and fillmiss requirements.
- **`conventions`**: Target model initial condition conventions (e.g. `nemo4_ece4`), defining target output file patterns, target NetCDF variable names, units, and namelist compatibility symlinks.

### CLI Inspection & Resolution Commands
```bash
# Resolve source metadata for Stage 1 standardization:
pisces-inidata resolve-source DOC --pack ece4 --export
pisces-inidata resolve-source hydrofe --pack ece4 --export

# Resolve target model convention for Stage 2 remapping:
pisces-inidata resolve-target TALK --grid eORCA1 --export

# Query target vertical levels from domain_cfg or catalog reference:
pisces-inidata get-vertical-levels --grid ORCA2

# Inspect resolved external package directory:
pisces-inidata catalog package-dir official_nemo_inputs
```

---

## 7. HPC Storage & Directory Structure

To ensure optimal performance and respect storage policies on HPC clusters (e.g. BSC Nord4 and MareNostrum 5):

```text
${PISCES_WORKSPACE}/               # Default: /gpfs/scratch/bsc32/${USER}/pisces_inidata
├── shared/
│   ├── raw/                       # Raw observational archives
│   └── standardized/              # Stage 1 regular 1°x1° NetCDFs
│       ├── ece4/                  # Cached and reused across all target grids
│       └── ece3/
└── grids/
    ├── eORCA1/
    │   ├── weights/               # CDO SCRIP remapping weights
    │   ├── inidata/               # Final 15 target NetCDF initial condition files
    │   ├── jobs/                  # Slurm job scripts
    │   └── logs/                  # Slurm stdout/stderr logs
    └── eORCA025/
```

### Local NVMe Scratch (`$TMPDIR`)
On BSC compute nodes, heavy intermediate CDO operations utilize:
```bash
$TMPDIR -> /scratch/tmp/$SLURM_JOB_ID
```
Local NVMe solid-state storage provides maximum I/O throughput and ensures shared GPFS file systems remain free of ephemeral scratch files. Temporary directories are automatically cleaned when Slurm terminates the job.
