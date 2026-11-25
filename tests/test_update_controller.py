from pathlib import Path

from sentinelguard.updates.update_checker import (
    ReleaseAsset,
    ReleaseInfo,
    UpdateCheckError
)
from sentinelguard.updates.update_controller import UpdateController
from sentinelguard.updates.update_downloader import UpdateDownloadError


def make_release(with_exe=True):
    assets = ()
    if with_exe:
        assets = (ReleaseAsset(
            name="SentinelGuard-Setup.exe",
            download_url="https://github.com/o/r/releases/download/v1/x.exe",
            size=10,
            digest="sha256:" + "a" * 64
        ),)
    return ReleaseInfo("v0.2.0", "v0.2.0", False, "", "", assets)


class FakeRoot:
    def __init__(self):
        self.after_calls = []

    def after(self, ms, fn):
        self.after_calls.append(fn)


class FakeManager:
    def __init__(self, result=None, error=None):
        self.result, self.error = result, error

    def find_update(self):
        if self.error:
            raise self.error
        return self.result


class FakeDownloader:
    def __init__(self, error=None):
        self.error = error

    def download(self, asset, progress=None):
        if self.error:
            raise self.error
        progress(5, 10)
        progress(10, 10)
        return Path("C:/updates/x.exe")


class FakeInstaller:
    def __init__(self):
        self.launched = []

    def launch(self, path, shutdown):
        self.launched.append(path)
        shutdown()


def build(manager=None, downloader=None):
    installer = FakeInstaller()
    controller = UpdateController(
        FakeRoot(),
        manager or FakeManager(),
        downloader or FakeDownloader(),
        installer,
        start_thread=lambda fn: fn()
    )
    statuses, available = [], []
    controller.bind(statuses.append, available.append)
    return controller, installer, statuses, available


def test_check_finds_update():
    c, _, statuses, available = build(FakeManager(make_release()))
    c.check()
    c.drain()

    assert c.busy is False
    assert available[-1].tag == "v0.2.0"
    assert "v0.2.0" in statuses[-1]


def test_check_up_to_date():
    c, _, statuses, available = build(FakeManager(None))
    c.check()
    c.drain()

    assert available == [None]
    assert statuses[-1] == "SentinelGuard güncel."


def test_check_error():
    c, _, statuses, _ = build(FakeManager(error=UpdateCheckError("x")))
    c.check()
    c.drain()

    assert c.busy is False
    assert "başarısız" in statuses[-1]


def test_install_downloads_and_launches():
    c, installer, statuses, _ = build(FakeManager(make_release()))
    c.check()
    c.drain()
    closed = []

    c.install(can_launch=lambda: True, shutdown=lambda: closed.append(1))
    c.drain()

    assert installer.launched == [Path("C:/updates/x.exe")]
    assert closed == [1]
    assert any("%100" in s for s in statuses)


def test_install_blocked_when_armed():
    c, installer, statuses, _ = build(FakeManager(make_release()))
    c.check()
    c.drain()

    c.install(can_launch=lambda: False, shutdown=lambda: None)
    c.drain()

    assert installer.launched == []
    assert "Koruma açık" in statuses[-1]


def test_install_download_error():
    c, installer, statuses, _ = build(
        FakeManager(make_release()),
        FakeDownloader(UpdateDownloadError("hash"))
    )
    c.check()
    c.drain()

    c.install(can_launch=lambda: True, shutdown=lambda: None)
    c.drain()

    assert installer.launched == []
    assert c.busy is False
    assert "İndirme başarısız" in statuses[-1]


def test_install_without_exe_asset():
    c, installer, statuses, _ = build(FakeManager(make_release(False)))
    c.check()
    c.drain()

    c.install(can_launch=lambda: True, shutdown=lambda: None)

    assert c.busy is False
    assert "kurulum dosyası yok" in statuses[-1]
