from types import SimpleNamespace

import win32con

from sentinelguard.monitors.usb_event_listener import (
    USBEventListener
)

def test_usb_arrival_calls_callback(monkeypatch):

    received_events = []

    def fake_callback(event_type, device_path):
        received_events.append((event_type, device_path))

    listener = USBEventListener(fake_callback)

    fake_device = SimpleNamespace(
        devicetype=win32con.DBT_DEVTYP_DEVICEINTERFACE,
        name="USB_DEVICE_1"
    )

    monkeypatch.setattr(
        "sentinelguard.monitors.usb_event_listener."
        "win32gui_struct.UnpackDEV_BROADCAST",
        lambda lparam: fake_device
    )

    result = listener.on_device_change(
        0,
        win32con.WM_DEVICECHANGE,
        win32con.DBT_DEVICEARRIVAL,
        123
    )

    assert result == 1
    assert received_events == [
        ("USB_CONNECTED", "USB_DEVICE_1")
    ]

def test_usb_removal_calls_callback(monkeypatch):

    received_events = []

    def fake_callback(event_type, device_path):
        received_events.append((event_type, device_path))

    listener = USBEventListener(fake_callback)

    fake_device = SimpleNamespace(
        devicetype=win32con.DBT_DEVTYP_DEVICEINTERFACE,
        name="USB_DEVICE_1"
    )

    monkeypatch.setattr(
        "sentinelguard.monitors.usb_event_listener."
        "win32gui_struct.UnpackDEV_BROADCAST",
        lambda lparam: fake_device
    )

    result = listener.on_device_change(
        0,
        win32con.WM_DEVICECHANGE,
        win32con.DBT_DEVICEREMOVECOMPLETE,
        123
    )

    assert result == 1
    assert received_events == [
        ("USB_DISCONNECTED", "USB_DEVICE_1")
    ]

def test_invalid_usb_notifications_are_ignored(monkeypatch):

    received_events = []

    def fake_callback(event_type, device_path):
        received_events.append((event_type, device_path))

    listener = USBEventListener(fake_callback)

    # USB arayuzu yerine farkli bir aygit turu
    fake_device = SimpleNamespace(
        devicetype=win32con.DBT_DEVTYP_VOLUME,
        name="OTHER_DEVICE"
    )

    monkeypatch.setattr(
        "sentinelguard.monitors.usb_event_listener."
        "win32gui_struct.UnpackDEV_BROADCAST",
        lambda lparam: fake_device
    )

    # 1. Ilgisiz Windows olayi
    listener.on_device_change(
        0,
        win32con.WM_DEVICECHANGE,
        win32con.DBT_DEVICEQUERYREMOVE,
        123
    )

    # 2. Eksik cihaz bilgisi
    listener.on_device_change(
        0,
        win32con.WM_DEVICECHANGE,
        win32con.DBT_DEVICEARRIVAL,
        0
    )

    # 3. USB arayuzu olmayan aygit turu
    listener.on_device_change(
        0,
        win32con.WM_DEVICECHANGE,
        win32con.DBT_DEVICEARRIVAL,
        123
    )

    assert received_events == []
