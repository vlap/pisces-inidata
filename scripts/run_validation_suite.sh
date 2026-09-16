#!/usr/bin/env bash
# ==============================================================================
# run_validation_suite.sh
# Validation driver for PISCES inidata on ORCA2 against SETTE benchmark reference.
# Verifies units, physical ranges, spatial patterns, and mass conservation.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export GRID_NAME="ORCA2"
export PRESET="${PRESET:-official_sette}"
source "${SCRIPT_DIR}/config.sh" 2>/dev/null || true

TEST_DIR="${OUTPUT_DIR:-${PWD}/output_ORCA2}"
REF_DIR="${SETTE_REF_DIR:-${WORK_DIR}/sette_reference_ORCA2}"
OUTPUT_MD="${OUTPUT_MD:-${PWD}/VALIDATION_SCOREBOARD_ORCA2.md}"

if [ ! -d "${REF_DIR}" ] && [ -f "${SCRIPT_DIR}/prepare_sette_reference_orca2.sh" ]; then
    echo "SETTE ORCA2 reference directory not found at ${REF_DIR}. Assembling..."
    bash "${SCRIPT_DIR}/prepare_sette_reference_orca2.sh" || true
fi

echo "========================================================================"
echo " Running PISCES Validation Suite on ORCA2 vs SETTE Benchmark"
echo " Preset:              ${PRESET}"
echo " Test Directory:      ${TEST_DIR}"
echo " Reference Directory: ${REF_DIR}"
echo " Output Scorecard:    ${OUTPUT_MD}"
echo "========================================================================"

pisces-inidata validate --preset "${PRESET}" --test-dir "${TEST_DIR}" --ref-dir "${REF_DIR}" --output-md "${OUTPUT_MD}"
