import time


class SecurityManager:

    PIN_TIMEOUT_SECONDS = 10.0

    # Ilk 3 yanlis denemeden sonra artan bekleme (saniye).
    FREE_PIN_ATTEMPTS = 3
    LOCKOUT_STEPS = (5.0, 10.0, 20.0, 40.0, 60.0)

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
        self.failed_pin_attempts = 0
        self.lockout_until = None

    def lockout_remaining(self) -> float:
        """Yanlis denemeler yuzunden kalan bekleme suresi (saniye)."""
        if self.lockout_until is None:
            return 0.0
        return max(0.0, self.lockout_until - self.clock())

    def _reset_pin_attempts(self):
        self.failed_pin_attempts = 0
        self.lockout_until = None

    def _register_failed_pin(self):
        self.failed_pin_attempts += 1
        extra = self.failed_pin_attempts - self.FREE_PIN_ATTEMPTS

        if extra > 0:
            index = min(extra, len(self.LOCKOUT_STEPS)) - 1
            self.lockout_until = (
                self.clock() + self.LOCKOUT_STEPS[index]
            )

    def arm(self):

        if self.is_armed:
            return

        self.is_armed = True
        self.pin_deadline = None
        self.pin_timeout_triggered = False
        self._reset_pin_attempts()

        print("SentinelGuard koruma modu aktif.")

    def disarm(self):

        if not self.is_armed:
            return

        self.is_armed = False
        self.pin_deadline = None
        self.pin_timeout_triggered = False
        self._reset_pin_attempts()

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

        # Bekleme suresindeyken PIN'e bakma (tahmin saldirisini yavaslat).
        if self.lockout_remaining() > 0:
            print("PIN denemesi gecici olarak kilitli.")
            return False

        # Gercek PIN kaydiyla dogrula.
        if not self.pin_verifier(pin):
            self._register_failed_pin()
            print("Yanlis PIN.")
            return False

        # PIN dogruysa korumayi kapat.
        self.disarm()

        return True

