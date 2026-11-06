from types import SimpleNamespace
from sentinelguard.monitors.power_monitor import PowerMonitor


class FakeSecurityManager:

    def __init__(self):
        self.events = []

    def handle_event(self, event_type):
        self.events.append(event_type)
        return True


def test_power_disconnected_triggers_event(monkeypatch):

    # 1. Sahte batarya durumlari
    states = iter([True, False])

    def fake_sensors_battery():
        return SimpleNamespace(
            power_plugged=next(states)
        )

    # 2. Gercek psutil fonksiyonunu gecici degistir
    monkeypatch.setattr(
        "sentinelguard.monitors.power_monitor.psutil.sensors_battery",
        fake_sensors_battery
    )

    # 3. Test nesnelerini olustur
    fake_security = FakeSecurityManager()
    monitor = PowerMonitor(fake_security)

    # 4. Izlemeyi baslat
    monitor.start_session()

    # 5. Sarj durumunu tekrar kontrol et
    monitor.check_power()

    # 6. Sonuclari kontrol et
    assert fake_security.events == ["POWER_DISCONNECTED"]
    assert monitor.previous_state is False

def test_monitor_disabled_when_started_unplugged(monkeypatch):

    # 1. Sarj kablosu baslangicta cikarilmis
    def fake_sensors_battery():
        return SimpleNamespace(
            power_plugged=False
        )

    # 2. Gercek psutil fonksiyonunu sahte fonksiyonla degistir
    monkeypatch.setattr(
        "sentinelguard.monitors.power_monitor.psutil.sensors_battery",
        fake_sensors_battery
    )

    # 3. Test nesnelerini olustur
    fake_security = FakeSecurityManager()
    monitor = PowerMonitor(fake_security)

    # 4. Izlemeyi baslat
    monitor.start_session()

    # 5. Kontrol yap
    monitor.check_power()

    # 6. Beklenen sonuclari kontrol et
    assert monitor.enabled is False
    assert monitor.previous_state is False
    assert fake_security.events == []

def test_no_event_when_power_stays_connected(monkeypatch):

    states = iter([True, True])

    def fake_sensors_battery():
        return SimpleNamespace(
            power_plugged=next(states)
        )

    monkeypatch.setattr(
        "sentinelguard.monitors.power_monitor.psutil.sensors_battery",
        fake_sensors_battery
    )

    fake_security = FakeSecurityManager()
    monitor = PowerMonitor(fake_security)

    monitor.start_session()
    monitor.check_power()

    assert fake_security.events == []
    assert monitor.previous_state is True
    assert monitor.enabled is True

def test_no_event_when_battery_state_is_none(monkeypatch):

    states = iter([True, None])

    def fake_sensors_battery():
        state = next(states)

        if state is None:
            return None

        return SimpleNamespace(
            power_plugged=state
        )

    monkeypatch.setattr(
        "sentinelguard.monitors.power_monitor.psutil.sensors_battery",
        fake_sensors_battery
    )

    fake_security = FakeSecurityManager()
    monitor = PowerMonitor(fake_security)

    monitor.start_session()
    monitor.check_power()

    assert fake_security.events == []
    assert monitor.previous_state is True
    assert monitor.enabled is True

def test_no_event_after_stop_session(monkeypatch):
    states = iter([True, False])

    def fake_sensors_battery():
        return SimpleNamespace(
            power_plugged=next(states)
        )

    monkeypatch.setattr(
        "sentinelguard.monitors.power_monitor.psutil.sensors_battery",
        fake_sensors_battery
    )

    fake_security = FakeSecurityManager()
    monitor = PowerMonitor(fake_security)

    monitor.start_session()
    monitor.stop_session()
    monitor.check_power()

    assert fake_security.events == []
    assert monitor.previous_state is None
    assert monitor.enabled is False


def test_no_event_when_battery_state_is_none(monkeypatch):

    states = iter([True, True, None, None])

    def fake_sensors_battery():
        state = next(states)

        if state is None:
            return None

        return SimpleNamespace(power_plugged=state)

    monkeypatch.setattr(
        "sentinelguard.monitors.power_monitor.psutil.sensors_battery",
        fake_sensors_battery
    )

    fake_security = FakeSecurityManager()
    monitor = PowerMonitor(fake_security)

    monitor.start_session()
    monitor.check_power()
    monitor.check_power()
    monitor.check_power()

    assert monitor.enabled is True
    assert monitor.previous_state is True
    assert fake_security.events == []

def test_power_disconnection_after_temporary_battery_unavailability(monkeypatch):

    states = iter([True, None, None, False])

    def fake_sensors_battery():
        state = next(states)

        if state is None:
            return None

        return SimpleNamespace(power_plugged=state)

    monkeypatch.setattr(
        "sentinelguard.monitors.power_monitor.psutil.sensors_battery",
        fake_sensors_battery
    )

    fake_security = FakeSecurityManager()
    monitor = PowerMonitor(fake_security)

    monitor.start_session()

    monitor.check_power()
    assert fake_security.events == []

    monitor.check_power()
    assert fake_security.events == []

    monitor.check_power()
    assert fake_security.events == ["POWER_DISCONNECTED"]

    assert monitor.enabled is True
    assert monitor.previous_state is False

def test_reconnecting_power_does_not_trigger_new_event(monkeypatch):
    states = iter([True, False, True])

    def fake_sensors_battery():
        state = next(states)
        return SimpleNamespace(power_plugged=state)

    monkeypatch.setattr(
        "sentinelguard.monitors.power_monitor.psutil.sensors_battery",
        fake_sensors_battery
    )

    fake_security = FakeSecurityManager()
    monitor = PowerMonitor(fake_security)

    monitor.start_session()

    monitor.check_power()
    assert fake_security.events == ["POWER_DISCONNECTED"]

    monitor.check_power()
    assert fake_security.events == ["POWER_DISCONNECTED"]

    assert monitor.enabled is True
    assert monitor.previous_state is True

def test_multiple_power_disconnections(monkeypatch):

    states = iter([True, False, True, False])

    def fake_sensors_battery():
        return SimpleNamespace(
            power_plugged=next(states)
        )

    monkeypatch.setattr(
        "sentinelguard.monitors.power_monitor.psutil.sensors_battery",
        fake_sensors_battery
    )

    fake_security = FakeSecurityManager()
    monitor = PowerMonitor(fake_security)

    monitor.start_session()
    monitor.check_power()
    assert fake_security.events == ["POWER_DISCONNECTED"]

    monitor.check_power()
    assert len(fake_security.events) == 1

    monitor.check_power()
    assert fake_security.events == [
        "POWER_DISCONNECTED",
        "POWER_DISCONNECTED"
]

    assert monitor.enabled is True
    assert monitor.previous_state is False

def test_monitor_disabled_when_battery_unavailable_at_start(monkeypatch):

    def fake_sensors_battery():
        return None

    monkeypatch.setattr(
        "sentinelguard.monitors.power_monitor.psutil.sensors_battery",
        fake_sensors_battery
    )

    fake_security = FakeSecurityManager()
    monitor = PowerMonitor(fake_security)

    monitor.start_session()

    assert monitor.enabled is False
    assert monitor.previous_state is None

    monitor.check_power()

    assert fake_security.events == []
    assert monitor.enabled is False
    assert monitor.previous_state is None