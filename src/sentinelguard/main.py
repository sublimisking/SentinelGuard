
import time

import customtkinter as ctk
from tkinter import messagebox

from sentinelguard.core.audio_manager import AudioManager
from sentinelguard.core.alarm_manager import AlarmManager
from sentinelguard.core.security_manager import SecurityManager
from sentinelguard.core.pin_manager import (
    PinManager,
    PinStorageError
)

from sentinelguard.monitors.power_monitor import PowerMonitor
from sentinelguard.monitors.usb_monitor import USBMonitor
from sentinelguard.monitors.input_monitor import InputMonitor

from sentinelguard.ui.theme import (
    configure_theme,
    center_window
)

from sentinelguard.ui.main_dashboard import MainDashboard
from sentinelguard.ui.pin_setup_window import PinSetupWindow
from sentinelguard.ui.pin_window import PinWindow
from sentinelguard.ui.audio_settings_window import AudioSettingsWindow


# ==================================================
# ILK KURULUM - SES CIKISI
# ==================================================

def ensure_alarm_speaker(root, audio_manager):
    """
    Kayitli hoparlor yoksa grafik arayuzlu
    ses ayarlari penceresini acar.
    """

    saved_speaker = audio_manager.load_speaker_selection()

    if saved_speaker is not None:
        return True

    dialog = AudioSettingsWindow(
        root,
        audio_manager,
        required=True
    )

    root.wait_window(dialog)

    return (
        audio_manager.load_speaker_selection()
        is not None
    )


# ==================================================
# ILK KURULUM - PIN
# ==================================================

def ensure_pin_configured(root, pin_manager):
    """
    PIN yoksa olusturma penceresini acar.
    PIN varsa kaydin okunabilirligini kontrol eder.
    """

    if pin_manager.has_pin():
        pin_manager.verify_pin("000000")
        return True

    dialog = PinSetupWindow(
        root,
        pin_manager
    )

    root.wait_window(dialog)

    return dialog.created


# ==================================================
# GUVENLIK OLAY YONLENDIRICISI
# ==================================================

class SecurityEventRouter:
    """
    Sensorlerden gelen olaylari SecurityManager'a
    iletir ve kabul edilen olaylarda PIN ekranini acar.
    """

    def __init__(self, security_manager, on_event):
        self.security_manager = security_manager
        self.on_event = on_event

    def handle_event(self, event_type):

        accepted = self.security_manager.handle_event(
            event_type
        )

        if accepted:
            self.on_event()

        return accepted


# ==================================================
# SENTINELGUARD UYGULAMASI
# ==================================================

class SentinelGuardApp:

    def __init__(self, root, audio_manager, pin_manager):

        self.root = root
        self.audio_manager = audio_manager
        self.pin_manager = pin_manager

        # Acik ses ayarlari penceresini takip eder.
        self.audio_window = None

        # Uygulama durumu
        self.arming_after_id = None
        self.next_power_check = 0.0
        self.monitor_fault = False
        self.closed = False

        # ------------------------------------------
        # GUVENLIK MODULLERI
        # ------------------------------------------

        self.alarm_manager = AlarmManager(
            audio_manager
        )

        self.security_manager = SecurityManager(
            self.alarm_manager,
            pin_verifier=pin_manager.verify_pin
        )

        # ------------------------------------------
        # PIN KILIT EKRANI
        # ------------------------------------------

        self.pin_window = PinWindow(
            root,
            self.security_manager,
            on_disarmed=self.on_disarmed
        )

        # ------------------------------------------
        # GUVENLIK OLAY YONLENDIRICISI
        # ------------------------------------------

        self.event_router = SecurityEventRouter(
            self.security_manager,
            self.show_pin_window
        )

        # ------------------------------------------
        # SENSORLER
        # ------------------------------------------

        self.power_monitor = PowerMonitor(
            self.event_router
        )

        self.usb_monitor = USBMonitor(
            self.event_router
        )

        self.input_monitor = InputMonitor(
            self.event_router
        )

        # ------------------------------------------
        # ANA ARAYUZ
        # ------------------------------------------

        self.dashboard = MainDashboard(
            root,
            on_arm=self.prepare_arm,
            on_audio_settings=self.open_audio_settings
        )

        self.status_var = self.dashboard.status_var
        self.arm_button = self.dashboard.arm_button

        # ------------------------------------------
        # PENCERE KAPATMA
        # ------------------------------------------

        root.protocol(
            "WM_DELETE_WINDOW",
            self.close
        )

        # ------------------------------------------
        # SENSOR KONTROL DONGUSU
        # ------------------------------------------

        root.after(
            50,
            self.tick
        )

    # ==================================================
    # SES AYARLARI PENCERESI
    # ==================================================

    def open_audio_settings(self):

        # Koruma aktifken ses ayarlari degistirilmesin.
        if self.security_manager.is_armed:
            return

        # Koruma baslatma geri sayimi devam ediyorsa acma.
        if self.arming_after_id is not None:
            return

        # Pencere zaten aciksa yeniden olusturma.
        if (
            self.audio_window is not None
            and self.audio_window.winfo_exists()
        ):
            self.audio_window.lift()
            self.audio_window.focus_set()
            return

        try:
            self.audio_window = AudioSettingsWindow(
                self.root,
                self.audio_manager,
                required=False
            )

        except Exception as error:
            messagebox.showerror(
                "Ses Ayarlari Hatasi",
                str(error),
                parent=self.root
            )

    # ==================================================
    # KORUMAYI ETKINLESTIRMEYE HAZIRLIK
    # ==================================================

    def prepare_arm(self):

        if self.security_manager.is_armed:
            return

        if self.arming_after_id is not None:
            return

        # Ses ayarlari penceresi aciksa korumayi baslatma.
        if (
            self.audio_window is not None
            and self.audio_window.winfo_exists()
        ):
            return

        # Kayitli hoparlor halen kullanilabilir olmali.
        if self.audio_manager.load_speaker_selection() is None:
            self.status_var.set(
                "Once alarm hoparlorunu secmelisiniz."
            )
            self.open_audio_settings()
            return

        self.arm_button.configure(
            state="disabled"
        )

        self.status_var.set(
            "3 saniye sonra koruma baslayacak."
        )

        self.arming_after_id = self.root.after(
            3000,
            self.activate_protection
        )

    # ==================================================
    # KORUMAYI ETKINLESTIR
    # ==================================================

    def activate_protection(self):

        self.arming_after_id = None
        self.monitor_fault = False

        try:
            # Once guvenlik yoneticisini etkinlestir.
            self.security_manager.arm()

            # Ardindan sensorleri baslat.
            self.power_monitor.start_session()
            self.usb_monitor.start_session()
            self.input_monitor.start_session()

        except Exception as error:

            self.stop_monitors()

            self.security_manager.disarm()

            self.arm_button.configure(
                state="normal"
            )

            self.status_var.set(
                f"Koruma baslatilamadi: {error}"
            )

            print(f"Koruma baslatma hatasi: {error}")

            return

        self.next_power_check = time.monotonic()

        self.status_var.set(
            "Koruma aktif."
        )

        print("SentinelGuard koruma modu aktif.")

        # Koruma basladiginda ana pencereyi gizle.
        self.root.withdraw()

    # ==================================================
    # PIN EKRANINI GOSTER
    # ==================================================

    def show_pin_window(self):

        if not self.security_manager.is_armed:
            return

        if not self.pin_window.is_visible:
            self.pin_window.show()

    # ==================================================
    # ANA SENSOR KONTROL DONGUSU
    # ==================================================

    def tick(self):

        if self.closed:
            return

        try:

            if self.security_manager.is_armed:

                # USB olaylarini isle.
                self.usb_monitor.process_events()

                now = time.monotonic()

                # Sarj durumunu 0.5 saniyede bir kontrol et.
                if now >= self.next_power_check:

                    self.power_monitor.check_power()

                    self.next_power_check = (
                        time.monotonic() + 0.5
                    )

                # Klavye ve fare hareketlerini kontrol et.
                self.input_monitor.check_input()

                # PIN geri sayimi doldu mu?
                self.security_manager.check_pin_timeout()

        except Exception as error:

            if not self.monitor_fault:

                self.monitor_fault = True

                print(
                    f"SentinelGuard izleme hatasi: {error}"
                )

                # Sensor arizasi sessizce gecilmesin.
                self.alarm_manager.start_alarm()

                self.show_pin_window()

        finally:

            if not self.closed:

                self.root.after(
                    50,
                    self.tick
                )

    # ==================================================
    # SENSORLERI DURDUR
    # ==================================================

    def stop_monitors(self):

        monitors = (
            self.input_monitor,
            self.usb_monitor,
            self.power_monitor
        )

        for monitor in monitors:

            try:
                monitor.stop_session()

            except Exception as error:
                print(
                    f"Monitor durdurma hatasi: {error}"
                )

    # ==================================================
    # KORUMA KAPATILINCA
    # ==================================================

    def on_disarmed(self):

        self.stop_monitors()

        self.monitor_fault = False

        self.status_var.set(
            "Koruma kapali."
        )

        self.arm_button.configure(
            state="normal"
        )

        # Ana pencereyi geri goster.
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    # ==================================================
    # UYGULAMAYI KAPAT
    # ==================================================

    def close(self):

        if self.closed:
            return

        # Koruma aktifken PIN olmadan normal
        # pencere kapatma islemi yapilmasin.
        if self.security_manager.is_armed:

            if self.security_manager.pin_deadline is None:
                self.event_router.handle_event(
                    "INPUT_DETECTED"
                )

            self.show_pin_window()
            return

        # Koruma baslatma geri sayimini iptal et.
        if self.arming_after_id is not None:

            self.root.after_cancel(
                self.arming_after_id
            )

            self.arming_after_id = None

        self.closed = True

        self.stop_monitors()

        # Ses ayarlari penceresi aciksa kapat.
        if (
            self.audio_window is not None
            and self.audio_window.winfo_exists()
        ):
            self.audio_window.destroy()

        self.pin_window.destroy()

        self.root.destroy()


# ==================================================
# UYGULAMA BASLANGICI
# ==================================================

def main():

    # ------------------------------------------
    # TEMAYI AYARLA
    # ------------------------------------------

    configure_theme()

    # ------------------------------------------
    # ANA PENCEREYI OLUSTUR
    # ------------------------------------------

    root = ctk.CTk()

    root.title("SentinelGuard")

    root.configure(
        fg_color="#0B1220"
    )

    root.resizable(
        False,
        False
    )

    # Ekranin ortasinda ac.
    center_window(
        root,
        760,
        550
    )

    # ------------------------------------------
    # ILK KURULUM BILGISI
    # ------------------------------------------

    setup_label = ctk.CTkLabel(
        root,
        text=(
            "SentinelGuard\n"
            "Güvenlik sistemi hazırlanıyor..."
        ),
        font=ctk.CTkFont(
            size=23,
            weight="bold"
        ),
        text_color="#F8FAFC"
    )

    setup_label.pack(
        expand=True
    )

    # ------------------------------------------
    # TEMEL MODULLERI OLUSTUR
    # ------------------------------------------

    try:

        audio_manager = AudioManager()
        pin_manager = PinManager()

        # --------------------------------------
        # SES CIKISI KONTROLU
        # --------------------------------------

        if not ensure_alarm_speaker(
            root,
            audio_manager
        ):
            root.destroy()
            return

        # --------------------------------------
        # PIN KURULUMU
        # --------------------------------------

        if not ensure_pin_configured(
            root,
            pin_manager
        ):
            root.destroy()
            return

    except (
        PinStorageError,
        OSError,
        RuntimeError,
        ValueError
    ) as error:

        messagebox.showerror(
            "SentinelGuard Hatasi",
            str(error),
            parent=root
        )

        root.destroy()
        return

    # ------------------------------------------
    # KURULUM TAMAMLANDI
    # ------------------------------------------

    setup_label.destroy()

    # ------------------------------------------
    # ANA UYGULAMAYI BASLAT
    # ------------------------------------------

    app = SentinelGuardApp(
        root,
        audio_manager,
        pin_manager
    )

    root.deiconify()
    root.lift()

    # ------------------------------------------
    # TKINTER OLAY DONGUSU
    # ------------------------------------------

    root.mainloop()


if __name__ == "__main__":
    main()