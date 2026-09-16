#!/usr/bin/env bash
# ==============================================================================
# format_tracers_3d.sh
# Modular orchestrator for 3D biogeochemical tracers:
#   1. Stage 1: Format & standardize regular source (prepare_standard_sources.sh)
#   2. Stage 2: Pure CDO remapping to target grid (remap_field.sh)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <TRACER_VAR> [MODE: offline|online]"
    echo "Tracer options: ${TRACERS_3D[*]}"
    exit 1
fi

VAR="$1"
MODE="${2:-offline}"

# Stage 1: Format & Standardize regular source (grid-agnostic, cached)
bash "${SCRIPT_DIR}/prepare_standard_sources.sh" "${VAR}"

# Stage 2: Pure CDO interpolation & remapping to target grid
bash "${SCRIPT_DIR}/remap_field.sh" "${VAR}" 3d
