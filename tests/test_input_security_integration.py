"""InputMonitor'un fare filtresi kullanan yeni arayuzu icin entegrasyon testleri.

Eski get_last_input_time temelli testleri degistirir; 40 px titreme
filtresini devre disi birakmaz.
"""

from sentinelguard.core.security_manager import SecurityManager
from sentinelguard.monitors.input_monitor import InputMonitor


class FakeAlarmManager:
    def __init__(self):
        self.started = 0
        self.stopped = 0

    def start_alarm(self):
        self.started += 1

    def stop_alarm(self):
        self.stopped += 1


class FakeInputBackend:
    def __init__(self):
        self.cursor = (100, 100)
        self.keys = set()

    def cursor_position(self):
        return self.cursor

    def pressed_keys(self):
        return frozenset(self.keys)


def make_session(pin_verifier=None):
    now = [100.0]
    alarm = FakeAlarmManager()
    backend = FakeInputBackend()
    security = SecurityManager(
        alarm,
        pin_verifier=pin_verifier,
        clock=lambda: now[0],
    )
    monitor = InputMonitor(
        security,
        backend=backend,
        clock=lambda: now[0],
    )
    security.arm()
    monitor.start_session()
    return security, monitor, backend, alarm, now


def trigger_intentional_mouse_movement(monitor, backend):
    # 40 px esigini gec: baslangic (100, 100) -> (155, 100).
    backend.cursor = (155, 100)
    return monitor.check_input()


def test_input_starts_pin_countdown():
    security, monitor, backend, alarm, now = make_session()

    assert trigger_intentional_mouse_movement(monitor, backend) is True
    assert security.pin_deadline == 110.0
    assert alarm.started == 0


def test_repeated_input_does_not_restart_countdown():
    security, monitor, backend, alarm, now = make_session()
    assert trigger_intentional_mouse_movement(monitor, backend) is True
    original_deadline = security.pin_deadline

    now[0] = 104.0
    backend.cursor = (300, 100)
    assert monitor.check_input() is False
    assert security.pin_deadline == original_deadline
    assert alarm.started == 0


def test_alarm_starts_after_ten_seconds():
    security, monitor, backend, alarm, now = make_session()
    trigger_intentional_mouse_movement(monitor, backend)

    now[0] = 109.9
    assert security.check_pin_timeout() is False
    assert alarm.started == 0

    now[0] = 110.0
    assert security.check_pin_timeout() is True
    assert alarm.started == 1


def test_correct_pin_disarms_before_timeout():
    security, monitor, backend, alarm, now = make_session(
        pin_verifier=lambda pin: pin == "123456"
    )
    trigger_intentional_mouse_movement(monitor, backend)

    now[0] = 105.0
    assert security.submit_pin("123456") is True
    assert security.is_armed is False
    assert security.pin_deadline is None
    assert alarm.started == 0
    assert alarm.stopped == 1


def test_wrong_pin_does_not_reset_countdown():
    security, monitor, backend, alarm, now = make_session(
        pin_verifier=lambda pin: pin == "123456"
    )
    trigger_intentional_mouse_movement(monitor, backend)
    original_deadline = security.pin_deadline

    now[0] = 105.0
    assert security.submit_pin("999999") is False
    assert security.pin_deadline == original_deadline
    assert security.is_armed is True

    now[0] = 110.0
    assert security.check_pin_timeout() is True
    assert alarm.started == 1


def test_usb_event_still_triggers_immediate_alarm():
    security, monitor, backend, alarm, now = make_session()

    assert security.handle_event("USB_DISCONNECTED") is True
    assert alarm.started == 1
    assert security.pin_deadline is None


def test_small_mouse_vibrations_do_not_start_countdown():
    security, monitor, backend, alarm, now = make_session()

    for offset, cursor in enumerate(((102, 100), (98, 103), (106, 100)), 1):
        now[0] = 100.0 + offset * 0.1
        backend.cursor = cursor
        assert monitor.check_input() is False

    assert security.pin_deadline is None
    assert alarm.started == 0
