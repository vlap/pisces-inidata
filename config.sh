#!/usr/bin/env bash
# ==============================================================================
# Configuration file for PISCES inidata processing tool
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Target Grid & Domain Configuration
# ------------------------------------------------------------------------------
# Grid resolution name (e.g. eORCA025, eORCA1, ORCA1, ORCA2)
GRID_NAME="${GRID_NAME:-eORCA025}"

# Base directory for NEMO domain files
DOMAIN_BASE_DIR="${DOMAIN_BASE_DIR:-/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain}"

# Paths to grid and mask files (provided by user)
DOMAIN_CFG="${DOMAIN_CFG:-${DOMAIN_BASE_DIR}/${GRID_NAME}/domain_cfg.nc}"
MASKUTIL="${MASKUTIL:-${DOMAIN_BASE_DIR}/${GRID_NAME}/maskutil.nc}"

# ------------------------------------------------------------------------------
# 2. Workspaces & Scratch Directories
# ------------------------------------------------------------------------------
# Scratch root (Nord4 / hub02 analysis default: /esarchive/scratch/vlapin/tmp/)
SCRATCH_ROOT="${SCRATCH_ROOT:-/esarchive/scratch/vlapin/tmp}"
WORK_DIR="${WORK_DIR:-${SCRATCH_ROOT}/pisces_inidata_${GRID_NAME}}"

# Subdirectories for raw data, weights, and final outputs
RAW_DIR="${WORK_DIR}/raw_sources"
WEIGHTS_DIR="${WORK_DIR}/weights"
OUTPUT_DIR="${WORK_DIR}/output_${GRID_NAME}"
LOG_DIR="${WORK_DIR}/logs"

# ------------------------------------------------------------------------------
# 3. HPC Environment & Slurm Settings (Nord4 / hub02)
# ------------------------------------------------------------------------------
SLURM_ACCOUNT="${SLURM_ACCOUNT:-bsc32}"
SLURM_PARTITION="${SLURM_PARTITION:-bsc_es}"
SLURM_TIME="${SLURM_TIME:-00:30:00}"
SLURM_CPUS_PER_TASK="${SLURM_CPUS_PER_TASK:-4}"

# Command to load required modules on HPC (Nord4 / interactive nodes)
MODULE_LOAD_CMD="module load CDO/2.1.1-foss-2019b NCO/5.1.3-foss-2019b 2>/dev/null || module load cdo nco 2>/dev/null || true"

# CDO execution options
CDO_THREADS="${CDO_THREADS:-4}"
CDO_OPTS="-L -P ${CDO_THREADS}"
CDO_COMPRESS="-f nc4 -z zip_4"

# ------------------------------------------------------------------------------
# 4. Source Data Catalog & References
# ------------------------------------------------------------------------------
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
