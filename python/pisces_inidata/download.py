"""
Download and Stage Raw Observational Datasets for PISCES Inidata.
Inspects sources.yaml to selectively fetch only the required raw climatologies
(WOA23, GLODAP, Panaïotis DOC, Official SETTE inputs).
"""

import os
import tarfile
import urllib.request
from typing import Optional
from pisces_inidata.config import load_config

WOA23_BASE = "https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA"
GLODAP_V2_URL = (
    "https://www.ncei.noaa.gov/data/oceans/ncei/ocads/data/0162565/mapped/"
    "GLODAPv2.2016b_MappedClimatologies.tar.gz"
)
OFFICIAL_JASMIN_URL = (
    "https://gws-access.jasmin.ac.uk/public/nemo/sette_inputs/extras/"
    "ORCA2_INPUTS_PISCES_v5.0.0.tar.gz"
)

WOA23_VARS = {
    'NO3': ('nitrate', 'n'),
    'PO4': ('phosphate', 'p'),
    'Si': ('silicate', 'i'),
    'O2': ('oxygen', 'o'),
}


def download_file(url: str, dest_path: str, dry_run: bool = False) -> bool:
    """
    Downloads a remote file via HTTP/HTTPS if not already present.
    Uses atomic .tmp file staging to prevent corrupted partial files.
    """
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        print(f"  [EXISTS] {os.path.basename(dest_path)}")
        return False

    print(f"  [FETCH] {url} -> {dest_path}")
    if dry_run:
        return True

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    tmp_path = dest_path + ".tmp"
    try:
        urllib.request.urlretrieve(url, tmp_path)
        os.rename(tmp_path, dest_path)
        return True
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise RuntimeError(f"Failed to download {url}: {e}") from e


def extract_tar(tar_path: str, extract_dir: str, strip_components: int = 0, dry_run: bool = False):
    """
    Extracts a tar/tar.gz archive into extract_dir, optionally stripping leading directories.
    """
    print(f"  [EXTRACT] {os.path.basename(tar_path)} -> {extract_dir}")
    if dry_run:
        return

    os.makedirs(extract_dir, exist_ok=True)
    with tarfile.open(tar_path, "r:*") as tar:
        for member in tar.getmembers():
            if strip_components > 0:
                parts = member.name.split("/", strip_components)
                if len(parts) <= strip_components:
                    continue
                member.name = parts[-1]
            tar.extract(member, path=extract_dir)


def download_woa23_tracer(var_name: str, code: str, folder: str, raw_dir: str, dry_run: bool = False):
    """
    Downloads full 12-month + annual WOA23 files for a specific tracer.
    """
    target_dir = os.path.join(raw_dir, "woa23", folder)
    print(f"\nChecking WOA23 {var_name} ({folder})...")
    for m in [f"{i:02d}" for i in range(13)]:
        fname = f"woa23_all_{code}{m}_01.nc"
        dest = os.path.join(target_dir, fname)
        url = f"{WOA23_BASE}/{folder}/netcdf/all/1.00/{fname}"
        download_file(url, dest, dry_run=dry_run)


def download_official_nemo_inputs(raw_dir: str, dry_run: bool = False):
    """
    Downloads and extracts the official NEMO/PISCES input package from JASMIN.
    Provides baseline forcings (dust, ndep, par, rivers, bathy, hydrofe) and unmasked fields.
    """
    from pisces_inidata.catalog import load_catalog, resolve_package_dir
    cat = load_catalog()
    pkg = cat.get("packages", {}).get("official_nemo_inputs", {})
    target_dir = resolve_package_dir("official_nemo_inputs", raw_dir=raw_dir)
    tar_name = pkg.get("archive", "ORCA2_INPUTS_PISCES_v5.0.0.tar.gz")
    tar_path = os.path.join(raw_dir, tar_name)
    url = pkg.get("url", OFFICIAL_JASMIN_URL)
    key_name = pkg.get("key_file", "data_FER_nomask.nc")
    key_file = os.path.join(target_dir, key_name)

    print("\nChecking Official NEMO PISCES inputs package...")
    if os.path.exists(key_file):
        print(f"  [EXISTS] Official inputs already present in {target_dir}")
        return

    candidate_urls = [url]
    if OFFICIAL_JASMIN_URL not in candidate_urls:
        candidate_urls.append(OFFICIAL_JASMIN_URL)

    downloaded = False
    last_err = None
    for cand_url in candidate_urls:
        try:
            download_file(cand_url, tar_path, dry_run=dry_run)
            downloaded = True
            break
        except Exception as exc:
            last_err = exc
            print(f"  [WARN] Download from {cand_url} failed: {exc}")

    if not downloaded and not dry_run:
        raise RuntimeError(f"Failed to download official NEMO inputs archive: {last_err}") from last_err

    if not dry_run and os.path.exists(tar_path):
        extract_tar(tar_path, target_dir, strip_components=1, dry_run=dry_run)


def download_glodap(raw_dir: str, dry_run: bool = False):
    """
    Downloads 3D gridded GLODAP mapped climatologies.
    """
    target_dir = os.path.join(raw_dir, "glodap_v2")
    key_file = os.path.join(target_dir, "GLODAPv2.2016b.TAlk.nc")
    tar_path = os.path.join(target_dir, "GLODAPv2.2016b_MappedClimatologies.tar.gz")

    print("\nChecking GLODAP (v2.2016b)...")
    if os.path.exists(key_file):
        print(f"  [EXISTS] GLODAPv2 already extracted in {target_dir}")
        return

    download_file(GLODAP_V2_URL, tar_path, dry_run=dry_run)
    if not dry_run and os.path.exists(tar_path):
        extract_tar(tar_path, target_dir, strip_components=0, dry_run=dry_run)


def download_sources(
    config_file: Optional[str] = None,
    raw_dir: Optional[str] = None,
    dry_run: bool = False,
    pack: Optional[str] = None,
    preset: Optional[str] = None,
) -> int:
    """
    Orchestrates dataset downloading according to user's sources.yaml configuration or pack.
    """
    active_pack = preset if preset is not None else pack
    config = load_config(config_file or "sources.yaml", pack=active_pack)
    workspace = os.environ.get("PISCES_WORKSPACE")
    default_raw = (
        os.path.join(workspace, "shared", "raw")
        if workspace
        else os.environ.get("RAW_DIR", os.path.join(os.getcwd(), "pisces_raw_sources"))
    )
    effective_raw = raw_dir or default_raw
    pack_name = config.get("INIDATA_PACK", config.get("INIDATA_PRESET", "ece4"))

    print("=" * 78)
    print(" PISCES INIDATA: OBSERVATIONAL SOURCE DATASET ACQUISITION")
    print("=" * 78)
    print(f"Target Directory : {effective_raw}")
    print(f"Configuration    : {config_file or 'sources.yaml'}")
    print(f"Active Pack      : {pack_name}")
    print(f"Dry-run Mode     : {'ENABLED' if dry_run else 'DISABLED'}")
    print("=" * 78)

    os.makedirs(effective_raw, exist_ok=True)

    # 1. Official NEMO PISCES inputs package (always needed for forcings & iron)
    download_official_nemo_inputs(effective_raw, dry_run=dry_run)

    # 2. WOA23 Nutrients & Oxygen
    for var, (folder, code) in WOA23_VARS.items():
        chosen = config.get(f"PRODUCT_{var}", "woa23")
        if chosen == "woa23":
            download_woa23_tracer(var, code, folder, effective_raw, dry_run=dry_run)

    # 3. GLODAP Carbon Chemistry (TALK, TDIC, PiDIC)
    carbon_products = [
        config.get("PRODUCT_TALK", "glodap_v2_2016b"),
        config.get("PRODUCT_TDIC", "glodap_v2_2016b"),
        config.get("PRODUCT_PiDIC", "glodap_v2_2016b"),
    ]
    if any("glodap" in p.lower() for p in carbon_products):
        download_glodap(effective_raw, dry_run=dry_run)

    # 4. Panaïotis et al. (2024) DOC Climatology
    if config.get("PRODUCT_DOC", "panaiotis2024") == "panaiotis2024":
        doc_dir = os.path.join(effective_raw, "panaiotis2024_doc")
        doc_nc = os.path.join(doc_dir, "panaiotis2024_doc_1deg.nc")
        print("\nChecking Panaïotis et al. (2024) DOC climatology...")
        if os.path.exists(doc_nc):
            print(f"  [EXISTS] DOC NetCDF already built at {doc_nc}")
        else:
            if dry_run:
                print(f"  [FETCH/BUILD] Would download CSVs and build {doc_nc}")
            else:
                print(f"  [BUILD] Generating {doc_nc} from SEANOE CSVs...")
                from pisces_inidata.doc import build_doc_climatology
                build_doc_climatology(doc_dir, doc_nc)

    print("\n" + "=" * 78)
    print(" SOURCE DATASET ACQUISITION COMPLETE")
    print("=" * 78)
    return 0
