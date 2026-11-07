from sentinelguard.core.security_manager import SecurityManager

class FakeAlarmManager:

    def __init__(self):
        self.start_count = 0
        self.stop_count = 0

    def start_alarm(self):
        self.start_count += 1

    def stop_alarm(self):
        self.stop_count += 1

def test_alarm_when_armed():
    # 1. hazirlik
    fake_alarm = FakeAlarmManager()
    security = SecurityManager(fake_alarm)

    # 2. Koruma modunu ac

    security.arm()

    # 3. Sahte bir sarj kesintisi bildir
    result = security.handle_event("POWER_DISCONNECTED")

    # 4. bekledigimiz sonuclari kontrol et
    assert result is True
    assert fake_alarm.start_count == 1
    assert fake_alarm.stop_count == 0

def test_event_is_rejected_when_not_armed():
    # 1. hazirlik
    fake_alarm = FakeAlarmManager()
    security = SecurityManager(fake_alarm)

    # 2. Sahte bir sarj kesintisi bildir
    result = security.handle_event("POWER_DISCONNECTED")

    # . bekledigimiz sonuclari kontrol et
    assert result is False
    assert fake_alarm.start_count == 0
    assert fake_alarm.stop_count == 0

def test_alarm_stops_when_disarmed():
    # 1. hazirlik
    fake_alarm = FakeAlarmManager()
    security = SecurityManager(fake_alarm)

    # 2. Koruma modunu ac
    security.arm()

    # 3. Sahte bir sarj kesintisi bildir
    result = security.handle_event("POWER_DISCONNECTED")

    # 4. bekledigimiz sonuclari kontrol et
    assert result is True
    assert fake_alarm.start_count == 1

    # 5. Koruma modunu kapat
    security.disarm()

    # 6. Sahte bir sarj kesintisi bildir
    result = security.handle_event("POWER_DISCONNECTED")

    # 7. bekledigimiz sonuclari kontrol et
    assert result is False
    assert fake_alarm.start_count == 1
    assert fake_alarm.stop_count == 1

def test_invalid_event_is_rejected():
    # 1. hazirlik
    fake_alarm = FakeAlarmManager()
    security = SecurityManager(fake_alarm)

    # 2. Koruma modunu ac
    security.arm()

    # 3. Sahte bir gecersiz olay bildir
    result = security.handle_event("SOMETHING_RANDOM")

    # 4. bekledigimiz sonuclari kontrol et
    assert result is False
    assert fake_alarm.start_count == 0
    assert fake_alarm.stop_count == 0

def test_multiple_valid_events_call_alarm_each_time():

    fake_alarm = FakeAlarmManager()
    security = SecurityManager(fake_alarm)

    security.arm()

    result1 = security.handle_event("POWER_DISCONNECTED")
    result2 = security.handle_event("POWER_DISCONNECTED")

    assert result1 is True
    assert result2 is True
    assert fake_alarm.start_count == 2
    assert fake_alarm.stop_count == 0

def test_disarm_stops_alarm_and_rejects_future_events():


    fake_alarm = FakeAlarmManager()
    security = SecurityManager(fake_alarm)

    security.arm()

    security.handle_event("POWER_DISCONNECTED")

    security.disarm()

    result = security.handle_event("USB_CONNECTED")

    assert result is False
    assert fake_alarm.start_count == 1
    assert fake_alarm.stop_count == 1

def test_disarm_twice_stops_alarm_only_once():

    fake_alarm = FakeAlarmManager()
    security = SecurityManager(fake_alarm)

    security.arm()

    security.handle_event("POWER_DISCONNECTED")

    security.disarm()
    security.disarm()

    assert security.is_armed is False
    assert fake_alarm.start_count == 1
    assert fake_alarm.stop_count == 1

def test_rearm_after_disarm():

    fake_alarm = FakeAlarmManager()
    security = SecurityManager(fake_alarm)

    security.arm()
    result1 = security.handle_event("POWER_DISCONNECTED")
    security.disarm()

    security.arm()
    result2 = security.handle_event("USB_CONNECTED")

    assert result1 is True
    assert result2 is True
    assert fake_alarm.start_count == 2
    assert fake_alarm.stop_count == 1


import pytest


@pytest.mark.parametrize("event_type", [
    "POWER_DISCONNECTED",
    "USB_CONNECTED",
    "USB_DISCONNECTED",
    "INPUT_DETECTED",
    "MOTION_DETECTED",
    "PERSON_DETECTED",
])
def test_all_valid_events_types(event_type):

    alarm = FakeAlarmManager()
    security = SecurityManager(alarm)

    security.arm()

    result = security.handle_event(event_type)

    assert result is True

    if event_type == "INPUT_DETECTED":
        # Klavye/fare: alarm degil, PIN sayaci baslar.
        assert alarm.start_count == 0
        assert security.pin_deadline is not None

    else:
        # Diger olaylar aninda alarm baslatir.
        assert alarm.start_count == 1