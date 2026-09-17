# Legacy Shell Scripts

This directory contains the original Bash pipeline scripts:
- `launcher_pisces_inidata.sh`: Original HPC job launcher script.
- `prepare_standard_sources.sh`: Stage 1 grid-agnostic ETL source standardization.
- `remap_field.sh`: Stage 2 target grid remapping and vertical interpolation.
- `gen_grid_and_weights.sh`: CDO SCRIP grid description and remapping weights generation.
- `prepare_sette_reference_orca2.sh`: Benchmark reference extraction for ORCA2 SETTE.
- `config.sh`: Shell environment configuration loader.

### Note
These scripts are preserved for historical reference and backward continuity.
The primary, actively maintained pipeline is implemented in pure Python under [`python/pisces_inidata/`](../python/pisces_inidata/) and orchestrated through the unified `pisces-inidata produce` CLI command.
