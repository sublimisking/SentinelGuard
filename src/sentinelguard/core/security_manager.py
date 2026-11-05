class SecurityManager:
    # Alarm tetikleyebilen olay turleri
    ALARM_EVENTS = frozenset({
    "POWER_DISCONNECTED",
    "USB_CONNECTED",
    "INPUT_DETECTED",
    "MOTION_DETECTED",
    "PERSON_DETECTED"
})

    def __init__(self, alarm_manager):
        self.is_armed = False
        self.alarm_manager = alarm_manager

    def arm(self):
        if self.is_armed:
            return

        self.is_armed = True
        print("SentinelGuard koruma modu aktif.")

    def disarm(self):
        if not self.is_armed:
            return

        self.alarm_manager.stop_alarm()
        self.is_armed = False

        print("SentinelGuard koruma modu kapatildi.")

    def handle_event(self, event_type: str) -> bool:
        if not self.is_armed:
            return False

        if event_type not in self.ALARM_EVENTS:
            print(f"Taninmayan veya izin verilmeyen olay: {event_type}")
            return False

        print(f"Guvenlik olayi algilandi: {event_type}")
        self.alarm_manager.start_alarm()

        return True
