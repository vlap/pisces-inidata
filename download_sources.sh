#!/usr/bin/env bash
# ==============================================================================
# download_sources.sh
# Fetch and prepare raw input source datasets for PISCES inidata:
#   1) Raw WOA2009 (NOAA NCEI Accession 0094866)
#   2) Raw GLODAPv1.1 (NOAA NCEI Accession 0001644)
#   3) Official NEMO PISCES inputs package (JASMIN baseline fallback)
# Run on an interactive node with outgoing internet access (e.g., hub04 / hub02).
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

echo "=== [1/4] Preparing directories ==="
mkdir -p "${RAW_DIR}" "${OUTPUT_DIR}" "${WEIGHTS_DIR}" "${LOG_DIR}"
WOA09_DIR="${RAW_DIR}/woa2009"
GLODAP_DIR="${RAW_DIR}/glodap_v1.1"
OFFICIAL_DIR="${RAW_DIR}/official_v5.0.0"

mkdir -p "${WOA09_DIR}" "${GLODAP_DIR}" "${OFFICIAL_DIR}"

echo "Working directory: ${WORK_DIR}"
echo "Raw sources directory: ${RAW_DIR}"

# ------------------------------------------------------------------------------
# 2. Download Raw WOA2009 from NOAA NCEI (Accession 0094866)
# ------------------------------------------------------------------------------
echo "=== [2/4] Fetching Raw WOA2009 from NOAA NCEI ==="
WOA_BASE="https://www.ncei.noaa.gov/data/oceans/ncei/archive/data/0094866/disc_contents/NODC-DVD-14_discImage_DVD/DATA"

download_woa_var() {
    local var_folder="$1"  # nitrate, phosphate, silicate, oxygen
    local prefix="$2"      # n, p, k, o
    local target_subdir="${WOA09_DIR}/${var_folder}"
    mkdir -p "${target_subdir}"

    echo "Downloading WOA2009 ${var_folder} monthly fields..."
    for m in $(seq -w 1 12); do
        local fname="${prefix}${m}an1.gz"
        local url="${WOA_BASE}/${var_folder}/grid/${fname}"
        if [ ! -f "${target_subdir}/${fname}" ]; then
            echo "  Fetching ${fname}..."
            curl -fSL "${url}" -o "${target_subdir}/${fname}"
        fi
    done
    # Also fetch annual field
    local fname_ann="${prefix}00an1.gz"
    local url_ann="${WOA_BASE}/${var_folder}/grid/${fname_ann}"
    if [ ! -f "${target_subdir}/${fname_ann}" ]; then
        echo "  Fetching ${fname_ann} (annual)..."
        curl -fSL "${url_ann}" -o "${target_subdir}/${fname_ann}"
    fi
}

download_woa_var "nitrate" "n"
download_woa_var "phosphate" "p"
download_woa_var "silicate" "i"
download_woa_var "oxygen" "o"

# ------------------------------------------------------------------------------
# 3. Download Raw GLODAP Mapped Climatology from NOAA NCEI OCADS
# ------------------------------------------------------------------------------
echo "=== [3/4] Fetching Raw GLODAP Mapped Climatology from NOAA NCEI ==="
GLODAP_URL="https://www.ncei.noaa.gov/data/oceans/ncei/ocads/data/0162565/mapped/GLODAPv2.2016b_MappedClimatologies.tar.gz"
GLODAP_TAR="${GLODAP_DIR}/GLODAP_MappedClimatologies.tar.gz"

if [ ! -f "${GLODAP_DIR}/GLODAPv2.2016b.TAlk.nc" ]; then
    if [ ! -f "${GLODAP_TAR}" ]; then
        echo "Fetching GLODAP mapped climatologies..."
        curl -fSL "${GLODAP_URL}" -o "${GLODAP_TAR}"
    fi
    echo "Extracting GLODAP archive..."
    tar -xzf "${GLODAP_TAR}" -C "${GLODAP_DIR}"
    echo "GLODAP extraction complete: $(ls -l ${GLODAP_DIR}/*.nc 2>/dev/null || true)"
else
    echo "GLODAP NetCDF files already present in ${GLODAP_DIR}"
fi

# ------------------------------------------------------------------------------
# 4. Download Official NEMO PISCES inputs package (JASMIN baseline fallback)
# ------------------------------------------------------------------------------
echo "=== [4/4] Fetching Official NEMO PISCES inputs package ==="
PISCES_TAR="${RAW_DIR}/ORCA2_INPUTS_PISCES_v5.0.0.tar.gz"
if [ ! -d "${OFFICIAL_DIR}/data_NO3_nomask.nc" ]; then
    if [ ! -f "${PISCES_TAR}" ]; then
        echo "Fetching ${JASMIN_PISCES_V5_URL}..."
        curl -fSL "${JASMIN_PISCES_V5_URL}" -o "${PISCES_TAR}"
    fi
    echo "Extracting official PISCES inputs..."
    tar -xzf "${PISCES_TAR}" -C "${OFFICIAL_DIR}" --strip-components=1 || cp -rf "${RAW_DIR}"/../ORCA2_INPUTS_PISCES_v4.2.0/* "${OFFICIAL_DIR}/" || true
fi

echo "=== All raw datasets downloaded and staged in ${RAW_DIR} ==="
