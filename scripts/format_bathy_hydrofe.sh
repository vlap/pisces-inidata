#!/usr/bin/env bash
# ==============================================================================
# format_bathy_hydrofe.sh
# Modular orchestrator for bathymetric shelf fraction and hydrothermal iron:
#   1. Stage 1: Format & standardize regular source (prepare_standard_sources.sh)
#   2. Stage 2: Pure CDO remapping to target grid (remap_field.sh)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

COMPONENT="${1:-all}"

process_comp() {
    local comp="$1"
    bash "${SCRIPT_DIR}/prepare_standard_sources.sh" "${comp}"
    bash "${SCRIPT_DIR}/remap_field.sh" "${comp}" "${comp}"
}

case "${COMPONENT}" in
    bathy|hydrofe)
        process_comp "${COMPONENT}"
        ;;
    all)
        process_comp bathy
        process_comp hydrofe
        ;;
    *)
        echo "ERROR: Unknown component: ${COMPONENT} (Choose: bathy | hydrofe | all)" >&2
        exit 1
        ;;
esac

echo "=== Bathy and hydrofe step finished successfully ==="
