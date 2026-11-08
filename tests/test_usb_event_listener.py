"""USB listener testleri: callback kuyruktan ana thread'de islenir.

USBEventListener.on_device_change() artik sadece olayi kaydedebilir;
gercek callback'in cagirilmasi process_events() sonrasinda dogrulanir.
"""

from types import SimpleNamespace

import win32con

from sentinelguard.monitors.usb_event_listener import USBEventListener


def _emit_test_notification(monkeypatch, change_code):
    received_events = []
    listener = USBEventListener(
        lambda event_type, device_path: received_events.append(
            (event_type, device_path)
        )
    )

    fake_device = SimpleNamespace(
        devicetype=win32con.DBT_DEVTYP_DEVICEINTERFACE,
        name="USB_DEVICE_1",
    )

    monkeypatch.setattr(
        "sentinelguard.monitors.usb_event_listener."
        "win32gui_struct.UnpackDEV_BROADCAST",
        lambda lparam: fake_device,
    )

    result = listener.on_device_change(
        0,
        win32con.WM_DEVICECHANGE,
        change_code,
        123,
    )
    assert result == 1

    # Yeni implementasyonda olay USB thread'inden kuyruğa atilir,
    # uygulamanin ana dongusu bu metotla callback'i calistirir.
    listener.process_events()
    return received_events


def test_usb_arrival_calls_callback(monkeypatch):
    assert _emit_test_notification(
        monkeypatch, win32con.DBT_DEVICEARRIVAL
    ) == [("USB_CONNECTED", "USB_DEVICE_1")]


def test_usb_removal_calls_callback(monkeypatch):
    assert _emit_test_notification(
        monkeypatch, win32con.DBT_DEVICEREMOVECOMPLETE
    ) == [("USB_DISCONNECTED", "USB_DEVICE_1")]


def test_invalid_usb_notifications_are_ignored(monkeypatch):
    received_events = []
    listener = USBEventListener(
        lambda event_type, path: received_events.append((event_type, path))
    )

    result = listener.on_device_change(
        0,
        win32con.WM_DEVICECHANGE,
        0xDEADBEEF,
        123,
    )
    assert result == 1
    listener.process_events()
    assert received_events == []
