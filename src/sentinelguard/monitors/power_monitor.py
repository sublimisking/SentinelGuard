import psutil


class PowerMonitor:
    def __init__(self, security_manager):
        self.security_manager = security_manager
        self.previous_state = None
        self.enabled = False

    def get_power_state(self):
        battery = psutil.sensors_battery()

        if battery is None:
            return None

        return battery.power_plugged

    def start_session(self):
        # Koruma basladiginda sarj durumunu kaydet.
        self.previous_state = self.get_power_state()

        # Baslangicta sarj takiliysa bu sensoru etkinlestir.
        self.enabled = self.previous_state is True

        if self.enabled:
            print("PowerMonitor: Sarj korumasi aktif.")
        else:
            print("PowerMonitor: Sarj korumasi devre disi.")

    def check_power(self):
        # Sarj korumasi kapaliysa kontrol etme.
        if not self.enabled:
            return

        current_state = self.get_power_state()

        # Batarya bilgisi okunamiyorsa o kontrolu atla.
        if current_state is None:
            return

        # Sarj baglantisi yeni kesildiyse olay bildir.
        if self.previous_state is True and current_state is False:
            print("PowerMonitor: Sarj kablosu cikarildi!")

            self.security_manager.handle_event(
                "POWER_DISCONNECTED"
            )

        # Son okunan durumu sakla.
        self.previous_state = current_state

    def stop_session(self):
        self.enabled = False
        self.previous_state = None

        print("PowerMonitor: Izleme durduruldu.")
