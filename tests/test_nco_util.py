from pisces_inidata.nco_util import get_cdo


def test_get_cdo():
    cdo = get_cdo(threads=2)
    assert cdo is not None
    ver = cdo.version()
    assert isinstance(ver, str)
    assert len(ver) > 0


def test_get_cdo_options():
    cdo = get_cdo(threads=4, options=["-b", "F32"])
    assert cdo is not None
    assert "-P 4" in cdo.env.get("CDO_OPTS", "")
    assert "-b F32" in cdo.env.get("CDO_OPTS", "")
    assert "-L" in cdo.env.get("CDO_OPTS", "")
