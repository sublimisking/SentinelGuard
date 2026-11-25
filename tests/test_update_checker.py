import json
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

import sentinelguard.updates.update_checker as update_module

from sentinelguard.updates.update_checker import (
    UpdateChecker,
    UpdateCheckError
)


def set_response(monkeypatch, data):

    response = BytesIO(
        json.dumps(data).encode("utf-8")
    )

    def fake_urlopen(request, timeout):
        assert timeout == 8
        assert "releases?per_page=30" in request.full_url
        return response

    monkeypatch.setattr(
        update_module,
        "urlopen",
        fake_urlopen
    )


def test_fetch_includes_beta_and_installer(monkeypatch):

    set_response(monkeypatch, [{
        "tag_name": "v0.2.0-beta.1",
        "draft": False,
        "prerelease": True,
        "name": "Beta",
        "body": "Changes",
        "assets": [{
            "name": "SentinelGuard-Setup.exe",
            "browser_download_url": (
                "https://github.com/owner/repo/"
                "releases/download/v0.2.0-beta.1/"
                "SentinelGuard-Setup.exe"
            ),
            "size": 100,
            "digest": "sha256:abcdef"
        }]
    }])

    releases = UpdateChecker(
        "owner",
        "repo"
    ).fetch_releases()

    assert len(releases) == 1

    release = releases[0]

    assert release.tag == "v0.2.0-beta.1"
    assert release.is_prerelease is True
    assert release.assets[0].name == "SentinelGuard-Setup.exe"


def test_draft_is_skipped(monkeypatch):

    set_response(monkeypatch, [
        {
            "tag_name": "v0.3.0",
            "draft": True
        },
        {
            "tag_name": "v0.2.0",
            "prerelease": False
        }
    ])

    releases = UpdateChecker(
        "owner",
        "repo"
    ).fetch_releases()

    assert [r.tag for r in releases] == [
        "v0.2.0"
    ]


def test_empty_is_valid(monkeypatch):

    set_response(monkeypatch, [])

    releases = UpdateChecker(
        "owner",
        "repo"
    ).fetch_releases()

    assert releases == []


def test_invalid_data(monkeypatch):

    set_response(monkeypatch, {
        "message": "error"
    })

    with pytest.raises(UpdateCheckError):
        UpdateChecker(
            "owner",
            "repo"
        ).fetch_releases()


def test_network_error(monkeypatch):

    def fail(request, timeout):
        raise URLError("offline")

    monkeypatch.setattr(
        update_module,
        "urlopen",
        fail
    )

    with pytest.raises(UpdateCheckError):
        UpdateChecker(
            "owner",
            "repo"
        ).fetch_releases()


def test_http_error(monkeypatch):

    def fail(request, timeout):
        raise HTTPError(
            request.full_url,
            404,
            "Not found",
            {},
            None
        )

    monkeypatch.setattr(
        update_module,
        "urlopen",
        fail
    )

    with pytest.raises(UpdateCheckError):
        UpdateChecker(
            "owner",
            "repo"
        ).fetch_releases()


def test_untrusted_asset_url_is_skipped(monkeypatch):

    set_response(monkeypatch, [{
        "tag_name": "v0.2.0",
        "assets": [{
            "name": "bad.exe",
            "browser_download_url": (
                "http://example.com/bad.exe"
            )
        }]
    }])

    releases = UpdateChecker(
        "owner",
        "repo"
    ).fetch_releases()

    assert releases[0].assets == ()
