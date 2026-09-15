#!/usr/bin/env bash
# ==============================================================================
# download_sources.sh
# Backward-compatible wrapper delegating dataset acquisition to pisces-inidata.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh" 2>/dev/null || true

RAW_DIR="${RAW_DIR:-${PWD}/pisces_raw_sources}"
CFG_FILE="${SCRIPT_DIR}/../sources.yaml"

pisces-inidata download --sources "${CFG_FILE}" --raw-dir "${RAW_DIR}" "$@"
