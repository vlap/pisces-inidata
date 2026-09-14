#!/usr/bin/env bash
# ==============================================================================
# download_sources.sh
# Fetch and prepare raw input source datasets for PISCES inidata.
# Run on an interactive node with outgoing internet access (e.g., hub02 analysis).
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

echo "=== [1/4] Preparing directories ==="
mkdir -p "${RAW_DIR}" "${OUTPUT_DIR}" "${WEIGHTS_DIR}" "${LOG_DIR}"

echo "Working directory: ${WORK_DIR}"
echo "Raw sources directory: ${RAW_DIR}"

# ------------------------------------------------------------------------------
# 1. Official NEMO PISCES inputs package (Baseline fallback)
# ------------------------------------------------------------------------------
PISCES_TAR="${RAW_DIR}/ORCA2_INPUTS_PISCES_v5.0.0.tar.gz"
EXTRACT_DIR="${RAW_DIR}/official_v5.0.0"

if [ ! -d "${EXTRACT_DIR}" ]; then
    echo "=== [2/4] Downloading official NEMO PISCES inputs archive ==="
    if [ ! -f "${PISCES_TAR}" ]; then
        echo "Fetching ${JASMIN_PISCES_V5_URL}..."
        curl -fSL "${JASMIN_PISCES_V5_URL}" -o "${PISCES_TAR}"
    else
        echo "Found existing archive: ${PISCES_TAR}"
    fi

    echo "Extracting official PISCES inputs to ${EXTRACT_DIR}..."
    mkdir -p "${EXTRACT_DIR}"
    tar -xzf "${PISCES_TAR}" -C "${EXTRACT_DIR}" --strip-components=1
else
    echo "=== [2/4] Official PISCES inputs already extracted in ${EXTRACT_DIR} ==="
fi

# ------------------------------------------------------------------------------
# 2. Check input grid & domain files
# ------------------------------------------------------------------------------
echo "=== [3/4] Verifying target domain files ==="
if [ ! -f "${DOMAIN_CFG}" ]; then
    echo "WARNING: domain_cfg.nc not found at ${DOMAIN_CFG}"
    echo "Please ensure ${DOMAIN_CFG} exists or set DOMAIN_CFG in config.sh"
else
    echo "Found domain_cfg: ${DOMAIN_CFG}"
fi

if [ ! -f "${MASKUTIL}" ]; then
    echo "WARNING: maskutil.nc not found at ${MASKUTIL}"
    echo "Please ensure ${MASKUTIL} exists or set MASKUTIL in config.sh"
else
    echo "Found maskutil: ${MASKUTIL}"
fi

echo "=== [4/4] Download and staging complete ==="
echo "All raw data staged in ${RAW_DIR}"
