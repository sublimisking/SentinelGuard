import hashlib
import io

import pytest

from sentinelguard.core import update_manager
from sentinelguard.core.update_manager import (
    UpdateError,
    check_for_update,
    download_update,
    is_newer,
    launch_installer,
    select_update,
)


def _release(tag, *, prerelease=False, draft=False, digest=None, checksum=True):
    name = f"SentinelGuard-{tag}-Setup.exe"
    installer = {
        "name": name,
        "browser_download_url": f"https://example.test/{name}",
        "size": 5,
    }
    if digest:
        installer["digest"] = digest
    assets = [installer]
    if checksum:
        assets.append({
            "name": name + ".sha256",
            "browser_download_url": f"https://example.test/{name}.sha256",
        })
    return {
        "tag_name": tag,
        "name": tag,
        "draft": draft,
        "prerelease": prerelease,
        "html_url": f"https://example.test/{tag}",
        "body": "notes",
        "assets": assets,
    }


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _opener(files):
    def open_url(url, accept=None):
        return FakeResponse(files[url])
    return open_url


@pytest.mark.parametrize(
    ("candidate", "current", "expected"),
    [
        ("v0.2.0", "0.1.0-beta", True),
        ("v0.1.0", "0.1.0-beta", True),
        ("v0.1.0-beta.2", "0.1.0-beta", True),
        ("v0.1.0-beta", "0.1.0-beta", False),
        ("v0.1.0-alpha", "0.1.0-beta", False),
        ("v0.0.9", "0.1.0-beta", False),
        ("v0.10.0", "0.9.0", True),
    ],
)
def test_version_comparison(candidate, current, expected):
    assert is_newer(candidate, current) is expected


def test_select_update_picks_highest_newer_release():
    releases = [
        _release("v0.1.0-beta"),
        _release("v0.3.0", draft=True),
        _release("v0.2.0-beta", prerelease=True),
        _release("v0.1.5"),
        _release("not-a-version"),
    ]
    info = select_update(releases, current="0.1.0-beta")
    assert info.version == "0.2.0-beta"
    assert info.asset_name == "SentinelGuard-v0.2.0-beta-Setup.exe"
    assert info.checksum_url.endswith(".sha256")


def test_select_update_skips_release_without_installer():
    release = _release("v0.2.0")
    release["assets"] = [{"name": "source.zip", "browser_download_url": "x"}]
    assert select_update([release], current="0.1.0-beta") is None


def test_select_update_returns_none_when_current():
    assert select_update([_release("v0.1.0-beta")], current="0.1.0-beta") is None


def test_check_for_update_rejects_bad_payload():
    with pytest.raises(UpdateError):
        check_for_update(fetch_json=lambda url: {"message": "rate limited"})


def test_download_verifies_checksum_file(tmp_path):
    data = b"MZexe"
    info = select_update([_release("v0.2.0")], current="0.1.0")
    sha = hashlib.sha256(data).hexdigest()
    opener = _opener({
        info.download_url: data,
        info.checksum_url: f"{sha}  {info.asset_name}".encode(),
    })
    path = download_update(info, target_dir=tmp_path, opener=opener)
    assert path.read_bytes() == data
    assert not list(tmp_path.glob("*.part"))


def test_download_prefers_github_digest(tmp_path):
    data = b"MZexe"
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    info = select_update(
        [_release("v0.2.0", digest=digest, checksum=False)], current="0.1.0"
    )
    path = download_update(
        info, target_dir=tmp_path, opener=_opener({info.download_url: data})
    )
    assert path.exists()


def test_download_rejects_checksum_mismatch(tmp_path):
    info = select_update([_release("v0.2.0")], current="0.1.0")
    opener = _opener({
        info.download_url: b"tampered",
        info.checksum_url: ("0" * 64).encode(),
    })
    with pytest.raises(UpdateError):
        download_update(info, target_dir=tmp_path, opener=opener)
    assert list(tmp_path.iterdir()) == []


def test_download_refuses_without_any_checksum(tmp_path):
    info = select_update([_release("v0.2.0", checksum=False)], current="0.1.0")
    with pytest.raises(UpdateError):
        download_update(
            info, target_dir=tmp_path, opener=_opener({info.download_url: b"x"})
        )


def test_download_rejects_oversized_file(tmp_path, monkeypatch):
    monkeypatch.setattr(update_manager, "MAX_INSTALLER_BYTES", 3)
    data = b"MZexe"
    info = select_update([_release("v0.2.0")], current="0.1.0")
    opener = _opener({
        info.download_url: data,
        info.checksum_url: hashlib.sha256(data).hexdigest().encode(),
    })
    with pytest.raises(UpdateError):
        download_update(info, target_dir=tmp_path, opener=opener)


def test_http_get_rejects_plain_http():
    with pytest.raises(UpdateError):
        update_manager._http_get("http://example.test/file")


def test_launch_installer_runs_silent_setup(tmp_path):
    calls = []

    def fake_popen(args, **kwargs):
        calls.append(args)

    launch_installer(tmp_path / "setup.exe", popen=fake_popen)
    assert calls[0][0].endswith("setup.exe")
    assert "/SILENT" in calls[0]
    assert "/CLOSEAPPLICATIONS" in calls[0]
