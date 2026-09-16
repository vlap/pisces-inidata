#!/usr/bin/env bash
# ==============================================================================
# format_rivers.sh
# Modular orchestrator for river nutrient exports (Global NEWS 2):
#   1. Stage 1: Format & sanitize regular source coordinates (prepare_standard_sources.sh)
#   2. Stage 2: Conservative remapping to target grid (remap_field.sh)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Stage 1: Standardize source
bash "${SCRIPT_DIR}/prepare_standard_sources.sh" river

# Stage 2: Remap to target grid
bash "${SCRIPT_DIR}/remap_field.sh" river river

echo "=== River nutrient step finished successfully ==="
