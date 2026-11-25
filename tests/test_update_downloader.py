import hashlib
from io import BytesIO
from urllib.error import URLError

import pytest

import sentinelguard.updates.update_downloader as dl_module

from sentinelguard.updates.update_checker import (
    ReleaseAsset,
    ReleaseInfo
)
from sentinelguard.updates.update_downloader import (
    UpdateDownloader,
    UpdateDownloadError,
    select_installer
)


DATA = b"fake installer bytes" * 1000
GOOD_DIGEST = "sha256:" + hashlib.sha256(DATA).hexdigest()
URL = (
    "https://github.com/owner/repo/releases/download/"
    "v0.2.0/SentinelGuard-Setup.exe"
)


def make_asset(name="SentinelGuard-Setup.exe", size=len(DATA),
               digest=GOOD_DIGEST):
    return ReleaseAsset(
        name=name,
        download_url=URL,
        size=size,
        digest=digest
    )


def serve(monkeypatch, data=DATA):

    def fake_urlopen(request, timeout):
        return BytesIO(data)

    monkeypatch.setattr(dl_module, "urlopen", fake_urlopen)


def test_download_ok(monkeypatch, tmp_path):
    serve(monkeypatch)
    calls = []

    path = UpdateDownloader(tmp_path).download(
        make_asset(),
        progress=lambda got, total: calls.append(got)
    )

    assert path.read_bytes() == DATA
    assert calls[-1] == len(DATA)
    assert not list(tmp_path.glob("*.part"))


def test_bad_hash_removes_file(monkeypatch, tmp_path):
    serve(monkeypatch)
    asset = make_asset(digest="sha256:" + "0" * 64)

    with pytest.raises(UpdateDownloadError):
        UpdateDownloader(tmp_path).download(asset)

    assert list(tmp_path.iterdir()) == []


def test_size_mismatch(monkeypatch, tmp_path):
    serve(monkeypatch)

    with pytest.raises(UpdateDownloadError):
        UpdateDownloader(tmp_path).download(make_asset(size=5))


def test_missing_digest_refused(monkeypatch, tmp_path):
    serve(monkeypatch)

    with pytest.raises(UpdateDownloadError):
        UpdateDownloader(tmp_path).download(make_asset(digest=None))


def test_missing_digest_allowed_when_disabled(monkeypatch, tmp_path):
    serve(monkeypatch)

    path = UpdateDownloader(tmp_path, require_digest=False).download(
        make_asset(digest=None)
    )

    assert path.exists()


def test_unsafe_name_refused(monkeypatch, tmp_path):
    serve(monkeypatch)

    with pytest.raises(UpdateDownloadError):
        UpdateDownloader(tmp_path).download(
            make_asset(name="..\\evil.exe")
        )


def test_network_error(monkeypatch, tmp_path):

    def fail(request, timeout):
        raise URLError("offline")

    monkeypatch.setattr(dl_module, "urlopen", fail)

    with pytest.raises(UpdateDownloadError):
        UpdateDownloader(tmp_path).download(make_asset())

    assert list(tmp_path.iterdir()) == []


def test_select_installer():
    release = ReleaseInfo(
        tag="v0.2.0", title="", is_prerelease=False,
        notes="", page_url="",
        assets=(
            make_asset(name="source.zip"),
            make_asset(name="SentinelGuard-Setup.exe")
        )
    )

    assert select_installer(release).name == "SentinelGuard-Setup.exe"
