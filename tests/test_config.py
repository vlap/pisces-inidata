"""
Tests for pisces_inidata.config module.
"""

import os
import tempfile
from pisces_inidata.config import load_config, validate_config


def test_default_config():
    cfg = load_config("non_existent_file.cfg")
    assert cfg['PRODUCT_NO3'] == 'woa23'
    assert cfg['PRODUCT_DOC'] == 'panaiotis2024'
    assert validate_config(cfg) is True


def test_custom_config_parsing():
    with tempfile.NamedTemporaryFile('w', delete=False) as f:
        f.write("# Sample config\n")
        f.write('PRODUCT_NO3="${PRODUCT_NO3:-woa2009}"\n')
        f.write('PRODUCT_DOC="panaiotis2024"\n')
        f.write('PRODUCT_TALK="glodap_v2_2016b"\n')
        f_name = f.name

    try:
        cfg = load_config(f_name)
        assert cfg['PRODUCT_NO3'] == 'woa2009'
        assert cfg['PRODUCT_DOC'] == 'panaiotis2024'
        assert cfg['PRODUCT_TALK'] == 'glodap_v2_2016b'
        assert validate_config(cfg) is True
    finally:
        if os.path.exists(f_name):
            os.remove(f_name)


def test_invalid_product_validation():
    bad_cfg = {'PRODUCT_NO3': 'invalid_product_xyz'}
    assert validate_config(bad_cfg) is False
