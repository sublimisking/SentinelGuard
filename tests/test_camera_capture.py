"""Gercek kamera olmadan alarm fotografi davranisi."""

from types import SimpleNamespace
import sqlite3
import sys
import threading
from unittest.mock import Mock

import pytest

from sentinelguard.app import SentinelGuardApp
from sentinelguard.core import camera_capture
from sentinelguard.core.camera_capture import (
    CameraCapture,
    load_camera_enabled,
    save_camera_enabled,
)
from sentinelguard.core.event_store import EventStore


class FakeVideoCapture:
    opened = True
    frames_ok = True
    created = 0

    def __init__(self, *args):
        type(self).created += 1

    def isOpened(self):
        return type(self).opened

    def read(self):
        return (True, object()) if type(self).frames_ok else (False, None)

    def release(self):
        pass


@pytest.fixture
def fake_cv2(monkeypatch):
    FakeVideoCapture.opened = True
    FakeVideoCapture.frames_ok = True
    FakeVideoCapture.created = 0

    def imwrite(path, frame, params):
        with open(path, "wb") as file:
            file.write(b"jpg")
        return True

    module = SimpleNamespace(
        VideoCapture=FakeVideoCapture,
        CAP_DSHOW=700,
        IMWRITE_JPEG_QUALITY=1,
        imwrite=imwrite,
    )
    monkeypatch.setitem(sys.modules, "cv2", module)
    return module


def make_camera(tmp_path, **kwargs):
    return CameraCapture(
        captures_dir=tmp_path / "captures",
        retry_delay=0,
        warmup_frames=2,
        **kwargs,
    )


def test_capture_writes_jpeg(tmp_path, fake_cv2):
    path = make_camera(tmp_path).capture_once()
    assert path.suffix == ".jpg"
    assert path.is_file()


def test_only_five_newest_photos_are_kept(tmp_path, fake_cv2):
    camera = make_camera(tmp_path)
    captures = tmp_path / "captures"
    captures.mkdir()
    for index in range(5):
        (captures / f"2026-01-01_00-00-0{index}.jpg").write_bytes(b"x")

    newest = camera.capture_once()

    names = sorted(p.name for p in captures.glob("*.jpg"))
    assert len(names) == 5
    assert "2026-01-01_00-00-00.jpg" not in names  # en eskisi silindi
    assert newest.name in names


def test_missing_camera_raises_after_retries(tmp_path, fake_cv2):
    FakeVideoCapture.opened = False
    camera = make_camera(tmp_path, attempts=3)
    with pytest.raises(RuntimeError, match="Kamera"):
        camera.capture_with_retries()
    # Her deneme DSHOW + varsayilan arka ucu dener.
    assert FakeVideoCapture.created == 6


def test_unreadable_frames_fail(tmp_path, fake_cv2):
    FakeVideoCapture.frames_ok = False
    with pytest.raises(RuntimeError):
        make_camera(tmp_path, attempts=1).capture_with_retries()


def test_retry_succeeds_on_second_attempt(tmp_path, fake_cv2, monkeypatch):
    camera = make_camera(tmp_path, attempts=3)
    calls = {"n": 0}
    real = camera.capture_once

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("meşgul")
        return real()

    monkeypatch.setattr(camera, "capture_once", flaky)
    assert camera.capture_with_retries().is_file()
    assert calls["n"] == 2


def test_async_reports_failure_without_raising(tmp_path, fake_cv2):
    FakeVideoCapture.opened = False
    done = threading.Event()
    result = {}

    def on_done(path, error):
        result["path"], result["error"] = path, error
        done.set()

    assert make_camera(tmp_path, attempts=1).capture_async(on_done)
    assert done.wait(5)
    assert result["path"] is None
    assert result["error"]


def test_camera_setting_defaults_on_and_keeps_other_keys(tmp_path):
    settings = tmp_path / "settings.json"
    assert load_camera_enabled(settings) is True

    settings.write_text('{"audio": {"speaker_device_id": "abc"}}')
    save_camera_enabled(False, settings)

    assert load_camera_enabled(settings) is False
    assert '"speaker_device_id": "abc"' in settings.read_text()

    settings.write_text("bozuk json")
    assert load_camera_enabled(settings) is True


def test_event_store_migrates_old_database(tmp_path):
    db = tmp_path / "events.db"
    with sqlite3.connect(db) as connection:
        connection.execute(
            """CREATE TABLE security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                occurred_at TEXT NOT NULL, code TEXT NOT NULL,
                category TEXT NOT NULL, message TEXT NOT NULL)"""
        )
        connection.execute(
            "INSERT INTO security_events (occurred_at, code, category, message)"
            " VALUES ('2026-01-01T00:00:00+00:00', 'ARMED', 'system', 'eski')"
        )
    connection.close()

    store = EventStore(db)
    store.add("PHOTO_CAPTURED", "alarm", "foto", photo_path=tmp_path / "a.jpg")
    records = store.recent()
    assert records[0].photo_path == str(tmp_path / "a.jpg")
    assert records[1].photo_path is None


def make_app(tmp_path, enabled=True):
    app = SentinelGuardApp.__new__(SentinelGuardApp)
    app.event_store = EventStore(tmp_path / "events.db")
    app._alarm_logged = False
    app.alarm_manager = SimpleNamespace(alarm_active=True)
    app.audio_manager = SimpleNamespace(settings_path=tmp_path / "settings.json")
    app.camera_capture = Mock()
    app._photo_results = __import__("queue").Queue()
    save_camera_enabled(enabled, app.audio_manager.settings_path)
    return app


def test_alarm_triggers_capture_once(tmp_path):
    app = make_app(tmp_path)
    app._record_alarm_start()
    app._record_alarm_start()
    assert app.camera_capture.capture_async.call_count == 1


def test_disabled_setting_skips_capture(tmp_path):
    app = make_app(tmp_path, enabled=False)
    app._record_alarm_start()
    app.camera_capture.capture_async.assert_not_called()


def test_capture_results_are_logged_on_main_thread(tmp_path):
    app = make_app(tmp_path)
    photo = tmp_path / "p.jpg"
    app._photo_results.put((photo, None))
    app._photo_results.put((None, "Kamera açılamadı"))
    app._drain_photo_results()

    records = {r.code: r for r in app.get_recent_events()}
    assert records["PHOTO_CAPTURED"].photo_path == str(photo)
    assert "Kamera açılamadı" in records["PHOTO_FAILED"].message


def test_capture_failure_never_stops_alarm_logging(tmp_path):
    app = make_app(tmp_path)
    app.camera_capture.capture_async.side_effect = RuntimeError("boom")
    app._record_alarm_start()
    codes = [r.code for r in app.get_recent_events()]
    assert "ALARM_STARTED" in codes
    assert "PHOTO_FAILED" in codes


def test_png_preview_missing_file_returns_none(tmp_path, fake_cv2):
    fake_cv2.imread = lambda path: None
    assert camera_capture.make_png_base64(tmp_path / "yok.jpg", 96) is None


def test_history_shows_only_last_ten_events(tmp_path):
    app = make_app(tmp_path)
    for index in range(15):
        app._log_event("ARMED", "system", f"olay {index}")
    events = app.get_recent_events()
    assert len(events) == 10
    assert events[0].message == "olay 14"


def test_list_photos_newest_first_and_delete(tmp_path):
    camera = make_camera(tmp_path)
    captures = tmp_path / "captures"
    captures.mkdir()
    for name in ("2026-01-01_00-00-01.jpg", "2026-01-01_00-00-03.jpg"):
        (captures / name).write_bytes(b"x")

    photos = camera.list_photos()
    assert photos[0].name == "2026-01-01_00-00-03.jpg"

    assert camera.delete_photo(photos[0]) is True
    assert camera.delete_photo(photos[0]) is False  # zaten yok
    assert len(camera.list_photos()) == 1


def test_delete_rejects_files_outside_captures(tmp_path):
    camera = make_camera(tmp_path)
    (tmp_path / "captures").mkdir()
    outside = tmp_path / "belge.jpg"
    outside.write_bytes(b"x")
    with pytest.raises(ValueError):
        camera.delete_photo(outside)
    with pytest.raises(ValueError):
        camera.delete_photo(tmp_path / "captures" / ".." / "belge.jpg")
    assert outside.exists()

    txt = tmp_path / "captures" / "not.txt"
    txt.write_bytes(b"x")
    with pytest.raises(ValueError):
        camera.delete_photo(txt)


def test_photos_page_delete_flow():
    from unittest.mock import patch
    from sentinelguard.ui.main_window import MainWindow

    window = MainWindow.__new__(MainWindow)
    window.on_delete_photo = Mock()
    window.refresh_photos = Mock()

    window._confirm_delete = Mock(return_value=False)
    window.delete_photo("a.jpg")
    window.on_delete_photo.assert_not_called()

    window._confirm_delete = Mock(return_value=True)
    window.delete_photo("a.jpg")
    window.on_delete_photo.assert_called_once_with("a.jpg")
    window.refresh_photos.assert_called_once_with()

    window.on_delete_photo.side_effect = OSError("kilitli")
    with patch("sentinelguard.ui.main_window.messagebox") as box:
        window.delete_photo("b.jpg")
    box.showerror.assert_called_once()


def test_photos_navigation_refreshes_list():
    from sentinelguard.ui.main_window import MainWindow

    window = MainWindow.__new__(MainWindow)
    window.pages = {"home": Mock(), "photos": Mock()}
    window.nav_buttons = {"home": Mock(), "photos": Mock()}
    window.page_title = Mock()
    window.page_subtitle = Mock()
    window.refresh_photos = Mock()

    window.show_page("photos")
    window.refresh_photos.assert_called_once_with()
    window.page_title.configure.assert_called_once_with(text="Fotoğraflar")
