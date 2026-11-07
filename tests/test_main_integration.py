from unittest.mock import Mock

from sentinelguard.core.pin_manager import PinManager
from sentinelguard.main import (
    SecurityEventRouter,
    SentinelGuardApp,
    ensure_pin_configured
)


def test_accepted_security_event_notifies_ui():

    security = Mock()
    security.handle_event.return_value = True

    on_event = Mock()

    router = SecurityEventRouter(security, on_event)

    assert router.handle_event("INPUT_DETECTED") is True

    security.handle_event.assert_called_once_with(
        "INPUT_DETECTED"
    )

    on_event.assert_called_once()


def test_rejected_security_event_does_not_open_ui():

    security = Mock()
    security.handle_event.return_value = False

    on_event = Mock()

    router = SecurityEventRouter(security, on_event)

    assert router.handle_event("INPUT_DETECTED") is False

    on_event.assert_not_called()


def test_first_run_creates_pin(tmp_path, monkeypatch):

    pin_manager = PinManager(
        tmp_path / "pin.json",
        iterations=2000
    )

    class FakePinSetupWindow:

        def __init__(self, parent, manager):
            manager.set_pin("246810")
            self.created = True

    monkeypatch.setattr(
        "sentinelguard.main.PinSetupWindow",
        FakePinSetupWindow
    )

    fake_root = Mock()

    result = ensure_pin_configured(
        fake_root,
        pin_manager
    )

    assert result is True
    assert pin_manager.verify_pin("246810") is True

    fake_root.wait_window.assert_called_once()


def test_activate_protection_starts_all_monitors():

    # Gercek Tk penceresi olusturmadan test et.
    app = SentinelGuardApp.__new__(SentinelGuardApp)

    app.arming_after_id = 123
    app.monitor_fault = True

    app.security_manager = Mock()
    app.power_monitor = Mock()
    app.usb_monitor = Mock()
    app.input_monitor = Mock()

    app.status_var = Mock()
    app.arm_button = Mock()
    app.root = Mock()

    app.activate_protection()

    assert app.arming_after_id is None
    assert app.monitor_fault is False

    app.security_manager.arm.assert_called_once()
    app.power_monitor.start_session.assert_called_once()
    app.usb_monitor.start_session.assert_called_once()
    app.input_monitor.start_session.assert_called_once()

    app.root.withdraw.assert_called_once()


def test_tick_checks_all_security_systems():

    app = SentinelGuardApp.__new__(SentinelGuardApp)

    app.closed = False
    app.monitor_fault = False
    app.next_power_check = 0.0

    app.root = Mock()

    app.security_manager = Mock()
    app.security_manager.is_armed = True

    app.usb_monitor = Mock()
    app.power_monitor = Mock()
    app.input_monitor = Mock()

    app.tick()

    app.usb_monitor.process_events.assert_called_once()
    app.power_monitor.check_power.assert_called_once()
    app.input_monitor.check_input.assert_called_once()
    app.security_manager.check_pin_timeout.assert_called_once()

    app.root.after.assert_called_once_with(
        50,
        app.tick
    )
