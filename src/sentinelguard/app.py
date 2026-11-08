"""SentinelGuard uygulama denetleyicisi.

Arayuz (MainWindow) ve sensor / guvenlik modulleri arasindaki baglantiyi
burada kuruyoruz. Gercek Windows kilit ekrani saglamaz.
"""

import time
from tkinter import messagebox

from sentinelguard.core.alarm_manager import AlarmManager
from sentinelguard.core.event_store import EventStore
from sentinelguard.core.security_manager import SecurityManager
from sentinelguard.monitors.input_monitor import InputMonitor
from sentinelguard.monitors.power_monitor import PowerMonitor
from sentinelguard.monitors.usb_monitor import USBMonitor
from sentinelguard.ui.audio_settings_window import AudioSettingsWindow
from sentinelguard.ui.main_window import MainWindow
from sentinelguard.ui.pin_window import PinWindow


class SecurityEventRouter:
    """Onaylanan sensor olaylarini guvenlik yoneticisine ve UI'ye iletir."""

    def __init__(self, security_manager, on_event, on_security_event=None):
        self.security_manager = security_manager
        self.on_event = on_event
        self.on_security_event = on_security_event

    def handle_event(self, event_type):
        accepted = self.security_manager.handle_event(event_type)
        if accepted:
            if self.on_security_event is not None:
                self.on_security_event(event_type)
            self.on_event()
        return accepted


class SentinelGuardApp:
    """Koruma oturumu, sensor dongusu ve pencerelerin yasam dongusu."""

    def __init__(self, root, audio_manager, pin_manager):
        self.root = root
        self.audio_manager = audio_manager
        self.pin_manager = pin_manager
        self.audio_window = None
        self.arming_after_id = None
        self.next_power_check = 0.0
        self.monitor_fault = False
        self.closed = False
        self._alarm_logged = False

        # Gecmis yazilamazsa güvenlik izlemesi durmamalidir.
        try:
            self.event_store = EventStore()
        except Exception as error:
            self.event_store = None
            print(f"Olay geçmişi başlatılamadı: {error}")

        self.alarm_manager = AlarmManager(audio_manager)
        self.security_manager = SecurityManager(
            self.alarm_manager,
            pin_verifier=self._verify_pin,
        )
        self.pin_window = PinWindow(
            root,
            self.security_manager,
            on_disarmed=self.on_disarmed,
        )
        self.event_router = SecurityEventRouter(
            self.security_manager,
            self.show_pin_window,
            on_security_event=self._on_security_event,
        )

        self.power_monitor = PowerMonitor(self.event_router)
        self.usb_monitor = USBMonitor(self.event_router)
        self.input_monitor = InputMonitor(self.event_router)

        self.main_window = MainWindow(
            root,
            on_arm=self.prepare_arm,
            on_audio_settings=self.open_audio_settings,
            on_get_events=self.get_recent_events,
        )
        # Eski kodun ve testlerin kullanabildigi isimler.
        self.dashboard = self.main_window
        self.status_var = self.main_window.status_var
        self.arm_button = self.main_window.arm_button

        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(50, self.tick)

    # Gecmis: UI, SQLite dosyasina dogrudan dokunmaz.
    def _log_event(self, code, category, message):
        store = getattr(self, "event_store", None)
        if store is None:
            return
        try:
            store.add(code, category, message)
        except Exception as error:
            print(f"Olay kaydı yazılamadı: {error}")

    def get_recent_events(self):
        store = getattr(self, "event_store", None)
        if store is None:
            raise RuntimeError("Olay geçmişi kullanılamıyor.")
        return store.recent(limit=100)

    def _verify_pin(self, pin):
        # PIN'i kesinlikle günlük kayıtlarına yazma.
        try:
            verified = self.pin_manager.verify_pin(pin)
        except Exception:
            self._log_event("PIN_ERROR", "auth", "PIN doğrulama hatası")
            raise

        self._log_event(
            "PIN_ACCEPTED" if verified else "PIN_REJECTED",
            "auth",
            "Doğru PIN girildi" if verified else "Yanlış PIN denemesi",
        )
        return verified

    def _record_alarm_start(self):
        if getattr(self, "_alarm_logged", False):
            return
        alarm_manager = getattr(self, "alarm_manager", None)
        if alarm_manager is not None and getattr(alarm_manager, "alarm_active", False):
            self._alarm_logged = True
            self._log_event("ALARM_STARTED", "alarm", "Siren başlatıldı")

    def _on_security_event(self, event_type):
        names = {
            "POWER_DISCONNECTED": "Şarj adaptörü çıkarıldı",
            "USB_CONNECTED": "USB cihazı bağlandı",
            "USB_DISCONNECTED": "USB cihazı çıkarıldı",
            "INPUT_DETECTED": "Klavye veya fare müdahalesi algılandı",
            "MOTION_DETECTED": "Cihaz hareketi algılandı",
            "PERSON_DETECTED": "Kişi algılandı",
        }
        self._log_event(event_type, "security", names.get(event_type, event_type))
        self._record_alarm_start()

    def _audio_dialog_is_open(self):
        return (
            self.audio_window is not None
            and bool(self.audio_window.winfo_exists())
        )

    def open_audio_settings(self):
        if self.closed or self.security_manager.is_armed:
            return
        if self.arming_after_id is not None:
            return
        if self._audio_dialog_is_open():
            self.audio_window.lift()
            self.audio_window.focus_set()
            return

        try:
            self.audio_window = AudioSettingsWindow(
                self.root, self.audio_manager, required=False
            )
        except Exception as error:
            messagebox.showerror(
                "Ses Ayarları Hatası", str(error), parent=self.root
            )

    def prepare_arm(self):
        if self.closed or self.security_manager.is_armed:
            return
        if self.arming_after_id is not None or self._audio_dialog_is_open():
            return

        try:
            if self.audio_manager.load_speaker_selection() is None:
                self.status_var.set("Önce alarm hoparlörünü seçmelisiniz.")
                self.open_audio_settings()
                return
            if not self.pin_manager.has_pin():
                self.status_var.set("PIN kaydı bulunamadı. Koruma açılamaz.")
                return
            # Eksik veya bozuk bir PIN kaydi ile koruma baslatma.
            self.pin_manager.verify_pin("000000")
        except Exception as error:
            self.status_var.set(f"Kurulum kontrolü başarısız: {error}")
            return

        self.arm_button.configure(state="disabled")
        self.status_var.set("3 saniye sonra koruma başlayacak.")
        self.arming_after_id = self.root.after(3000, self.activate_protection)

    def activate_protection(self):
        self.arming_after_id = None
        self.monitor_fault = False
        self._alarm_logged = False

        try:
            self.security_manager.arm()
            self.power_monitor.start_session()
            self.usb_monitor.start_session()
            self.input_monitor.start_session()
        except Exception as error:
            self._log_event("ARM_FAILED", "system", "Koruma başlatılamadı")
            self.stop_monitors()
            try:
                self.security_manager.disarm()
            except Exception as cleanup_error:
                print(f"Koruma kapatılırken hata: {cleanup_error}")
            self.arm_button.configure(state="normal")
            self.status_var.set(f"Koruma başlatılamadı: {error}")
            return

        self.next_power_check = time.monotonic()
        self._log_event("ARMED", "system", "Koruma etkinleştirildi")
        self.status_var.set("Koruma aktif.")
        self.root.withdraw()

    def show_pin_window(self):
        if self.security_manager.is_armed and not self.pin_window.is_visible:
            self.pin_window.show()

    def tick(self):
        if self.closed:
            return

        try:
            if self.security_manager.is_armed:
                self.usb_monitor.process_events()

                now = time.monotonic()
                if now >= self.next_power_check:
                    self.power_monitor.check_power()
                    self.next_power_check = time.monotonic() + 0.5

                self.input_monitor.check_input()
                if self.security_manager.check_pin_timeout():
                    self._log_event("PIN_TIMEOUT", "alarm", "PIN süresi doldu")
                    self._record_alarm_start()
        except Exception as error:
            if not self.monitor_fault:
                self.monitor_fault = True
                print(f"SentinelGuard izleme hatası: {error}")
                self._log_event("MONITOR_ERROR", "system", "Sensör izleme hatası")
                try:
                    self.alarm_manager.start_alarm()
                    self._record_alarm_start()
                except Exception as alarm_error:
                    self._log_event("ALARM_FAILED", "system", "Siren başlatılamadı")
                    print(f"Alarm başlatma hatası: {alarm_error}")
                self.show_pin_window()
        finally:
            if not self.closed:
                self.root.after(50, self.tick)

    def stop_monitors(self):
        for monitor in (
            self.input_monitor,
            self.usb_monitor,
            self.power_monitor,
        ):
            try:
                monitor.stop_session()
            except Exception as error:
                print(f"Monitör kapatma hatası: {error}")

    def on_disarmed(self):
        self._log_event("DISARMED", "system", "Koruma PIN ile kapatıldı")
        self._alarm_logged = False
        self.stop_monitors()
        self.monitor_fault = False
        self.status_var.set("Koruma kapalı.")
        self.arm_button.configure(state="normal")
        self.root.deiconify()
        self.root.lift()

    def close(self):
        if self.closed:
            return

        if self.security_manager.is_armed:
            if self.security_manager.pin_deadline is None:
                self.event_router.handle_event("INPUT_DETECTED")
            self.show_pin_window()
            return

        if self.arming_after_id is not None:
            self.root.after_cancel(self.arming_after_id)
            self.arming_after_id = None

        self.closed = True
        self.stop_monitors()

        if self._audio_dialog_is_open():
            self.audio_window.destroy()
        self.pin_window.destroy()
        self.root.destroy()
