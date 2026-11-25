import pytest

from sentinelguard.updates.update_checker import ReleaseInfo
from sentinelguard.updates.version_manager import (
    Version,
    VersionManager
)


def release(tag, pre=False):
    return ReleaseInfo(
        tag=tag,
        title=tag,
        is_prerelease=pre,
        notes="",
        page_url="",
        assets=()
    )


class FakeChecker:

    def __init__(self, releases):
        self.releases = releases

    def fetch_releases(self):
        return self.releases


def manager(releases, current="0.1.0", beta=False):
    return VersionManager(
        FakeChecker(releases),
        current=Version.parse(current),
        include_prerelease=beta
    )


def test_parse_and_order():
    assert Version.parse("v0.2.0-beta.1") < Version.parse("0.2.0")
    assert Version.parse("0.2.0-beta.2") > Version.parse("0.2.0-beta.1")
    assert Version.parse("0.2.0-rc") > Version.parse("0.2.0-beta.9")
    assert Version.parse("1.0.0") > Version.parse("0.99.99")


def test_parse_invalid():
    with pytest.raises(ValueError):
        Version.parse("latest")


def test_newer_stable_found():
    found = manager([
        release("v0.1.0"),
        release("v0.3.0"),
        release("v0.2.0")
    ]).find_update()

    assert found.tag == "v0.3.0"


def test_up_to_date_returns_none():
    assert manager([release("v0.1.0")]).find_update() is None


def test_beta_skipped_by_default():
    found = manager([
        release("v0.2.0-beta.1", pre=True),
        release("v0.1.1")
    ]).find_update()

    assert found.tag == "v0.1.1"


def test_beta_allowed():
    found = manager(
        [release("v0.2.0-beta.1", pre=True), release("v0.1.1")],
        beta=True
    ).find_update()

    assert found.tag == "v0.2.0-beta.1"


def test_bad_tag_ignored():
    found = manager([
        release("nightly"),
        release("v0.2.0")
    ]).find_update()

    assert found.tag == "v0.2.0"
