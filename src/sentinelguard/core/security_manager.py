import time


class SecurityManager:

    PIN_TIMEOUT_SECONDS = 10.0

    ALARM_EVENTS = frozenset({
        "POWER_DISCONNECTED",
        "USB_CONNECTED",
        "USB_DISCONNECTED",
        "INPUT_DETECTED",
        "MOTION_DETECTED",
        "PERSON_DETECTED",
    })

    def __init__(
        self,
        alarm_manager,
        pin_verifier=None,
        clock=None
    ):
        self.alarm_manager = alarm_manager
        self.pin_verifier = pin_verifier
        self.clock = clock if clock is not None else time.monotonic

        self.is_armed = False
        self.pin_deadline = None
        self.pin_timeout_triggered = False

    def arm(self):

        if self.is_armed:
            return

        self.is_armed = True
        self.pin_deadline = None
        self.pin_timeout_triggered = False

        print("SentinelGuard koruma modu aktif.")

    def disarm(self):

        if not self.is_armed:
            return

        self.is_armed = False
        self.pin_deadline = None
        self.pin_timeout_triggered = False

        self.alarm_manager.stop_alarm()

        print("SentinelGuard koruma modu kapatildi.")

    def handle_event(self, event_type: str) -> bool:

        if not self.is_armed:
            return False

        if event_type not in self.ALARM_EVENTS:
            print(f"Taninmayan olay: {event_type}")
            return False

        # Klavye/fare icin PIN suresi baslat.
        if event_type == "INPUT_DETECTED":

            if self.pin_deadline is not None:
                return False

            self.pin_deadline = (
                self.clock() + self.PIN_TIMEOUT_SECONDS
            )

            print("Giris algilandi. PIN icin 10 saniye.")
            return True

        # Diger guvenlik olaylari aninda alarm verir.
        self.alarm_manager.start_alarm()
        return True

    def check_pin_timeout(self) -> bool:

        if not self.is_armed:
            return False

        if self.pin_deadline is None:
            return False

        if self.pin_timeout_triggered:
            return False

        if self.clock() < self.pin_deadline:
            return False

        self.pin_timeout_triggered = True
        self.alarm_manager.start_alarm()

        print("PIN suresi doldu!")
        return True

    
    def submit_pin(self, pin: str) -> bool:

        # Koruma aktif degilse PIN dogrulama yapma.
        if not self.is_armed:
            return False

        # PIN dogrulama sistemi bagli olmali.
        if self.pin_verifier is None:
            return False

        # Bekleme suresi dolduysa once bunu isle.
        self.check_pin_timeout()

        # Gercek PIN kaydiyla dogrula.
        if not self.pin_verifier(pin):
            print("Yanlis PIN.")
            return False

        # PIN dogruysa korumayi kapat.
        self.disarm()

        return True

