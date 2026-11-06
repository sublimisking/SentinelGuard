import time

from sentinelguard.monitors.usb_event_listener import (
    USBEventListener
)


class USBMonitor:

    def __init__(self, security_manager=None):

        self.security_manager = security_manager
        self.enabled = False

        # Tekrarlanan bildirimleri kontrol etmek icin.
        self.last_events = {}
        self.duplicate_window = 0.3

        # Windows dinleyicisini olustur.
        self.listener = USBEventListener(
            self.handle_usb_event
        )

    def start_session(self):

        if self.enabled:
            return

        self.enabled = True
        self.last_events.clear()

        try:
            self.listener.start()
        except Exception:
            self.enabled = False
            raise

        print("USBMonitor: Koruma izleme aktif.")

    def handle_usb_event(self, event_type, device_path):

        if not self.enabled:
            return

        # Ayni cihazdan cok kisa araliklarla gelen
        # ayni tip bildirimleri filtrele.
        key = (
            event_type,
            device_path.casefold()
        )

        now = time.monotonic()
        last_time = self.last_events.get(key)

        if last_time is not None:
            if now - last_time < self.duplicate_window:
                return

        self.last_events[key] = now

        print(f"\nUSB OLAYI: {event_type}")
        print(f"Cihaz: {device_path}")

        # Guvenlik yoneticisine bildir.
        if self.security_manager is not None:
            self.security_manager.handle_event(
                event_type
            )

    def process_events(self):

        if not self.enabled:
            return

        self.listener.process_events()

    def stop_session(self):

        self.enabled = False

        try:
            self.listener.stop()
        finally:
            self.last_events.clear()

        print("USBMonitor: Izleme durduruldu.")
