"""
Download Management Module for PISCES Inidata
Provides download utilities for WOA23, GLODAP, DOC, and Copernicus Marine Service datasets.
"""

import os
import urllib.request
import shutil
from typing import Optional

BASE_WOA23 = "https://www.ncei.noaa.gov/thredds-ocean/fileServer/woa23/DATA"
BASE_OCADS = "https://www.ncei.noaa.gov/data/oceans/ncei/ocads/data/0162565"

SOURCES = {
    'woa23_nitrate': f"{BASE_WOA23}/nitrate/netcdf/all/1.00/woa23_all_n00_01.nc",
    'woa23_phosphate': f"{BASE_WOA23}/phosphate/netcdf/all/1.00/woa23_all_p00_01.nc",
    'woa23_silicate': f"{BASE_WOA23}/silicate/netcdf/all/1.00/woa23_all_i00_01.nc",
    'woa23_oxygen': f"{BASE_WOA23}/oxygen/netcdf/all/1.00/woa23_all_o00_01.nc",
    'glodap_v2_2016b_talk': f"{BASE_OCADS}/GLODAPv2.2016b.TAlk.nc",
    'glodap_v2_2016b_tco2': f"{BASE_OCADS}/GLODAPv2.2016b.TCO2.nc",
    'panaiotis2024_doc': "https://www.seanoe.org/data/00911/101170/data/111812.nc",
}


def download_url(url: str, dest_path: str, force: bool = False) -> str:
    """
    Downloads a file from url to dest_path with progress indication.
    """
    if os.path.exists(dest_path) and not force:
        print(f"File already exists: {dest_path}")
        return dest_path

    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    print(f"Downloading {url} -> {dest_path} ...")

    with urllib.request.urlopen(url) as response, open(dest_path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

    print(f"Download complete: {dest_path} ({os.path.getsize(dest_path)} bytes)")
    return dest_path


def download_cmems_product(
    product_id: str,
    output_directory: str,
    username: Optional[str] = None,
    password: Optional[str] = None
):
    """
    Downloads dataset from Copernicus Marine Service using copernicusmarine Python package if available.
    """
    try:
        import copernicusmarine
    except ImportError:
        raise ImportError(
            "The 'copernicusmarine' package is required to download directly from Copernicus Marine Service.\n"
            "Install it with: pip install 'pisces-inidata[copernicus]' or pip install copernicusmarine"
        )

    print(f"Querying Copernicus Marine for product {product_id}...")
    copernicusmarine.get(
        dataset_id=product_id,
        output_directory=output_directory,
        username=username,
        password=password,
    )
