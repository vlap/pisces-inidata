#!/usr/bin/env bash
# ==============================================================================
# Configuration file for PISCES inidata processing tool
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Target Grid & Domain Configuration
# ------------------------------------------------------------------------------
# Grid resolution name (e.g. eORCA1, eORCA025, ORCA1, ORCA2)
GRID_NAME="${GRID_NAME:-eORCA1}"

# Base directory for NEMO domain files
DOMAIN_BASE_DIR="${DOMAIN_BASE_DIR:-/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain}"

# Paths to grid and mask files (provided by user)
DOMAIN_CFG="${DOMAIN_CFG:-${DOMAIN_BASE_DIR}/${GRID_NAME}/domain_cfg.nc}"
MASKUTIL="${MASKUTIL:-${DOMAIN_BASE_DIR}/${GRID_NAME}/maskutil.nc}"

# ------------------------------------------------------------------------------
# 2. Workspaces & Scratch Directories
# ------------------------------------------------------------------------------
# Scratch root: auto-detect user scratch on /esarchive, otherwise fallback to local scratch
if [ -d "/esarchive/scratch/${USER}" ]; then
    DEFAULT_SCRATCH="/esarchive/scratch/${USER}/tmp"
elif [ -d "/esarchive/scratch" ]; then
    DEFAULT_SCRATCH="/esarchive/scratch/${USER}/tmp"
else
    DEFAULT_SCRATCH="/tmp/${USER}/pisces"
fi
SCRATCH_ROOT="${SCRATCH_ROOT:-${DEFAULT_SCRATCH}}"
WORK_DIR="${WORK_DIR:-${SCRATCH_ROOT}/pisces_inidata_${GRID_NAME}}"

# Subdirectories for raw data, weights, and final outputs
# Default to shared team raw directory if present, else user scratch
if [ -d "/esarchive/scratch/vlapin/tmp/pisces_raw_sources" ]; then
    DEFAULT_RAW="/esarchive/scratch/vlapin/tmp/pisces_raw_sources"
else
    DEFAULT_RAW="${SCRATCH_ROOT}/pisces_raw_sources"
fi
RAW_DIR="${RAW_DIR:-${DEFAULT_RAW}}"
WEIGHTS_DIR="${WORK_DIR}/weights"
OUTPUT_DIR="${WORK_DIR}/output_${GRID_NAME}"
LOG_DIR="${WORK_DIR}/logs"

# ------------------------------------------------------------------------------
# 3. HPC Environment & Slurm Settings (Nord4 / hub02)
# ------------------------------------------------------------------------------
SLURM_ACCOUNT="${SLURM_ACCOUNT:-bsc32}"
SLURM_PARTITION="${SLURM_PARTITION:-bsc_es}"
SLURM_TIME="${SLURM_TIME:-01:00:00}"
SLURM_CPUS_PER_TASK="${SLURM_CPUS_PER_TASK:-16}"

# Command to load required modules on HPC (Nord4 / interactive nodes)
MODULE_LOAD_CMD="set +u; module load CDO/2.3.0-gompi-2020b NCO/5.1.0-foss-2020b netcdf4-python/1.6.1-foss-2020b-Python-3.8.6 2>/dev/null || module load CDO NCO 2>/dev/null || true; set -u"

# CDO execution options (safe login node limit: 4 threads; full Slurm job: 16 threads)
if [ -z "${SLURM_JOB_ID:-}" ]; then
    CDO_THREADS="${CDO_THREADS:-4}"
else
    CDO_THREADS="${SLURM_CPUS_PER_TASK:-16}"
fi
CDO_OPTS="-L -P ${CDO_THREADS}"
CDO_COMPRESS="-f nc4 -z zip_4"

# ------------------------------------------------------------------------------
# 4. Source Data Catalog & References
# ------------------------------------------------------------------------------
# Source mode:
#   'modern'           : Uses latest observational products: WOA23 (NO3, PO4, Si, O2) & GLODAPv2 (TALK, TDIC, PiDIC)
#   'official_regular' : Uses official regular 1x1 unmasked fields (WOA/GLODAP nomask) with 3D interpolation
#   'ece3_baseline'    : Uses validated ECE3/SHACONEMO baseline in /gpfs/projects/bsc32/models/ecearth/v3.3.3/inidata/pisces/
SOURCE_MODE="${SOURCE_MODE:-modern}"

WOA23_DIR="${RAW_DIR}/woa23"
GLODAP_V2_DIR="${RAW_DIR}/glodap_v2"

# Paths to ECE3 / BSC baseline sources
ECE3_PISCES_DIR="${ECE3_PISCES_DIR:-/gpfs/projects/bsc32/models/ecearth/v3.3.3/inidata/pisces}"
if [ -f "/esarchive/scratch/vlapin/cdo_griddes_files/orca1_grid" ]; then
    DEFAULT_ORCA1_GRIDDES="/esarchive/scratch/vlapin/cdo_griddes_files/orca1_grid"
else
    DEFAULT_ORCA1_GRIDDES="${RAW_DIR}/orca1_grid"
fi
ORCA1_GRIDDES="${ORCA1_GRIDDES:-${DEFAULT_ORCA1_GRIDDES}}"

# JASMIN official PISCES inputs reference (fallback baseline)
JASMIN_PISCES_V5_URL="https://gws-access.jasmin.ac.uk/public/nemo/sette_inputs/extras/ORCA2_INPUTS_PISCES_v5.0.0.tar.gz"

# 3D Tracers to process
TRACERS_3D=("NO3" "PO4" "Si" "O2" "TALK" "TDIC" "PiDIC" "DOC" "Fer")

# River export variables (Global NEWS 2)
RIVER_VARS=("riverdin" "riverdip" "riverdon" "riverdop" "riverdoc" "riverdsi" "riverdic")

# Atmospheric deposition variables
DUST_VARS=("dust" "dustfer" "dustpo4" "dustsi" "solubility2")
NDEP_VARS=("ndep" "ndep2")

# Export all variables for sub-scripts
export GRID_NAME DOMAIN_BASE_DIR DOMAIN_CFG MASKUTIL
export SCRATCH_ROOT WORK_DIR RAW_DIR WEIGHTS_DIR OUTPUT_DIR LOG_DIR
export SLURM_ACCOUNT SLURM_PARTITION SLURM_TIME SLURM_CPUS_PER_TASK
export MODULE_LOAD_CMD CDO_THREADS CDO_OPTS CDO_COMPRESS
export TRACERS_3D RIVER_VARS DUST_VARS NDEP_VARS
export SOURCE_MODE ECE3_PISCES_DIR ORCA1_GRIDDES
export WOA23_DIR GLODAP_V2_DIR
