# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-15
### Added
- Complete open-source pipeline packaging for EC-Earth4 and NEMO/PISCES community.
- Full per-variable product configuration (`products.cfg`) allowing selection between WOA23, WOA2009, GLODAP (v1, v2.2016b, v2.2023, v3), Panaïotis et al. (2024) DOC, Hansell (2009), and Tagliabue et al. (2012) Iron.
- Machine-learning DOC climatology (Panaïotis et al. 2024, SEANOE) preprocessing pipeline.
- Automated validation suite and diagnostic scoreboard (`generate_validation_scoreboard.py`) computing RMSE, NRMSE, Mean Bias, Pearson $r$, and Spearman $\rho$ against the official SETTE ORCA2 reference.
- Abyssal depth padding (`pad_abyssal_depth.py`) extending 5500m observations to 6000m abyss with boundary layer replication.
- Comprehensive Sphinx documentation for ReadTheDocs with MyST markdown parser and RTD theme.
- CI workflows for GitHub Actions testing linting, unit tests, and documentation builds.
