#!/usr/bin/env bash
# ==============================================================================
# test_pipeline_reproduction.sh
# Precision benchmark testing whether re-interpolating original 1x1 unmasked
# regular products (WOA2009 & GLODAPv1.1) faithfully reproduces the EC-Earth3
# baseline inidata on eORCA1.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export GRID_NAME="eORCA1"
export PRESET="${PRESET:-official_sette}"
source "${SCRIPT_DIR}/config.sh" 2>/dev/null || true

REF_DIR="${ECE4_PISCES_REF:-/gpfs/projects/bsc32/models/ecearth/ece4-trunk/inidata/nemo/pisces}"
RAW_NOMASK_DIR="${RAW_DIR:-${PWD}/pisces_raw_sources}/official_v5.0.0"
VAL_OUTPUT_DIR="${OUTPUT_DIR:-${WORK_DIR:-${PWD}/work_eORCA1}/output_eORCA1}"
REPORT_MD="${REPORT_MD:-${PWD}/PIPELINE_REPRODUCTION_REPORT.md}"
MASK_FILE="${DOMAIN_BASE_DIR:-${PWD}/domain}/eORCA1/maskutil.nc"

mkdir -p "${VAL_OUTPUT_DIR}"

echo "========================================================================"
echo " PISCES Pipeline Precision Benchmark: EC-Earth3 Baseline Reproduction"
echo " Preset:                  ${PRESET}"
echo " Raw 1x1 Unmasked Source: ${RAW_NOMASK_DIR}"
echo " Reference eORCA1 Ground Truth: ${REF_DIR}"
echo " Output Directory:        ${VAL_OUTPUT_DIR}"
echo " Report Markdown:         ${REPORT_MD}"
echo "========================================================================"

# Run python reproduction benchmark tool
pisces-inidata test-reproduction \
    --preset "${PRESET}" \
    --test-dir "${VAL_OUTPUT_DIR}" \
    --ref-dir "${REF_DIR}" \
    --mask "${MASK_FILE}" \
    --output-md "${REPORT_MD}" || true
