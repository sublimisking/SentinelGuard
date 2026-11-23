"""Uygulama ici guncellemenin koruma durumuyla etkilesimi."""

import queue
import sys
import types
from unittest.mock import Mock

import pytest

# Windows disinda da import edilebilsin diye Windows'a ozel modulleri taklit et.
for _name in (
    "winsound", "comtypes", "pycaw", "pycaw.pycaw",
    "win32con", "win32gui", "win32gui_struct",
):
    if _name not in sys.modules:
        try:
            __import__(_name)
        except Exception:
            module = types.ModuleType(_name)
            module.AudioUtilities = object
            sys.modules[_name] = module

app_module = pytest.importorskip("sentinelguard.app")
from sentinelguard.core.update_manager import UpdateInfo

INFO = UpdateInfo(
    version="0.2.0", tag="v0.2.0", name="v0.2.0", notes="", page_url="",
    asset_name="SentinelGuard-v0.2.0-Setup.exe",
    download_url="https://example.test/setup.exe", size=1,
    sha256="0" * 64, checksum_url=None,
)


def make_app(armed=False):
    app = app_module.SentinelGuardApp.__new__(app_module.SentinelGuardApp)
    app.root = Mock()
    app.closed = False
    app.arming_after_id = None
    app.audio_window = None
    app.pin_change_window = None
    app.security_manager = Mock(is_armed=armed)
    app.main_window = Mock()
    app.status_var = Mock()
    app.update_queue = queue.Queue()
    app.update_state = "idle"
    app.update_manual = False
    app.available_update = None
    app.downloaded_installer = None
    app.close = Mock()
    return app


def test_install_is_blocked_while_armed(monkeypatch):
    app = make_app(armed=True)
    app.available_update = INFO
    app.update_state = "available"
    ask = Mock(return_value=True)
    monkeypatch.setattr(app_module.messagebox, "askyesno", ask)

    app.install_update()

    ask.assert_not_called()
    assert app.update_state == "available"


def test_install_is_blocked_while_arming(monkeypatch):
    app = make_app()
    app.arming_after_id = "after#1"
    app.available_update = INFO
    ask = Mock(return_value=True)
    monkeypatch.setattr(app_module.messagebox, "askyesno", ask)

    app.install_update()

    ask.assert_not_called()


def test_download_finished_while_armed_does_not_install(monkeypatch):
    app = make_app()
    launch = Mock()
    monkeypatch.setattr(app_module.update_manager, "launch_installer", launch)

    app.security_manager.is_armed = True  # indirme surerken koruma acildi
    app.update_queue.put(("download", True, "C:/tmp/setup.exe"))
    app.process_update_results()

    launch.assert_not_called()
    app.close.assert_not_called()
    assert app.downloaded_installer == "C:/tmp/setup.exe"


def test_download_finished_when_disarmed_installs_and_closes(monkeypatch):
    app = make_app()
    launch = Mock()
    monkeypatch.setattr(app_module.update_manager, "launch_installer", launch)

    app.update_queue.put(("download", True, "C:/tmp/setup.exe"))
    app.process_update_results()

    launch.assert_called_once_with("C:/tmp/setup.exe")
    app.close.assert_called_once()


def test_check_result_marks_update_available():
    app = make_app()
    app.update_state = "checking"
    app.update_queue.put(("check", True, INFO))
    app.process_update_results()

    assert app.update_state == "available"
    assert app.available_update is INFO


def test_silent_check_failure_is_quiet():
    app = make_app()
    app.update_state = "checking"
    app.update_queue.put(("check", False, RuntimeError("offline")))
    app.process_update_results()

    assert app.update_state == "idle"
    message = app.main_window.set_update_state.call_args.args[0]
    assert "offline" not in message
