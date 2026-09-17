"""
Tests for pisces_inidata.download module.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from pisces_inidata.download import (
    download_file,
    extract_tar,
    download_woa23_tracer,
    download_official_nemo_inputs,
    download_glodap,
    download_sources,
)


def test_download_file_already_exists():
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write("existing data")
        temp_path = f.name

    try:
        with patch("urllib.request.urlretrieve") as mock_retrieve:
            result = download_file("http://example.com/file.nc", temp_path, dry_run=False)
            assert result is False
            mock_retrieve.assert_not_called()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_download_file_dry_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "test_target.nc")
        with patch("urllib.request.urlretrieve") as mock_retrieve:
            result = download_file("http://example.com/file.nc", target, dry_run=True)
            assert result is True
            assert not os.path.exists(target)
            mock_retrieve.assert_not_called()


def test_download_file_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "subdir", "test_file.nc")

        def fake_urlretrieve(url, filename):
            with open(filename, "w") as f:
                f.write("downloaded content")

        with patch("urllib.request.urlretrieve", side_effect=fake_urlretrieve):
            result = download_file("http://example.com/file.nc", target, dry_run=False)
            assert result is True
            assert os.path.exists(target)
            with open(target) as f:
                assert f.read() == "downloaded content"


def test_download_file_failure_cleans_tmp():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "test_fail.nc")
        tmp_target = target + ".tmp"

        def fail_urlretrieve(url, filename):
            with open(filename, "w") as f:
                f.write("partial corrupt content")
            raise ConnectionResetError("Connection dropped")

        with patch("urllib.request.urlretrieve", side_effect=fail_urlretrieve):
            with pytest.raises(RuntimeError, match="Failed to download"):
                download_file("http://example.com/file.nc", target, dry_run=False)

        assert not os.path.exists(target)
        assert not os.path.exists(tmp_target)


def test_extract_tar_dry_run():
    with patch("tarfile.open") as mock_tar:
        extract_tar("fake.tar.gz", "/tmp/fake_dir", dry_run=True)
        mock_tar.assert_not_called()


def test_extract_tar_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        tar_mock = MagicMock()
        member1 = MagicMock()
        member1.name = "sub/file.txt"
        tar_mock.getmembers.return_value = [member1]

        with patch("tarfile.open") as mock_open:
            mock_open.return_value.__enter__.return_value = tar_mock
            extract_tar("archive.tar.gz", tmpdir, strip_components=1, dry_run=False)
            assert member1.name == "file.txt"
            tar_mock.extract.assert_called_once_with(member1, path=tmpdir)


def test_download_woa23_tracer_dry_run():
    with patch("pisces_inidata.download.download_file") as mock_dl:
        download_woa23_tracer("nitrate", "n", "nitrate", "/tmp/raw", dry_run=True)
        # 1 annual + 12 monthly = 13 files
        assert mock_dl.call_count == 13


def test_download_official_nemo_inputs_already_present():
    with tempfile.TemporaryDirectory() as tmpdir:
        off_dir = os.path.join(tmpdir, "official_v5.0.0")
        os.makedirs(off_dir, exist_ok=True)
        with open(os.path.join(off_dir, "data_FER_nomask.nc"), "w") as f:
            f.write("dummy")

        with patch("pisces_inidata.download.download_file") as mock_dl:
            download_official_nemo_inputs(tmpdir, dry_run=False)
            mock_dl.assert_not_called()


def test_download_glodap_already_present():
    with tempfile.TemporaryDirectory() as tmpdir:
        glodap_dir = os.path.join(tmpdir, "glodap_v2")
        os.makedirs(glodap_dir, exist_ok=True)
        with open(os.path.join(glodap_dir, "GLODAPv2.2016b.TAlk.nc"), "w") as f:
            f.write("dummy")

        with patch("pisces_inidata.download.download_file") as mock_dl:
            download_glodap(tmpdir, dry_run=False)
            mock_dl.assert_not_called()


def test_download_sources_dry_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        code = download_sources(config_file="sources.yaml", raw_dir=tmpdir, dry_run=True)
        assert code == 0


def test_cli_download_prepare_flag(monkeypatch):
    from pisces_inidata.cli import main
    import sys

    monkeypatch.setattr(sys, 'argv', ['pisces-inidata', 'download', '--help'])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


def test_download_official_nemo_inputs_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        attempted_urls = []

        def mock_dl(url, target, dry_run=False):
            attempted_urls.append(url)
            if "bad" in url:
                raise RuntimeError("404 Not Found")
            with open(target, "w") as f:
                f.write("tar-content")
            return True

        with patch("pisces_inidata.download.download_file", side_effect=mock_dl), \
             patch("pisces_inidata.download.extract_tar") as mock_extract, \
             patch("pisces_inidata.catalog.load_catalog") as mock_cat:
            mock_cat.return_value = {
                "packages": {
                    "official_nemo_inputs": {
                        "url": "https://fail.jasmin.ac.uk/bad.tar.gz",
                        "archive": "test.tar.gz",
                        "key_file": "key.nc",
                        "default_dir": "off_dir",
                    }
                }
            }
            download_official_nemo_inputs(tmpdir, dry_run=False)
            assert len(attempted_urls) == 2
            assert attempted_urls[0] == "https://fail.jasmin.ac.uk/bad.tar.gz"
            assert "sette_inputs/extras" in attempted_urls[1]
            mock_extract.assert_called_once()
