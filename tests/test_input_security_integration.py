from sentinelguard.core.security_manager import SecurityManager
from sentinelguard.monitors.input_monitor import InputMonitor


class FakeAlarmManager:

    def __init__(self):
        self.start_count = 0
        self.stop_count = 0

    def start_alarm(self):
        self.start_count += 1

    def stop_alarm(self):
        self.stop_count += 1


def test_input_starts_pin_countdown(monkeypatch):

    alarm = FakeAlarmManager()
    now = [100.0]

    security = SecurityManager(
        alarm,
        clock=lambda: now[0]
    )

    monitor = InputMonitor(security)

    timestamps = iter([1000, 1100])

    monkeypatch.setattr(
        monitor,
        "get_last_input_time",
        lambda: next(timestamps)
    )

    security.arm()
    monitor.start_session()

    result = monitor.check_input()

    assert result is True
    assert security.pin_deadline == 110.0
    assert alarm.start_count == 0


def test_repeated_input_does_not_restart_countdown(monkeypatch):

    alarm = FakeAlarmManager()
    now = [100.0]

    security = SecurityManager(
        alarm,
        clock=lambda: now[0]
    )

    monitor = InputMonitor(security)

    timestamps = iter([1000, 1100])

    monkeypatch.setattr(
        monitor,
        "get_last_input_time",
        lambda: next(timestamps)
    )

    security.arm()
    monitor.start_session()

    monitor.check_input()

    first_deadline = security.pin_deadline

    now[0] = 105.0

    result = monitor.check_input()

    assert result is False
    assert security.pin_deadline == first_deadline
    assert alarm.start_count == 0


def test_alarm_starts_after_ten_seconds():

    alarm = FakeAlarmManager()
    now = [100.0]

    security = SecurityManager(
        alarm,
        clock=lambda: now[0]
    )

    security.arm()
    security.handle_event("INPUT_DETECTED")

    now[0] = 109.9

    assert security.check_pin_timeout() is False
    assert alarm.start_count == 0

    now[0] = 110.0

    assert security.check_pin_timeout() is True
    assert alarm.start_count == 1

    # Sure dolduktan sonra alarm tekrar baslamasin.
    assert security.check_pin_timeout() is False
    assert alarm.start_count == 1


def test_correct_pin_disarms_before_timeout():

    alarm = FakeAlarmManager()
    now = [100.0]

    security = SecurityManager(
        alarm,
        pin_verifier=lambda pin: pin == "1234",
        clock=lambda: now[0]
    )

    security.arm()
    security.handle_event("INPUT_DETECTED")

    now[0] = 105.0

    assert security.submit_pin("1234") is True
    assert security.is_armed is False
    assert alarm.start_count == 0
    assert alarm.stop_count == 1


def test_wrong_pin_does_not_reset_countdown():

    alarm = FakeAlarmManager()
    now = [100.0]

    security = SecurityManager(
        alarm,
        pin_verifier=lambda pin: pin == "1234",
        clock=lambda: now[0]
    )

    security.arm()
    security.handle_event("INPUT_DETECTED")

    now[0] = 105.0

    assert security.submit_pin("9999") is False
    assert security.pin_deadline == 110.0

    now[0] = 110.0

    assert security.check_pin_timeout() is True
    assert alarm.start_count == 1


def test_usb_event_still_triggers_immediate_alarm():

    alarm = FakeAlarmManager()
    security = SecurityManager(alarm)

    security.arm()

    security.handle_event("USB_DISCONNECTED")

    assert alarm.start_count == 1
    assert security.pin_deadline is None
