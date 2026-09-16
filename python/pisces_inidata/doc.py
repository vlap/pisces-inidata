#!/usr/bin/env python3
"""
prepare_panaiotis2024_doc.py
Convert Panaïotis et al. (2024) SEANOE machine learning-based DOC climatology
from layer-wise tabular CSVs into a standard CF-compliant 3D/4D NetCDF climatology
on a regular 1x1 degree grid with 12 monthly timesteps and abyssal 6000m padding.

Reference:
    Panaïotis Thelma, Wilson Jamie, Cael BB (2024).
    A machine learning-based dissolved organic carbon climatology.
    SEANOE. https://doi.org/10.17882/101170
"""

import os
import csv
import numpy as np
import netCDF4 as nc
from pisces_inidata.download import download_file
from pisces_inidata.provenance import create_cf_coordinates

SEANOE_ANNUAL_URL = "https://www.seanoe.org/data/00900/101170/data/111994.csv"
SEANOE_SEASONAL_URL = "https://www.seanoe.org/data/00900/101170/data/111995.csv"

# Representative layer mid-depths (meters)
# Layer 1: Surface (0 - 10 m) -> 5 m
# Layer 2: Epipelagic (10 - 200 m) -> 100 m
# Layer 3: Mesopelagic (200 - 1000 m) -> 600 m
# Layer 4: Bathypelagic (> 1000 m) -> 2500 m
# Layer 5: Abyssal padding -> 6000 m (replicated from bathypelagic)
DEPTH_LEVELS = [5.0, 100.0, 600.0, 2500.0, 6000.0]

# Mapping from calendar month (1-12) to meteorological season (1=DJF, 2=MAM, 3=JJA, 4=SON)
MONTH_TO_SEASON = {
    1: 1, 2: 1, 12: 1,  # DJF
    3: 2, 4: 2, 5: 2,   # MAM
    6: 3, 7: 3, 8: 3,   # JJA
    9: 4, 10: 4, 11: 4  # SON
}


def build_doc_climatology(raw_dir, output_nc):
    os.makedirs(raw_dir, exist_ok=True)
    ann_csv = os.path.join(raw_dir, "annual_climatologies.csv")
    sea_csv = os.path.join(raw_dir, "seasonal_climatologies.csv")

    download_file(SEANOE_ANNUAL_URL, ann_csv)
    download_file(SEANOE_SEASONAL_URL, sea_csv)

    # Standard global 1x1 grid
    lons = np.arange(-179.5, 180.5, 1.0)  # 360 values: -179.5 to 179.5
    lats = np.arange(-89.5, 90.5, 1.0)    # 180 values: -89.5 to 89.5
    nlons = len(lons)
    nlats = len(lats)
    ndepths = len(DEPTH_LEVELS)
    ntimes = 12

    # Map lon, lat to grid indices
    lon_idx = {float(np.round(lon, 2)): i for i, lon in enumerate(lons)}
    lat_idx = {float(np.round(lat, 2)): j for j, lat in enumerate(lats)}

    # Pre-allocate 3D annual layers: (depth, lat, lon)
    fill_val = 1.0e20
    ann_grid = np.full((ndepths, nlats, nlons), fill_val, dtype=np.float32)

    def parse_float(val: str) -> float:
        if not val or val.strip() in ("", "NA", "NaN", "nan"):
            return fill_val
        try:
            return float(val)
        except ValueError:
            return fill_val

    print("Loading annual climatology...")
    with open(ann_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lon = round(float(row['lon']), 2)
            lat = round(float(row['lat']), 2)
            if lon in lon_idx and lat in lat_idx:
                i = lon_idx[lon]
                j = lat_idx[lat]

                surf = parse_float(row.get('surf_doc_avg', ''))
                epi = parse_float(row.get('epi_doc_avg', ''))
                meso = parse_float(row.get('meso_doc_avg', ''))
                bathy = parse_float(row.get('bathy_doc_avg', ''))

                ann_grid[0, j, i] = surf
                ann_grid[1, j, i] = epi
                ann_grid[2, j, i] = meso
                ann_grid[3, j, i] = bathy
                ann_grid[4, j, i] = bathy  # Abyssal 6000m padding replicates bathypelagic layer

    # Pre-allocate 4 seasonal surface grids: (season, lat, lon)
    season_surf = np.full((5, nlats, nlons), fill_val, dtype=np.float32)
    print("Loading seasonal climatology...")
    with open(sea_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            s = int(row['season'])
            lon = round(float(row['lon']), 2)
            lat = round(float(row['lat']), 2)
            if 1 <= s <= 4 and lon in lon_idx and lat in lat_idx:
                i = lon_idx[lon]
                j = lat_idx[lat]
                season_surf[s, j, i] = parse_float(row.get('surf_doc_avg', ''))

    # Assemble 4D monthly field: (time=12, depth=5, lat=180, lon=360)
    print("Assembling 12 monthly climatological timesteps...")
    doc_4d = np.full((ntimes, ndepths, nlats, nlons), fill_val, dtype=np.float32)

    for m in range(1, 13):
        t = m - 1
        s = MONTH_TO_SEASON[m]

        # Subsurface levels (depths 1..4) are annual
        doc_4d[t, 1:, :, :] = ann_grid[1:, :, :]

        # Surface level (depth 0): use seasonal if available, fallback to annual
        surf_s = season_surf[s, :, :]
        surf_ann = ann_grid[0, :, :]
        # Combine: where seasonal is valid use it, else annual
        valid_s = (surf_s != fill_val)
        valid_ann = (surf_ann != fill_val)

        surf_combined = np.full((nlats, nlons), fill_val, dtype=np.float32)
        surf_combined[valid_ann] = surf_ann[valid_ann]
        surf_combined[valid_s] = surf_s[valid_s]

        doc_4d[t, 0, :, :] = surf_combined

    # Write CF-compliant NetCDF
    print(f"Writing CF-compliant NetCDF: {output_nc}...")
    os.makedirs(os.path.dirname(os.path.abspath(output_nc)), exist_ok=True)

    with nc.Dataset(output_nc, 'w', format='NETCDF4') as ds:
        # Global attributes
        ds.title = "Machine learning-based Dissolved Organic Carbon (DOC) Climatology"
        ds.institution = "National Oceanography Centre & University of Liverpool"
        ds.source = "Panaïotis et al. (2024), SEANOE doi:10.17882/101170"
        ds.references = "https://doi.org/10.17882/101170"
        ds.Conventions = "CF-1.6"

        # Dimensions & CF-compliant coordinates
        create_cf_coordinates(
            ds,
            lons=lons,
            lats=lats,
            depths=np.array(DEPTH_LEVELS, dtype=np.float32),
            times=np.arange(1, 13, dtype=np.float32),
            time_units="months since 0000-01-01",
        )

        # Main data variable
        vdoc = ds.createVariable('DOC', 'f4', ('time_counter', 'depth', 'lat', 'lon'),
                                 fill_value=fill_val, zlib=True, complevel=4)
        vdoc.units = "umol C/L"
        vdoc.long_name = "Dissolved Organic Carbon"
        vdoc.standard_name = "mole_concentration_of_dissolved_organic_carbon_in_sea_water"
        vdoc.coordinates = "time_counter depth lat lon"
        vdoc[:] = doc_4d

    print(f"Successfully generated {output_nc}")
