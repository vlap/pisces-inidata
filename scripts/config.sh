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
if [ -z "${DOMAIN_BASE_DIR:-}" ]; then
    if [ -d "${PWD}/domain/${GRID_NAME}" ]; then
        DOMAIN_BASE_DIR="${PWD}/domain"
    elif [ -d "/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain" ]; then
        DOMAIN_BASE_DIR="/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/domain"
    else
        DOMAIN_BASE_DIR="${PWD}/domain"
    fi
fi

# Paths to grid and mask files (provided by user or official EC-Earth4 inidata)
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

MODULE_LOAD_CMD="set +u; module load CDO/2.3.0-gompi-2020b NCO/5.1.0-foss-2020b netcdf4-python/1.5.7-foss-2020b-Python-3.8.6 2>/dev/null || module load CDO/2.3.0-gompi-2020b NCO/5.1.0-foss-2020b netcdf4-python/1.6.1-foss-2020b-Python-3.8.6 2>/dev/null || module load CDO NCO 2>/dev/null || true; set -u"

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
#   'modern'           : Uses latest observational products: WOA23 (NO3, PO4, Si, O2) & GLODAP (TALK, TDIC, PiDIC)
#   'official_regular' : Uses official regular 1x1 unmasked fields (WOA/GLODAP nomask) with 3D interpolation
# NOTE: EC-Earth3 inidata is strictly a verification benchmark (test_pipeline_reproduction.sh), not an input source.
SOURCE_MODE="${SOURCE_MODE:-modern}"

# GLODAP version configuration (supported: 'v2.2016b' [default 3D gridded], 'v2.2023', 'v1.1')
# Only 3D gridded products are supported; discrete bottle master files (e.g. GLODAPv3 Master File) are not supported.
GLODAP_VERSION="${GLODAP_VERSION:-v2.2016b}"

# Load per-variable source configuration (sources.yaml) via Python exporter
SCRIPT_DIR_CONFIG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR_CONFIG}/.." && pwd)"
if [ -f "${REPO_DIR}/sources.yaml" ]; then
    eval "$(python3 -m pisces_inidata.config export "${REPO_DIR}/sources.yaml" 2>/dev/null || pisces-inidata config --export --file "${REPO_DIR}/sources.yaml" 2>/dev/null || true)"
elif [ -f "${SCRIPT_DIR_CONFIG}/sources.yaml" ]; then
    eval "$(python3 -m pisces_inidata.config export "${SCRIPT_DIR_CONFIG}/sources.yaml" 2>/dev/null || pisces-inidata config --export --file "${SCRIPT_DIR_CONFIG}/sources.yaml" 2>/dev/null || true)"
fi

WOA23_DIR="${RAW_DIR}/woa23"
GLODAP_V3_DIR="${RAW_DIR}/glodap_v3"
GLODAP_V2_2023_DIR="${RAW_DIR}/glodap_v2_2023"
GLODAP_V2_DIR="${RAW_DIR}/glodap_v2"
GLODAP_V1_DIR="${RAW_DIR}/glodap_v1"
PANAIOTIS_DOC_DIR="${RAW_DIR}/panaiotis2024_doc"

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
export WOA23_DIR GLODAP_VERSION GLODAP_V3_DIR GLODAP_V2_2023_DIR GLODAP_V2_DIR GLODAP_V1_DIR PANAIOTIS_DOC_DIR

# ------------------------------------------------------------------------------
# 5. Scientific Provenance & FAIR Metadata Stamping
# ------------------------------------------------------------------------------
stamp_provenance() {
    local target_file="$1"
    if [ -f "${target_file}" ] && command -v ncatted >/dev/null 2>&1; then
        local git_rev
        git_rev="$(git -C "${SCRIPT_DIR_CONFIG:-.}" rev-parse --short HEAD 2>/dev/null || echo 'release')"
        local timestamp
        timestamp="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
        local prod_summary="NO3:${PRODUCT_NO3:-woa23}, PO4:${PRODUCT_PO4:-woa23}, Si:${PRODUCT_Si:-woa23}, O2:${PRODUCT_O2:-woa23}, TALK:${PRODUCT_TALK:-glodap_v2_2016b}, TDIC:${PRODUCT_TDIC:-glodap_v2_2016b}, DOC:${PRODUCT_DOC:-panaiotis2024}, Fer:${PRODUCT_Fer:-sette_nomask}"

        ncatted -h -O \
            -a title,global,o,c,"PISCES Biogeochemical Initial Conditions for NEMO/EC-Earth4 (${GRID_NAME})" \
            -a institution,global,o,c,"Barcelona Supercomputing Center (BSC), EC-Earth Consortium" \
            -a source_pipeline,global,o,c,"pisces-inidata (https://github.com/vlap/pisces-inidata)" \
            -a source_products,global,o,c,"${prod_summary}" \
            -a git_commit,global,o,c,"${git_rev}" \
            -a generation_timestamp,global,o,c,"${timestamp}" \
            -a references,global,o,c,"https://pisces-inidata.readthedocs.io/en/latest/" \
            -a license,global,o,c,"Apache-2.0" \
            "${target_file}" 2>/dev/null || true
    fi
}
export -f stamp_provenance 2>/dev/null || true

