import pytest

from sentinelguard.core.pin_manager import PinManager
from sentinelguard.core.security_manager import SecurityManager


class FakeAlarmManager:

    def __init__(self):
        self.start_count = 0
        self.stop_count = 0

    def start_alarm(self):
        self.start_count += 1

    def stop_alarm(self):
        self.stop_count += 1


@pytest.fixture
def system(tmp_path):

    pin_manager = PinManager(
        tmp_path / "pin.json",
        iterations=2000
    )

    pin_manager.set_pin("864201")

    alarm = FakeAlarmManager()
    now = [100.0]

    security = SecurityManager(
        alarm,
        pin_verifier=pin_manager.verify_pin,
        clock=lambda: now[0]
    )

    security.arm()

    return security, alarm, now


# TEST 1 - Dogru PIN sayac bitmeden korumayi kapatir.
def test_correct_pin_before_timeout(system):

    security, alarm, now = system

    security.handle_event("INPUT_DETECTED")

    now[0] = 105.0

    assert security.submit_pin("864201") is True
    assert security.is_armed is False
    assert alarm.start_count == 0
    assert alarm.stop_count == 1


# TEST 2 - Yanlis PIN sayaci sifirlamaz.
def test_wrong_pin_does_not_reset_timer(system):

    security, alarm, now = system

    security.handle_event("INPUT_DETECTED")

    now[0] = 105.0

    assert security.submit_pin("111111") is False
    assert security.is_armed is True
    assert security.pin_deadline == 110.0
    assert alarm.start_count == 0


# TEST 3 - USB alarmindan sonra PIN ile kapatma.
def test_correct_pin_stops_usb_alarm(system):

    security, alarm, now = system

    security.handle_event("USB_DISCONNECTED")

    assert alarm.start_count == 1

    assert security.submit_pin("864201") is True
    assert security.is_armed is False
    assert alarm.stop_count == 1


# TEST 4 - Sure dolunca alarm, sonra PIN ile kapatma.
def test_pin_works_after_timeout(system):

    security, alarm, now = system

    security.handle_event("INPUT_DETECTED")

    now[0] = 110.0

    assert security.check_pin_timeout() is True
    assert alarm.start_count == 1

    assert security.submit_pin("864201") is True
    assert security.is_armed is False
    assert alarm.stop_count == 1


# TEST 5 - Yanlis PIN calan alarmi durdurmaz.
def test_wrong_pin_cannot_stop_alarm(system):

    security, alarm, now = system

    security.handle_event("POWER_DISCONNECTED")

    assert alarm.start_count == 1

    assert security.submit_pin("000000") is False
    assert security.is_armed is True
    assert alarm.stop_count == 0


# TEST 6 - Olay yokken de dogru PIN ile kapatilabilir.
def test_correct_pin_disarms_without_event(system):

    security, alarm, now = system

    assert security.submit_pin("864201") is True
    assert security.is_armed is False
    assert alarm.stop_count == 1
