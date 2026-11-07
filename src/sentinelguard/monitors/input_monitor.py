import ctypes
import time

from ctypes import wintypes


# Windows API'nin bekledigi veri yapisi
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwTime", wintypes.DWORD)
    ]


class InputMonitor:

    def __init__(self, security_manager=None):

        self.security_manager = security_manager
        self.input_detected = False
        self.enabled = False
        self.previous_input_time = None

        # Windows'un user32 kutuphanesine eris.
        self.user32 = ctypes.WinDLL(
            "user32",
            use_last_error=True
        )

        self.get_last_input_info = (
            self.user32.GetLastInputInfo
        )

        self.get_last_input_info.argtypes = [
            ctypes.POINTER(LASTINPUTINFO)
        ]

        self.get_last_input_info.restype = wintypes.BOOL

    def get_last_input_time(self):

        # Windows'a gonderecegimiz yapiyi hazirla.
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)

        # Windows'tan son giris zamanini al.
        success = self.get_last_input_info(
            ctypes.byref(info)
        )

        if not success:
            raise OSError(
                ctypes.get_last_error(),
                "GetLastInputInfo basarisiz."
            )

        return info.dwTime

    def start_session(self):

        if self.enabled:
            return

        self.previous_input_time = self.get_last_input_time()

        self.input_detected = False
        self.enabled = True

        print("InputMonitor: Izleme baslatildi.")

    
    def check_input(self):

        if not self.enabled:
            return False

        # Bu oturumda daha once giris algilandiysa
        # tekrar kontrol etme.
        if self.input_detected:
            return False

        current_input_time = self.get_last_input_time()

        if current_input_time == self.previous_input_time:
            return False

        # Ilk giris algilandi.
        self.previous_input_time = current_input_time
        self.input_detected = True

        print("InputMonitor: Kullanici girisi algilandi!")

        if self.security_manager is not None:
            self.security_manager.handle_event(
                "INPUT_DETECTED"
            )

        return True


    def stop_session(self):

        self.enabled = False
        self.previous_input_time = None
        self.input_detected = False

        print("InputMonitor: Izleme durduruldu.")


# BAGIMSIZ TEST - GERCEK SIREN CALMAZ
if __name__ == "__main__":

    monitor = InputMonitor()

    try:
        print("InputMonitor test modu.")
        print("3 saniye sonra izleme baslayacak.")
        print("Fare ve klavyeden elini cek.")

        time.sleep(3)

        monitor.start_session()

        print("Fareyi oynat veya bir tusa bas.")
        print("Cikmak icin Ctrl+C.")

        while True:
            monitor.check_input()
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nTest sonlandirildi.")

    finally:
        monitor.stop_session()
