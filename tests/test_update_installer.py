import sys

import pytest

import sentinelguard.updates.update_installer as inst_module

from sentinelguard.updates.update_installer import (
    UpdateInstaller,
    UpdateInstallError
)


@pytest.fixture(autouse=True)
def windows(monkeypatch):
    monkeypatch.setattr(inst_module.sys, "platform", "win32")


def make_exe(folder, name="SentinelGuard-Setup.exe"):
    path = folder / name
    path.write_bytes(b"MZ fake")
    return path


class Recorder:

    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def __call__(self, args, **kwargs):
        if self.error:
            raise self.error
        self.calls.append((args, kwargs))


def test_launch_runs_silent_then_shutdown(tmp_path):
    exe = make_exe(tmp_path)
    popen = Recorder()
    closed = []

    UpdateInstaller(tmp_path, popen).launch(
        exe, lambda: closed.append(True)
    )

    args, kwargs = popen.calls[0]

    assert args[0] == str(exe.resolve())
    assert "/VERYSILENT" in args
    assert "/SUPPRESSMSGBOXES" in args
    assert closed == [True]


def test_outside_dir_refused(tmp_path):
    allowed = tmp_path / "updates"
    allowed.mkdir()
    exe = make_exe(tmp_path)
    popen = Recorder()

    with pytest.raises(UpdateInstallError):
        UpdateInstaller(allowed, popen).launch(exe, lambda: None)

    assert popen.calls == []


def test_non_exe_refused(tmp_path):
    bad = make_exe(tmp_path, "setup.bat")

    with pytest.raises(UpdateInstallError):
        UpdateInstaller(tmp_path, Recorder()).launch(bad, lambda: None)


def test_missing_file(tmp_path):
    with pytest.raises(UpdateInstallError):
        UpdateInstaller(tmp_path, Recorder()).launch(
            tmp_path / "nope.exe", lambda: None
        )


def test_popen_fail_does_not_shutdown(tmp_path):
    exe = make_exe(tmp_path)
    closed = []

    with pytest.raises(UpdateInstallError):
        UpdateInstaller(tmp_path, Recorder(OSError("x"))).launch(
            exe, lambda: closed.append(True)
        )

    assert closed == []


def test_non_windows_refused(monkeypatch, tmp_path):
    monkeypatch.setattr(inst_module.sys, "platform", "linux")
    exe = make_exe(tmp_path)

    with pytest.raises(UpdateInstallError):
        UpdateInstaller(tmp_path, Recorder()).launch(exe, lambda: None)
