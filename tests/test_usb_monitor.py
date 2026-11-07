from sentinelguard.monitors.usb_monitor import USBMonitor

class FakeSecurityManager:

    def __init__(self):
        self.events = []

    def handle_event(self, event_type):
        self.events.append(event_type)
        return True

class FakeUSBEventListener:

    def __init__(self, callback):
        self.callback = callback
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def process_event(self):
        pass

    def simulate_device_event(self, event_type, device_path):
        if self.started:
            self.callback(event_type,device_path)

def test_usb_connection_sends_event(monkeypatch):
    monkeypatch.setattr(
    "sentinelguard.monitors.usb_monitor.USBEventListener",
    FakeUSBEventListener
)

    fake_security = FakeSecurityManager()
    monitor = USBMonitor(fake_security)

    monitor.start_session()
    monitor.listener.simulate_device_event(
        "USB_CONNECTED",
        "USB_DEVICE_1"
    )

    assert monitor.enabled is True
    assert fake_security.events == ["USB_CONNECTED"]

    monitor.stop_session()


def test_usb_disconnection_sends_event(monkeypatch):

    monkeypatch.setattr(
        "sentinelguard.monitors.usb_monitor.USBEventListener",
        FakeUSBEventListener
    )

    fake_security = FakeSecurityManager()
    monitor = USBMonitor(fake_security)

    monitor.start_session()

    monitor.listener.simulate_device_event(
        "USB_DISCONNECTED",
        "USB_DEVICE_1"
    )

    assert fake_security.events == ["USB_DISCONNECTED"]

    monitor.stop_session()

def test_usb_event_ignored_when_monitor_disabled(monkeypatch):

    monkeypatch.setattr(
        "sentinelguard.monitors.usb_monitor.USBEventListener",
        FakeUSBEventListener
    )

    fake_security = FakeSecurityManager()
    monitor = USBMonitor(fake_security)

    # start_session() cagrilmiyor.
    monitor.handle_usb_event(
        "USB_CONNECTED",
        "USB_DEVICE_1"
    )

    assert monitor.enabled is False
    assert fake_security.events == []

def test_duplicate_usb_event_is_ignored(monkeypatch):

    monkeypatch.setattr(
        "sentinelguard.monitors.usb_monitor.USBEventListener",
        FakeUSBEventListener
    )

    # Test boyunca zamani sabit tut.
    monkeypatch.setattr(
        "sentinelguard.monitors.usb_monitor.time.monotonic",
        lambda: 100.0
    )

    fake_security = FakeSecurityManager()
    monitor = USBMonitor(fake_security)

    monitor.start_session()

    monitor.listener.simulate_device_event(
        "USB_CONNECTED",
        "USB_DEVICE_1"
    )

    monitor.listener.simulate_device_event(
        "USB_CONNECTED",
        "USB_DEVICE_1"
    )

    assert fake_security.events == ["USB_CONNECTED"]
    assert len(fake_security.events) == 1

    monitor.stop_session()

def test_two_different_usb_devices(monkeypatch):

    monkeypatch.setattr(
        "sentinelguard.monitors.usb_monitor.USBEventListener",
        FakeUSBEventListener
    )

    fake_security = FakeSecurityManager()
    monitor = USBMonitor(fake_security)

    monitor.start_session()

    monitor.listener.simulate_device_event(
        "USB_CONNECTED",
        "USB_DEVICE_1"
    )

    monitor.listener.simulate_device_event(
        "USB_CONNECTED",
        "USB_DEVICE_2"
    )

    assert fake_security.events == [
        "USB_CONNECTED",
        "USB_CONNECTED"
    ]

    assert len(fake_security.events) == 2

    monitor.stop_session()

def test_usb_disconnected_and_reconnected(monkeypatch):

    monkeypatch.setattr(
        "sentinelguard.monitors.usb_monitor.USBEventListener",
        FakeUSBEventListener
    )

    fake_security = FakeSecurityManager()
    monitor = USBMonitor(fake_security)

    monitor.start_session()

    monitor.listener.simulate_device_event(
        "USB_DISCONNECTED",
        "USB_DEVICE_1"
    )

    monitor.listener.simulate_device_event(
        "USB_CONNECTED",
        "USB_DEVICE_1"
    )

    assert fake_security.events == [
        "USB_DISCONNECTED",
        "USB_CONNECTED"
    ]

    monitor.stop_session()

def test_no_usb_event_after_stop_session(monkeypatch):

    monkeypatch.setattr(
        "sentinelguard.monitors.usb_monitor.USBEventListener",
        FakeUSBEventListener
    )

    fake_security = FakeSecurityManager()
    monitor = USBMonitor(fake_security)

    monitor.start_session()

    monitor.stop_session()

    monitor.listener.simulate_device_event(
        "USB_CONNECTED",
        "USB_DEVICE_1"
    )

    assert monitor.enabled is False
    assert monitor.listener.started is False
    assert fake_security.events == []

def test_usb_monitor_can_restart(monkeypatch):

    monkeypatch.setattr(
        "sentinelguard.monitors.usb_monitor.USBEventListener",
        FakeUSBEventListener
    )

    fake_security = FakeSecurityManager()
    monitor = USBMonitor(fake_security)

    # Birinci koruma oturumu
    monitor.start_session()

    monitor.listener.simulate_device_event(
        "USB_CONNECTED",
        "USB_DEVICE_1"
    )

    monitor.stop_session()

    # Ikinci koruma oturumu
    monitor.start_session()

    monitor.listener.simulate_device_event(
        "USB_CONNECTED",
        "USB_DEVICE_1"
    )

    assert monitor.enabled is True
    assert fake_security.events == [
        "USB_CONNECTED",
        "USB_CONNECTED"
    ]

    monitor.stop_session()
