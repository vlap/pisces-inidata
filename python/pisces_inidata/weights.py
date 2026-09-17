"""
Target Grid Coordinates Extraction & SCRIP Remapping Weights Generation.
Pure Python module replacing scripts/gen_grid_and_weights.sh using python-cdo and pynco.
"""

import os
from typing import Optional, Dict
import netCDF4 as nc
import numpy as np
from pisces_inidata.nco_util import get_cdo
from pisces_inidata.grids import load_grid_config
from pisces_inidata.catalog import resolve_package_dir


def extract_target_grid(
    grid_name: str,
    domain_cfg: str,
    maskutil: str,
    out_target_grid_nc: str,
    raw_dir: Optional[str] = None
) -> str:
    """
    Extracts 2D horizontal coordinates (lon, lat) and ocean mask (tmaskutil) from domain files,
    or falls back to official reference bathy file. Writes CF-compliant target_grid NetCDF.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_target_grid_nc)), exist_ok=True)

    if os.path.isfile(domain_cfg) and os.path.isfile(maskutil):
        with nc.Dataset(domain_cfg, "r") as d_cfg, nc.Dataset(maskutil, "r") as d_mask:
            lon_data = np.squeeze(d_cfg.variables["glamt"][:])
            lat_data = np.squeeze(d_cfg.variables["gphit"][:])
            mask_data = np.squeeze(d_mask.variables["tmaskutil"][:])

            ny, nx = lon_data.shape
            with nc.Dataset(out_target_grid_nc, "w", format="NETCDF4") as out:
                out.createDimension("y", ny)
                out.createDimension("x", nx)

                v_lon = out.createVariable("lon", "f8", ("y", "x"))
                v_lon.units = "degrees_east"
                v_lon.standard_name = "longitude"
                v_lon[:] = lon_data

                v_lat = out.createVariable("lat", "f8", ("y", "x"))
                v_lat.units = "degrees_north"
                v_lat.standard_name = "latitude"
                v_lat[:] = lat_data

                v_mask = out.createVariable("tmaskutil", "i1", ("y", "x"))
                v_mask.coordinates = "lon lat"
                v_mask[:] = mask_data
        return out_target_grid_nc

    # Fallback to reference coordinates
    grid_cfg = load_grid_config(grid_name)
    fallback_rel = grid_cfg.get("fallback_coords_source")
    fallback_path = None
    if fallback_rel:
        effective_raw = raw_dir or os.environ.get("RAW_DIR", os.path.join(os.getcwd(), "pisces_raw_sources"))
        official_dir = resolve_package_dir("official_nemo_inputs", raw_dir=effective_raw)
        cands = [
            os.path.join(effective_raw, fallback_rel),
            os.path.join(official_dir, os.path.basename(fallback_rel)),
            os.path.join(effective_raw, "official_v5.0.0", os.path.basename(fallback_rel))
        ]
        for c in cands:
            if os.path.isfile(c):
                fallback_path = c
                break

    if fallback_path and os.path.isfile(fallback_path):
        with nc.Dataset(fallback_path, "r") as d_fb:
            lon_var = "nav_lon" if "nav_lon" in d_fb.variables else "lon"
            lat_var = "nav_lat" if "nav_lat" in d_fb.variables else "lat"
            mask_var = (
                "bathy" if "bathy" in d_fb.variables
                else ("tmaskutil" if "tmaskutil" in d_fb.variables else None)
            )

            lon_data = np.squeeze(d_fb.variables[lon_var][:])
            lat_data = np.squeeze(d_fb.variables[lat_var][:])
            mask_data = np.squeeze(d_fb.variables[mask_var][:]) if mask_var else np.ones_like(lon_data, dtype=np.int8)

            ny, nx = lon_data.shape
            with nc.Dataset(out_target_grid_nc, "w", format="NETCDF4") as out:
                out.createDimension("y", ny)
                out.createDimension("x", nx)

                v_lon = out.createVariable("lon", "f8", ("y", "x"))
                v_lon.units = "degrees_east"
                v_lon.standard_name = "longitude"
                v_lon[:] = lon_data

                v_lat = out.createVariable("lat", "f8", ("y", "x"))
                v_lat.units = "degrees_north"
                v_lat.standard_name = "latitude"
                v_lat[:] = lat_data

                v_mask = out.createVariable("tmaskutil", "i1", ("y", "x"))
                v_mask.coordinates = "lon lat"
                v_mask[:] = mask_data
        return out_target_grid_nc

    raise FileNotFoundError(
        f"Target domain files not found for grid '{grid_name}'.\n"
        f"Checked DOMAIN_CFG: {domain_cfg}\n"
        f"Checked MASKUTIL:   {maskutil}\n"
        f"Please set DOMAIN_BASE_DIR (or --domain-dir) to your directory containing {grid_name}/domain_cfg.nc."
    )


def compute_target_area(target_grid_nc: str, out_area_nc: str, domain_cfg: Optional[str] = None) -> str:
    """Computes horizontal cell area (e1t * e2t or via CDO spherical gridarea)."""
    cdo = get_cdo()
    os.makedirs(os.path.dirname(os.path.abspath(out_area_nc)), exist_ok=True)
    if domain_cfg and os.path.isfile(domain_cfg):
        with nc.Dataset(domain_cfg, "r") as ds_cfg, nc.Dataset(target_grid_nc, "r") as ds_grid:
            e1t = np.squeeze(ds_cfg.variables["e1t"][:])
            e2t = np.squeeze(ds_cfg.variables["e2t"][:])
            area_data = (e1t * e2t).astype(np.float64)
            ny, nx = area_data.shape

            with nc.Dataset(out_area_nc, "w", format="NETCDF4") as out:
                out.createDimension("y", ny)
                out.createDimension("x", nx)

                v_lon = out.createVariable("lon", "f8", ("y", "x"))
                v_lon.units = "degrees_east"
                v_lon.standard_name = "longitude"
                v_lon[:] = ds_grid.variables["lon"][:]

                v_lat = out.createVariable("lat", "f8", ("y", "x"))
                v_lat.units = "degrees_north"
                v_lat.standard_name = "latitude"
                v_lat[:] = ds_grid.variables["lat"][:]

                v_area = out.createVariable("cell_area", "f8", ("y", "x"))
                v_area.units = "m2"
                v_area.standard_name = "cell_area"
                v_area.coordinates = "lon lat"
                v_area[:] = area_data
        return out_area_nc
    else:
        try:
            cdo.gridarea(input=target_grid_nc, output=out_area_nc)
        except Exception:
            cdo.setgrid(target_grid_nc, input="-gridarea -topo,r360x180", output=out_area_nc)
        return out_area_nc


def generate_scrip_weights(target_grid_nc: str, out_weights_nc: str, method: str = "bilinear") -> str:
    """Precomputes SCRIP remapping weights from 1x1 regular grid to target grid using CDO."""
    cdo = get_cdo()
    os.makedirs(os.path.dirname(os.path.abspath(out_weights_nc)), exist_ok=True)
    if method == "bilinear":
        cdo.genbil(target_grid_nc, input="-topo,r360x180", output=out_weights_nc)
    elif method in ("distance", "distance_conservative", "dis"):
        cdo.gendis(target_grid_nc, input="-topo,r360x180", output=out_weights_nc)
    elif method in ("nearest_neighbor", "nn"):
        cdo.remapnn(target_grid_nc, input="-topo,r360x180", output=out_weights_nc)
    else:
        raise ValueError(f"Unknown remapping method: {method}")
    return out_weights_nc


def ensure_grid_and_weights(
    grid_name: str,
    domain_dir: Optional[str] = None,
    raw_dir: Optional[str] = None,
    weights_dir: Optional[str] = None,
    force: bool = False
) -> Dict[str, str]:
    """
    High-level orchestrator: ensures target_grid.nc, weights_bilin.nc, and weights_dis.nc are ready.
    """
    workspace = os.environ.get("PISCES_WORKSPACE")
    if workspace:
        base_grid_dir = os.path.join(workspace, "grids", grid_name)
    else:
        base_grid_dir = os.path.join(os.getcwd(), "grids", grid_name)
    w_dir = weights_dir or os.path.join(base_grid_dir, "weights")
    os.makedirs(w_dir, exist_ok=True)

    target_grid_nc = os.path.join(w_dir, f"target_grid_{grid_name}.nc")
    weights_bilin_nc = os.path.join(w_dir, f"weights_r360x180_to_{grid_name}_bilin.nc")
    weights_dis_nc = os.path.join(w_dir, f"weights_r360x180_to_{grid_name}_dis.nc")
    target_area_nc = os.path.join(w_dir, f"target_area_{grid_name}.nc")

    # 1. Target Grid Extraction
    if force or not os.path.isfile(target_grid_nc):
        base_domain = domain_dir or os.environ.get("DOMAIN_BASE_DIR", os.path.join(os.getcwd(), "domain"))
        domain_cfg = os.path.join(base_domain, grid_name, "domain_cfg.nc")
        maskutil = os.path.join(base_domain, grid_name, "maskutil.nc")
        print(f"Extracting target grid description for {grid_name}...")
        extract_target_grid(grid_name, domain_cfg, maskutil, target_grid_nc, raw_dir=raw_dir)

    # 2. Cell Area
    if force or not os.path.isfile(target_area_nc):
        base_domain = domain_dir or os.environ.get("DOMAIN_BASE_DIR", os.path.join(os.getcwd(), "domain"))
        domain_cfg = os.path.join(base_domain, grid_name, "domain_cfg.nc")
        cfg_arg = domain_cfg if os.path.isfile(domain_cfg) else None
        compute_target_area(target_grid_nc, target_area_nc, domain_cfg=cfg_arg)

    # 3. Bilinear Weights
    if force or not os.path.isfile(weights_bilin_nc):
        print(f"Generating bilinear remapping weights (r360x180 -> {grid_name})...")
        generate_scrip_weights(target_grid_nc, weights_bilin_nc, method="bilinear")

    # 4. Distance-Weighted Weights
    if force or not os.path.isfile(weights_dis_nc):
        print(f"Generating distance-weighted weights (r360x180 -> {grid_name})...")
        generate_scrip_weights(target_grid_nc, weights_dis_nc, method="distance")

    return {
        "target_grid": target_grid_nc,
        "target_grid_nc": target_grid_nc,
        "weights_bilin": weights_bilin_nc,
        "weights_bilin_nc": weights_bilin_nc,
        "weights_dis": weights_dis_nc,
        "weights_dis_nc": weights_dis_nc,
        "target_area": target_area_nc,
        "target_area_nc": target_area_nc,
    }
