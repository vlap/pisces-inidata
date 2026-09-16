#!/usr/bin/env bash
# ==============================================================================
# format_surface_forcings.sh
# Modular orchestrator for atmospheric and surface forcings:
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
    bash "${SCRIPT_DIR}/remap_field.sh" "${comp}" 2d
}

case "${COMPONENT}" in
    dust|ndep|par)
        process_comp "${COMPONENT}"
        ;;
    all)
        process_comp dust
        process_comp ndep
        process_comp par
        ;;
    *)
        echo "ERROR: Unknown component: ${COMPONENT} (Choose: dust | ndep | par | all)" >&2
        exit 1
        ;;
esac

echo "=== Surface forcings step finished successfully ==="
