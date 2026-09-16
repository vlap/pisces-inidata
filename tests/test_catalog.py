from pisces_inidata.catalog import (
    load_catalog,
    resolve_package_dir,
    resolve_source_field,
    resolve_target_field,
    get_expected_products,
    export_source_env,
    export_target_env,
)


def test_load_catalog():
    cat = load_catalog()
    assert "packages" in cat
    assert "sources" in cat
    assert "conventions" in cat
    assert "official_nemo_inputs" in cat["packages"]
    assert "woa23" in cat["sources"]
    assert "sette_nomask" in cat["sources"]
    assert "nemo4_ece4" in cat["conventions"]


def test_resolve_package_dir(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    off_dir = raw / "official_v5.0.0"
    off_dir.mkdir()

    # Default lookup
    resolved = resolve_package_dir("official_nemo_inputs", raw_dir=str(raw))
    assert resolved == str(off_dir)

    # Environment override
    custom_off = tmp_path / "custom_official_v5.1.0"
    monkeypatch.setenv("OFFICIAL_INPUTS_DIR", str(custom_off))
    resolved_env = resolve_package_dir("official_nemo_inputs", raw_dir=str(raw))
    assert resolved_env == str(custom_off)


def test_resolve_source_field_ece4(tmp_path):
    raw = str(tmp_path / "raw")

    # WOA23 for NO3
    no3_meta = resolve_source_field("NO3", preset="ece4", raw_dir=raw)
    assert no3_meta["product"] == "woa23"
    assert no3_meta["handler"] == "woa23"
    assert no3_meta["src_var"] == "n_an"
    assert no3_meta["std_var"] == "NO3"
    assert no3_meta["fillmiss"] is True

    # GLODAP for TALK
    talk_meta = resolve_source_field("TALK", preset="ece4", raw_dir=raw)
    assert talk_meta["product"] == "glodap_v2_2016b"
    assert talk_meta["handler"] == "glodap"
    assert talk_meta["src_var"] == "TAlk"
    assert talk_meta["std_var"] == "Alkalini"

    # Panaïotis DOC
    doc_meta = resolve_source_field("DOC", preset="ece4", raw_dir=raw)
    assert doc_meta["product"] == "panaiotis2024"
    assert doc_meta["handler"] == "doc"
    assert doc_meta["src_var"] == "DOC"
    assert doc_meta["std_var"] == "DOC"

    # Tagliabue Fer
    fe_meta = resolve_source_field("Fer", preset="ece4", raw_dir=raw)
    assert fe_meta["product"] == "sette_nomask"
    assert fe_meta["src_var"] == "Fer"
    assert fe_meta["pad_depth"] == 6000.0


def test_resolve_source_field_official_sette(tmp_path):
    raw = str(tmp_path / "raw")

    # In official_sette, all 3D tracers come from sette_nomask
    no3_meta = resolve_source_field("NO3", preset="official_sette", raw_dir=raw)
    assert no3_meta["product"] == "sette_nomask"
    assert no3_meta["src_var"] == "NO3"
    assert "data_NO3_nomask.nc" in no3_meta["src_file"]

    talk_meta = resolve_source_field("TALK", preset="official_sette", raw_dir=raw)
    assert talk_meta["product"] == "sette_nomask"
    assert talk_meta["src_var"] == "TALK"
    assert talk_meta["std_var"] == "Alkalini"
    assert "data_ALK_nomask.nc" in talk_meta["src_file"]

    doc_meta = resolve_source_field("DOC", preset="official_sette", raw_dir=raw)
    assert doc_meta["product"] == "sette_nomask"
    assert doc_meta["src_var"] == "DOC"
    assert "data_DOC_nomask.nc" in doc_meta["src_file"]


def test_resolve_boundary_forcings(tmp_path):
    raw = str(tmp_path / "raw")

    dust_meta = resolve_source_field("dust", preset="ece4", raw_dir=raw)
    assert dust_meta["product"] == "sette_orca2"
    assert "dust" in dust_meta["vars_list"]
    assert "solubility2" in dust_meta["vars_list"]

    hydrofe_meta = resolve_source_field("hydrofe", preset="ece4", raw_dir=raw)
    assert hydrofe_meta["src_var"] == "epsdb"
    assert "hydrofe.orca.nc" in hydrofe_meta["src_file"]

    river_meta = resolve_source_field("river", preset="ece4", raw_dir=raw)
    assert river_meta["src_var"] == "riverdin"
    assert "riverdin" in river_meta["vars_list"]
    assert "bathy.orca.nc" in river_meta["coords_source_file"]


def test_resolve_target_field():
    talk_target = resolve_target_field("TALK", "eORCA1")
    assert talk_target["out_file"] == "data_TALK_eORCA1.nc"
    assert talk_target["target_var"] == "Alkalini"
    assert "Alkalini_GLODAP_annual_eORCA1.nc" in talk_target["symlinks"]

    par_target = resolve_target_field("par", "eORCA025")
    assert par_target["out_file"] == "par.orca.nc"
    assert par_target["target_var"] == "fr_par"
    assert "par_fraction_daily_eORCA025.nc" in par_target["symlinks"]


def test_get_expected_products():
    expected = get_expected_products("eORCA1")
    assert len(expected) >= 15
    fnames = [e[0] for e in expected]
    assert "data_NO3_eORCA1.nc" in fnames
    assert "data_TALK_eORCA1.nc" in fnames
    assert "dust.orca.nc" in fnames
    assert "river.orca.nc" in fnames


def test_export_env_scripts():
    src_env = export_source_env("DOC", preset="ece4")
    assert "export VAR=\"DOC\"" in src_env
    assert "export HANDLER=\"doc\"" in src_env

    tgt_env = export_target_env("TALK", "ORCA2")
    assert "export OUT_FILE=\"data_TALK_ORCA2.nc\"" in tgt_env
    assert "export TARGET_VAR=\"Alkalini\"" in tgt_env
