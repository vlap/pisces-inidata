#!/usr/bin/env bash
# ==============================================================================
# download_sources.sh
# Fetch and prepare raw input source datasets for PISCES inidata:
#   1) Modern WOA23 (NOAA NCEI NetCDF-4, 1.00 degree, 102 levels)
#   2) GLODAPv2.2016b mapped climatologies (NOAA NCEI OCADS)
#   3) Official NEMO PISCES inputs package (JASMIN baseline fallback)
#   4) Optional Legacy WOA2009 (NOAA NCEI Accession 0094866)
# Run on an interactive node with outgoing internet access (e.g., hub04 / hub02).
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

echo "=== [1/5] Preparing raw directories ==="
mkdir -p "${RAW_DIR}" "${OUTPUT_DIR}" "${WEIGHTS_DIR}" "${LOG_DIR}"
WOA23_DIR="${RAW_DIR}/woa23"
GLODAP_V2_DIR="${RAW_DIR}/glodap_v2"
OFFICIAL_DIR="${RAW_DIR}/official_v5.0.0"
WOA09_DIR="${RAW_DIR}/woa2009"

mkdir -p "${WOA23_DIR}" "${GLODAP_V2_DIR}" "${OFFICIAL_DIR}"

echo "Working directory: ${WORK_DIR}"
echo "Raw sources directory: ${RAW_DIR}"

# ------------------------------------------------------------------------------
# 2. Download Modern WOA23 from NOAA NCEI (NetCDF-4, 1.00 degree, 102 levels)
# ------------------------------------------------------------------------------
echo "=== [2/5] Fetching Modern WOA23 from NOAA NCEI ==="
WOA23_BASE="https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA"

download_woa23_var() {
    local var_folder="$1"  # nitrate, phosphate, silicate, oxygen
    local code="$2"        # n, p, i, o
    local target_subdir="${WOA23_DIR}/${var_folder}"
    mkdir -p "${target_subdir}"

    echo "Checking/Downloading WOA23 ${var_folder} (annual + 12 monthly)..."
    for m in 00 $(seq -w 1 12); do
        local fname="woa23_all_${code}${m}_01.nc"
        local dest="${target_subdir}/${fname}"
        local url="${WOA23_BASE}/${var_folder}/netcdf/all/1.00/${fname}"
        if [ ! -s "${dest}" ]; then
            echo "  Fetching ${fname}..."
            curl -fSL "${url}" -o "${dest}.tmp" && mv "${dest}.tmp" "${dest}"
        fi
    done
}

download_woa23_var "nitrate" "n"
download_woa23_var "phosphate" "p"
download_woa23_var "silicate" "i"
download_woa23_var "oxygen" "o"

# ------------------------------------------------------------------------------
# 3. Download Raw GLODAPv2 Mapped Climatology from NOAA NCEI OCADS
# ------------------------------------------------------------------------------
echo "=== [3/5] Fetching Raw GLODAPv2 Mapped Climatology from NOAA NCEI ==="
GLODAP_URL="https://www.ncei.noaa.gov/data/oceans/ncei/ocads/data/0162565/mapped/GLODAPv2.2016b_MappedClimatologies.tar.gz"
GLODAP_TAR="${GLODAP_V2_DIR}/GLODAPv2.2016b_MappedClimatologies.tar.gz"

if [ ! -f "${GLODAP_V2_DIR}/GLODAPv2.2016b.TAlk.nc" ]; then
    if [ ! -f "${GLODAP_TAR}" ]; then
        echo "Fetching GLODAP mapped climatologies..."
        curl -fSL "${GLODAP_URL}" -o "${GLODAP_TAR}"
    fi
    echo "Extracting GLODAP archive..."
    tar -xzf "${GLODAP_TAR}" -C "${GLODAP_V2_DIR}"
    echo "GLODAP extraction complete: $(ls -l ${GLODAP_V2_DIR}/*.nc 2>/dev/null || true)"
else
    echo "GLODAP NetCDF files already present in ${GLODAP_V2_DIR}"
fi

# ------------------------------------------------------------------------------
# 4. Download Official NEMO PISCES inputs package (v5.0.0 fallback)
# ------------------------------------------------------------------------------
echo "=== [4/5] Fetching Official NEMO PISCES inputs package ==="
PISCES_TAR="${RAW_DIR}/ORCA2_INPUTS_PISCES_v5.0.0.tar.gz"
if [ ! -d "${OFFICIAL_DIR}/data_NO3_nomask.nc" ] && [ ! -f "${OFFICIAL_DIR}/data_NO3_nomask.nc" ]; then
    if [ ! -f "${PISCES_TAR}" ]; then
        echo "Fetching ${JASMIN_PISCES_V5_URL}..."
        curl -fSL "${JASMIN_PISCES_V5_URL}" -o "${PISCES_TAR}"
    fi
    echo "Extracting official PISCES inputs..."
    tar -xzf "${PISCES_TAR}" -C "${OFFICIAL_DIR}" --strip-components=1
fi

# ------------------------------------------------------------------------------
# 5. Optional Legacy WOA2009 (Only if explicitly requested)
# ------------------------------------------------------------------------------
DOWNLOAD_LEGACY="${DOWNLOAD_LEGACY:-false}"
if [ "${DOWNLOAD_LEGACY}" = "true" ]; then
    echo "=== [5/5] Fetching Legacy WOA2009 from NOAA NCEI ==="
    mkdir -p "${WOA09_DIR}"
    WOA09_BASE="https://www.ncei.noaa.gov/data/oceans/ncei/archive/data/0094866/disc_contents/NODC-DVD-14_discImage_DVD/DATA"

    download_woa09_var() {
        local var_folder="$1"
        local prefix="$2"
        local target_subdir="${WOA09_DIR}/${var_folder}"
        mkdir -p "${target_subdir}"

        echo "Downloading WOA2009 ${var_folder} monthly fields..."
        for m in $(seq -w 1 12); do
            local fname="${prefix}${m}an1.gz"
            local url="${WOA09_BASE}/${var_folder}/grid/${fname}"
            if [ ! -f "${target_subdir}/${fname}" ]; then
                echo "  Fetching ${fname}..."
                curl -fSL "${url}" -o "${target_subdir}/${fname}"
            fi
        done
        local fname_ann="${prefix}00an1.gz"
        local url_ann="${WOA09_BASE}/${var_folder}/grid/${fname_ann}"
        if [ ! -f "${target_subdir}/${fname_ann}" ]; then
            echo "  Fetching ${fname_ann} (annual)..."
            curl -fSL "${url_ann}" -o "${target_subdir}/${fname_ann}"
        fi
    }

    download_woa09_var "nitrate" "n"
    download_woa09_var "phosphate" "p"
    download_woa09_var "silicate" "i"
    download_woa09_var "oxygen" "o"
else
    echo "=== [5/5] Skipping Legacy WOA2009 (set DOWNLOAD_LEGACY=true to enable) ==="
fi

echo "=== All raw datasets staged successfully in ${RAW_DIR} ==="
