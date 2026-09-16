"""
Tests for pisces_inidata.config module (sources.yaml).
"""

import os
import tempfile
from pisces_inidata.config import load_config, validate_config, export_env_commands


def test_default_config():
    cfg = load_config("sources.yaml")
    assert cfg['PRODUCT_NO3'] == 'woa23'
    assert cfg['PRODUCT_DOC'] == 'panaiotis2024'
    assert cfg['PRODUCT_TALK'] == 'glodap_v2_2016b'
    assert cfg['PRODUCT_Fer'] == 'sette_nomask'
    assert cfg['PRODUCT_DUST'] == 'sette_orca2'
    assert validate_config(cfg) is True


def test_custom_yaml_parsing():
    content = """
tracers_3d:
  NO3: woa2009
  DOC: sette_nomask
  TALK: glodap_v1
boundary_forcings:
  dust: sette_orca2
"""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(content)
        f_name = f.name

    try:
        cfg = load_config(f_name)
        assert cfg['PRODUCT_NO3'] == 'woa2009'
        assert cfg['PRODUCT_DOC'] == 'sette_nomask'
        assert cfg['PRODUCT_TALK'] == 'glodap_v1'
        assert cfg['PRODUCT_DUST'] == 'sette_orca2'
        assert validate_config(cfg) is True
    finally:
        if os.path.exists(f_name):
            os.remove(f_name)


def test_invalid_product_validation():
    bad_cfg = {'PRODUCT_NO3': 'invalid_product_xyz'}
    assert validate_config(bad_cfg) is False
    assert validate_config({'PRODUCT_TALK': 'glodap_v3'}) is False


def test_ece3_rejected_as_source():
    # EC-Earth3 inidata must never be allowed as an input source; it is only for verification
    assert validate_config({'PRODUCT_NO3': 'ece3'}) is False
    assert validate_config({'PRODUCT_DOC': 'ece3'}) is False
    assert validate_config({'PRODUCT_Fer': 'ece3'}) is False
    assert validate_config({'PRODUCT_DUST': 'ece3'}) is False


def test_export_env_commands():
    cfg = {'PRODUCT_NO3': 'woa23', 'PRODUCT_DOC': 'panaiotis2024'}
    export_str = export_env_commands(cfg)
    assert 'export PRODUCT_NO3="woa23"' in export_str
    assert 'export PRODUCT_DOC="panaiotis2024"' in export_str


def test_yaml_comments_and_formatting():
    content = """
tracers_3d:
  NO3: woa2009 # test inline comment
  TALK: glodap_v1
boundary_forcings:
  dust: sette_orca2
"""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(content)
        f_name = f.name

    try:
        cfg = load_config(f_name)
        assert cfg['PRODUCT_NO3'] == 'woa2009'
        assert cfg['PRODUCT_TALK'] == 'glodap_v1'
        assert cfg['PRODUCT_DUST'] == 'sette_orca2'
    finally:
        if os.path.exists(f_name):
            os.remove(f_name)


def test_presets():
    # ECE4 preset (modern EC-Earth4)
    cfg_ece4 = load_config("sources.yaml", preset="ece4")
    assert cfg_ece4['INIDATA_PRESET'] == 'ece4'
    assert cfg_ece4['PRODUCT_NO3'] == 'woa23'
    assert cfg_ece4['PRODUCT_DOC'] == 'panaiotis2024'

    # ECE3 preset (observational sources used in EC-Earth3)
    cfg_ece3 = load_config("sources.yaml", preset="ece3")
    assert cfg_ece3['INIDATA_PRESET'] == 'ece3'
    assert cfg_ece3['PRODUCT_NO3'] == 'woa2009'
    assert cfg_ece3['PRODUCT_TALK'] == 'glodap_v1'
    assert cfg_ece3['PRODUCT_DOC'] == 'sette_nomask'

    # official_sette preset (all from SETTE with pure interpolation)
    cfg_sette = load_config("sources.yaml", preset="official_sette")
    assert cfg_sette['INIDATA_PRESET'] == 'official_sette'
    assert cfg_sette['PRODUCT_NO3'] == 'sette_nomask'
    assert cfg_sette['PRODUCT_TALK'] == 'sette_nomask'
    assert cfg_sette['PRODUCT_DOC'] == 'sette_nomask'
    assert cfg_sette['PRODUCT_DUST'] == 'sette_orca2'
    assert cfg_sette['PRODUCT_RIVER'] == 'sette_orca2'


def test_custom_preset():
    content = """
preset: my_custom_exp
base_preset: ece4
tracers_3d:
  DOC: sette_nomask
  TALK: glodap_v2_2023
"""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(content)
        f_name = f.name

    try:
        cfg = load_config(f_name)
        assert cfg['INIDATA_PRESET'] == 'my_custom_exp'
        assert cfg['PRODUCT_DOC'] == 'sette_nomask'
        assert cfg['PRODUCT_TALK'] == 'glodap_v2_2023'
        assert cfg['PRODUCT_NO3'] == 'woa23'  # inherited from ece4
        assert validate_config(cfg) is True
    finally:
        if os.path.exists(f_name):
            os.remove(f_name)


def test_custom_preset_cli_override():
    cfg = load_config("sources.yaml", preset="exp_variant")
    assert cfg['INIDATA_PRESET'] == 'exp_variant'
    assert cfg['PRODUCT_NO3'] == 'woa23'  # inherited from default ece4 base
    assert validate_config(cfg) is True
