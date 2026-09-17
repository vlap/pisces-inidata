#!/usr/bin/env bash
# ==============================================================================
# Configuration file for PISCES inidata processing tool
# ==============================================================================

SCRIPT_DIR_CONFIG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR_CONFIG}/.." && pwd)"

# Ensure pisces-inidata CLI and Python modules are discoverable
export PATH="${REPO_DIR}/bin:${PATH}"
export PYTHONPATH="${REPO_DIR}/python:${PYTHONPATH:-}"

# Target grid resolution (e.g. eORCA1, eORCA025, ORCA2, eORCA12)
GRID_NAME="${GRID_NAME:-eORCA1}"

# ------------------------------------------------------------------------------
# 1. Platform Configuration (platforms.yaml)
# ------------------------------------------------------------------------------
eval "$(python3 -m pisces_inidata.cli platform-config ${PLATFORM:+--platform "${PLATFORM}"} --export 2>/dev/null || true)"

SLURM_ACCOUNT="${SLURM_ACCOUNT:-}"
SLURM_PARTITION="${SLURM_PARTITION:-}"
MODULE_LOAD_CMD="${MODULE_LOAD_CMD:-}"

# ------------------------------------------------------------------------------
# 2. Target Grid & Resource Profile (grids.yaml)
# ------------------------------------------------------------------------------
eval "$(python3 -m pisces_inidata.cli grid-config --grid "${GRID_NAME}" --export 2>/dev/null || true)"

SLURM_TIME="${SLURM_TIME:-${GRID_SLURM_TIME:-01:00:00}}"
SLURM_MEM="${SLURM_MEM:-${GRID_SLURM_MEM:-16G}}"
SLURM_CPUS_PER_TASK="${SLURM_CPUS_PER_TASK:-${GRID_SLURM_CPUS:-16}}"

# ------------------------------------------------------------------------------
# 3. Workspaces & Storage Hierarchy
# ------------------------------------------------------------------------------
SCRATCH_ROOT="${SCRATCH_ROOT:-${DEFAULT_PLATFORM_SCRATCH:-${HOME}/scratch}}"
WORKSPACE="${PISCES_WORKSPACE:-${SCRATCH_ROOT}/pisces_inidata}"
export WORKSPACE
export PISCES_WORKSPACE="${WORKSPACE}"

# Shared assets (Raw catalog & standardized ETL)
RAW_DIR="${RAW_DIR:-${WORKSPACE}/shared/raw}"
if [ ! -d "${RAW_DIR}" ] && [ -d "${PWD}/pisces_raw_sources" ] && [ -n "$(ls -A "${PWD}/pisces_raw_sources" 2>/dev/null)" ]; then
    RAW_DIR="${PWD}/pisces_raw_sources"
fi

# Target domain directory
DOMAIN_BASE_DIR="${DOMAIN_BASE_DIR:-${DEFAULT_PLATFORM_DOMAIN:-${PWD}/domain}}"
DOMAIN_CFG="${DOMAIN_CFG:-${DOMAIN_BASE_DIR}/${GRID_NAME}/domain_cfg.nc}"
MASKUTIL="${MASKUTIL:-${DOMAIN_BASE_DIR}/${GRID_NAME}/maskutil.nc}"

# ------------------------------------------------------------------------------
# 4. Observational Sources & Presets (sources.yaml)
# ------------------------------------------------------------------------------
CONFIG_FILE="${PISCES_CONFIG:-${CONFIG_FILE:-${REPO_DIR}/sources.yaml}}"
export CONFIG_FILE
export PISCES_CONFIG="${CONFIG_FILE}"

if [ -f "${CONFIG_FILE}" ]; then
    eval "$(python3 -m pisces_inidata.cli config --export --file "${CONFIG_FILE}" ${PRESET:+--preset "${PRESET}"} 2>/dev/null || true)"
fi

PRESET="${PRESET:-${INIDATA_PRESET:-ece4}}"
export PRESET INIDATA_PRESET

STANDARDIZED_DIR="${STANDARDIZED_DIR:-${WORKSPACE}/shared/standardized/${PRESET}}"
export STANDARDIZED_DIR

# Target grid output paths
GRID_DIR="${WORKSPACE}/grids/${GRID_NAME}"
WORK_DIR="${WORK_DIR:-${GRID_DIR}}"
WEIGHTS_DIR="${WEIGHTS_DIR:-${GRID_DIR}/weights}"
OUTPUT_DIR="${OUTPUT_DIR:-${GRID_DIR}/inidata}"
LOG_DIR="${LOG_DIR:-${GRID_DIR}/logs}"
SBATCH_DIR="${SBATCH_DIR:-${GRID_DIR}/jobs}"

# Local NVMe scratch or fallback
TMP_BASE="${TMPDIR:-${WORKSPACE}/fallback_tmp}"
mkdir -p "${TMP_BASE}" "${WORKSPACE}" "${OUTPUT_DIR}" "${WEIGHTS_DIR}" "${LOG_DIR}" "${SBATCH_DIR}" 2>/dev/null || true

# ------------------------------------------------------------------------------
# 5. CDO Execution & Compression Options (platforms.yaml)
# ------------------------------------------------------------------------------
CDO_THREADS="${CDO_THREADS:-${SLURM_CPUS_PER_TASK:-${DEFAULT_CDO_THREADS:-4}}}"
CDO_OPTS="${CDO_OPTS:-${DEFAULT_CDO_OPTS:--L -P ${CDO_THREADS}}}"
CDO_COMPRESS="${CDO_COMPRESS:-${DEFAULT_CDO_COMPRESS:--f nc4 -z zip_4}}"
PISCES_INSTITUTION="${PISCES_INSTITUTION:-${DEFAULT_PLATFORM_INSTITUTION:-EC-Earth Consortium}}"
export PISCES_INSTITUTION

# Catalog paths
OFFICIAL_DIR="${OFFICIAL_INPUTS_DIR:-$(python3 -m pisces_inidata.cli catalog package-dir official_nemo_inputs --raw-dir "${RAW_DIR}" 2>/dev/null || echo "${RAW_DIR}/official_v5.0.0")}"
WOA23_DIR="${WOA23_DIR:-${RAW_DIR}/woa23}"
GLODAP_VERSION="${GLODAP_VERSION:-v2.2016b}"
GLODAP_V2_2023_DIR="${GLODAP_V2_2023_DIR:-${RAW_DIR}/glodap_v2_2023}"
GLODAP_V2_DIR="${GLODAP_V2_DIR:-${RAW_DIR}/glodap_v2}"
GLODAP_V1_DIR="${GLODAP_V1_DIR:-${RAW_DIR}/glodap_v1}"
PANAIOTIS_DOC_DIR="${PANAIOTIS_DOC_DIR:-${RAW_DIR}/panaiotis2024_doc}"

# Tracers and boundary variables (declared in sources.yaml)
IFS=' ' read -r -a TRACERS_3D <<< "${TRACERS_3D_LIST:-NO3 PO4 Si O2 TALK TDIC PiDIC DOC Fer}"
IFS=' ' read -r -a RIVER_VARS <<< "${RIVER_VARS_LIST:-riverdin riverdip riverdon riverdop riverdoc riverdsi riverdic}"
IFS=' ' read -r -a DUST_VARS <<< "${DUST_VARS_LIST:-dust dustfer dustpo4 dustsi solubility2}"
IFS=' ' read -r -a NDEP_VARS <<< "${NDEP_VARS_LIST:-ndep ndep2}"

# Export all variables for sub-scripts
export GRID_NAME DOMAIN_BASE_DIR DOMAIN_CFG MASKUTIL
export SCRATCH_ROOT WORKSPACE PISCES_WORKSPACE GRID_DIR WORK_DIR RAW_DIR STANDARDIZED_DIR WEIGHTS_DIR OUTPUT_DIR LOG_DIR SBATCH_DIR TMP_BASE
export SLURM_ACCOUNT SLURM_PARTITION SLURM_TIME SLURM_CPUS_PER_TASK
export MODULE_LOAD_CMD CDO_THREADS CDO_OPTS CDO_COMPRESS
export TRACERS_3D RIVER_VARS DUST_VARS NDEP_VARS INIDATA_PRESET CONFIG_FILE PISCES_CONFIG
export GRID_BATCH_WEIGHTS GRID_FALLBACK_COORDS GRID_VERTICAL_LEVELS
export OFFICIAL_DIR WOA23_DIR GLODAP_VERSION GLODAP_V2_2023_DIR GLODAP_V2_DIR GLODAP_V1_DIR PANAIOTIS_DOC_DIR

# ------------------------------------------------------------------------------
# 6. Scientific Provenance & Metadata Stamping (CF-1.8)
# ------------------------------------------------------------------------------
stamp_provenance() {
    local target_file="$1"
    [ -f "${target_file}" ] || return 0
    python3 -m pisces_inidata.cli stamp "${target_file}" 2>/dev/null || {
        command -v ncatted >/dev/null 2>&1 || return 0
        local timestamp
        timestamp="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
        local git_rev
        git_rev="$(git -C "${SCRIPT_DIR_CONFIG}" rev-parse --short HEAD 2>/dev/null || echo 'release')"
        ncatted -h -O \
            -a title,global,o,c,"PISCES Initial Conditions (${GRID_NAME})" \
            -a institution,global,o,c,"${PISCES_INSTITUTION:-EC-Earth Consortium}" \
            -a source_pipeline,global,o,c,"pisces-inidata (git:${git_rev})" \
            -a inidata_preset,global,o,c,"${INIDATA_PRESET:-custom}" \
            -a generation_date,global,o,c,"${timestamp}" \
            "${target_file}" 2>/dev/null || true
    }
}
export -f stamp_provenance 2>/dev/null || true
