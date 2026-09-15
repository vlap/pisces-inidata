# API & CLI Reference

This section provides technical references for the Python modules and command-line interfaces.

---

## Command-Line Interface (`pisces-inidata`)

### `pisces-inidata info`
Displays the active configuration, paths, and checks that chosen product settings are valid.

### `pisces-inidata run [--orca {ORCA2,eORCA1,eORCA025}]`
Executes the full end-to-end pipeline to generate 3D tracers and 2D boundary forcings on the selected NEMO grid.

### `pisces-inidata validate`
Runs statistical diagnostics against the SETTE reference files on ORCA2 and writes `VALIDATION_SCOREBOARD_ORCA2.md`.

### `pisces-inidata check [--orca {ORCA2,eORCA1,eORCA025}]`
Runs automated pre-flight verification of system binaries (CDO, NCO), Python environment, target grid & domain definitions, raw observational catalog, and disk space.

### `pisces-inidata pad <input.nc> <output.nc> [--depth 6000.0]`
Directly runs the vertical depth padding utility on any 3D/4D NetCDF file.

---

## Python API

### `pisces_inidata.padding`

::: pisces_inidata.padding.pad_abyssal_depth
    handler: python
    options:
      show_root_heading: true

### `pisces_inidata.scoreboard`

::: pisces_inidata.scoreboard.compute_diagnostics
    handler: python
    options:
      show_root_heading: true

::: pisces_inidata.scoreboard.generate_scoreboard
    handler: python
    options:
      show_root_heading: true

### `pisces_inidata.config`

::: pisces_inidata.config.load_config
    handler: python
    options:
      show_root_heading: true

::: pisces_inidata.config.validate_config
    handler: python
    options:
      show_root_heading: true
