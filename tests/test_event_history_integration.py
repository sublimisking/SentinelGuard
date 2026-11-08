"""GUI penceresi acmadan app.py ile olay kaydi uyumlulugu."""

from types import SimpleNamespace
from unittest.mock import Mock

from sentinelguard.app import SecurityEventRouter, SentinelGuardApp
from sentinelguard.core.event_store import EventStore
from sentinelguard.ui.main_window import MainWindow


def make_app(tmp_path):
    app = SentinelGuardApp.__new__(SentinelGuardApp)
    app.event_store = EventStore(tmp_path / "events.db")
    app._alarm_logged = False
    app.alarm_manager = SimpleNamespace(alarm_active=False)
    app.pin_manager = SimpleNamespace(verify_pin=lambda pin: pin == "123456")
    return app


def test_usb_and_alarm_are_recorded_once(tmp_path):
    app = make_app(tmp_path)
    security = Mock()
    security.handle_event.return_value = True
    security.handle_event.side_effect = lambda e: (
        setattr(app.alarm_manager, "alarm_active", True) or True
    )
    router = SecurityEventRouter(
        security, Mock(), on_security_event=app._on_security_event
    )

    router.handle_event("USB_DISCONNECTED")
    router.handle_event("USB_DISCONNECTED")
    codes = [e.code for e in app.get_recent_events()]
    assert codes.count("USB_DISCONNECTED") == 2
    assert codes.count("ALARM_STARTED") == 1


def test_pin_attempts_are_recorded_without_pin_value(tmp_path):
    app = make_app(tmp_path)
    assert app._verify_pin("999999") is False
    assert app._verify_pin("123456") is True
    items = app.get_recent_events()
    assert [e.code for e in items] == ["PIN_ACCEPTED", "PIN_REJECTED"]
    assert all("123456" not in item.message for item in items)
    assert all("999999" not in item.message for item in items)


def test_rejected_events_are_not_recorded(tmp_path):
    app = make_app(tmp_path)
    security = Mock()
    security.handle_event.return_value = False
    router = SecurityEventRouter(
        security, Mock(), on_security_event=app._on_security_event
    )
    assert router.handle_event("USB_CONNECTED") is False
    assert app.get_recent_events() == []


def test_events_navigation_refreshes_history():
    window = MainWindow.__new__(MainWindow)
    window.pages = {"home": Mock(), "events": Mock(), "settings": Mock()}
    window.nav_buttons = {"home": Mock(), "events": Mock(), "settings": Mock()}
    window.page_title = Mock()
    window.page_subtitle = Mock()
    window.refresh_events = Mock()

    window.show_page("events")
    window.refresh_events.assert_called_once_with()
    window.page_title.configure.assert_called_once_with(text="Olay Geçmişi")


def test_log_failure_never_blocks_security_event(tmp_path):
    app = make_app(tmp_path)
    app.event_store = Mock()
    app.event_store.add.side_effect = OSError("Disk error")
    security = Mock()
    security.handle_event.return_value = True
    on_event = Mock()
    router = SecurityEventRouter(
        security, on_event, on_security_event=app._on_security_event
    )
    assert router.handle_event("INPUT_DETECTED") is True
    on_event.assert_called_once_with()


def test_disarm_event_is_recorded(tmp_path):
    app = make_app(tmp_path)
    app.input_monitor = Mock()
    app.usb_monitor = Mock()
    app.power_monitor = Mock()
    app.status_var = Mock()
    app.arm_button = Mock()
    app.root = Mock()
    app.monitor_fault = True

    app.on_disarmed()

    assert app.get_recent_events()[0].code == "DISARMED"
    app.root.deiconify.assert_called_once()
