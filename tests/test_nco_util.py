import numpy as np
import netCDF4 as nc
from pisces_inidata.nco_util import get_nco, get_cdo, NetCDF4NcoFallback


def test_get_cdo():
    cdo = get_cdo(threads=2)
    assert cdo is not None
    ver = cdo.version()
    assert isinstance(ver, str)
    assert len(ver) > 0


def test_get_nco():
    nco = get_nco()
    assert nco is not None
    assert hasattr(nco, "ncrename")
    assert hasattr(nco, "ncatted")
    assert hasattr(nco, "ncks")
    assert hasattr(nco, "ncwa")


def test_netcdf4_nco_fallback(tmp_path):
    test_nc = str(tmp_path / "sample.nc")
    with nc.Dataset(test_nc, "w") as ds:
        ds.createDimension("time", 1)
        ds.createDimension("lat", 4)
        ds.createDimension("lon", 5)
        v = ds.createVariable("temp", "f4", ("time", "lat", "lon"))
        v[:] = np.arange(20).reshape(1, 4, 5)
        v.units = "K"

    fallback = NetCDF4NcoFallback()

    # Test ncatted
    fallback.ncatted(test_nc, options=["-O", "-a", "units,temp,m,c,celsius", "-a", "title,global,c,c,Test Dataset"])
    with nc.Dataset(test_nc, "r") as ds:
        assert ds.variables["temp"].units == "celsius"
        assert ds.title == "Test Dataset"

    # Test ncrename
    fallback.ncrename(test_nc, options=["-v", "temp,temperature"])
    with nc.Dataset(test_nc, "r") as ds:
        assert "temperature" in ds.variables
        assert "temp" not in ds.variables

    # Test ncwa (squeeze time dimension)
    fallback.ncwa(test_nc, options=["-O", "-a", "time"])
    with nc.Dataset(test_nc, "r") as ds:
        assert ds.variables["temperature"].shape == (4, 5)

    # Test ncks extraction
    extract_nc = str(tmp_path / "extract.nc")
    fallback.ncks(test_nc, extract_nc, options=["-O", "-v", "temperature"])
    with nc.Dataset(extract_nc, "r") as ds:
        assert "temperature" in ds.variables
        assert ds.variables["temperature"].shape == (4, 5)
