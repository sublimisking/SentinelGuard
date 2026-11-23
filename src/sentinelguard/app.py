"""SentinelGuard uygulama denetleyicisi.

Arayuz (MainWindow) ve sensor / guvenlik modulleri arasindaki baglantiyi
burada kuruyoruz. Gercek Windows kilit ekrani saglamaz.
"""

import queue
import threading
import time
from tkinter import messagebox

from sentinelguard.core import update_manager
from sentinelguard.core.alarm_manager import AlarmManager
from sentinelguard.core.security_manager import SecurityManager
from sentinelguard.monitors.input_monitor import InputMonitor
from sentinelguard.monitors.power_monitor import PowerMonitor
from sentinelguard.monitors.usb_monitor import USBMonitor
from sentinelguard.ui.audio_settings_window import AudioSettingsWindow
from sentinelguard.ui.main_window import MainWindow
from sentinelguard.ui.pin_window import PinWindow
from sentinelguard.ui.pin_change_window import PinChangeWindow
from sentinelguard.version import __version__

# Acilistan kac ms sonra sessiz guncelleme kontrolu yapilacak.
STARTUP_UPDATE_CHECK_MS = 4000


class SecurityEventRouter:
    """Onaylanan sensor olaylarini guvenlik yoneticisine ve UI'ye iletir."""

    def __init__(self, security_manager, on_event):
        self.security_manager = security_manager
        self.on_event = on_event

    def handle_event(self, event_type):
        accepted = self.security_manager.handle_event(event_type)
        if accepted:
            self.on_event()
        return accepted


class SentinelGuardApp:
    """Koruma oturumu, sensor dongusu ve pencerelerin yasam dongusu."""

    def __init__(self, root, audio_manager, pin_manager):
        self.root = root
        self.audio_manager = audio_manager
        self.pin_manager = pin_manager
        self.audio_window = None
        self.pin_change_window = None
        self.arming_after_id = None
        self.next_power_check = 0.0
        self.monitor_fault = False
        self.closed = False

        # Guncelleme durumu. Ag islemleri arka plan thread'inde calisir,
        # sonuclar bu kuyruk uzerinden tick() icinde UI'ye aktarilir.
        self.update_queue = queue.Queue()
        self.update_state = "idle"  # idle|checking|available|downloading|ready
        self.update_manual = False
        self.available_update = None
        self.downloaded_installer = None

        self.alarm_manager = AlarmManager(audio_manager)
        self.security_manager = SecurityManager(
            self.alarm_manager,
            pin_verifier=pin_manager.verify_pin,
        )
        self.pin_window = PinWindow(
            root,
            self.security_manager,
            on_disarmed=self.on_disarmed,
        )
        self.event_router = SecurityEventRouter(
            self.security_manager,
            self.show_pin_window,
        )

        self.power_monitor = PowerMonitor(self.event_router)
        self.usb_monitor = USBMonitor(self.event_router)
        self.input_monitor = InputMonitor(self.event_router)

        self.main_window = MainWindow(
            root,
            on_arm=self.prepare_arm,
            on_audio_settings=self.open_audio_settings,
            on_pin_change=self.open_pin_change,
            on_update=self.on_update_button,
        )
        # Eski kodun ve testlerin kullanabildigi isimler.
        self.dashboard = self.main_window
        self.status_var = self.main_window.status_var
        self.arm_button = self.main_window.arm_button

        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(50, self.tick)
        root.after(
            STARTUP_UPDATE_CHECK_MS, lambda: self.check_for_updates(manual=False)
        )

    def _audio_dialog_is_open(self):
        return (
            self.audio_window is not None
            and bool(self.audio_window.winfo_exists())
        )

    def _pin_change_dialog_is_open(self):
        return (
            self.pin_change_window is not None
            and bool(self.pin_change_window.winfo_exists())
        )

    def open_pin_change(self):
        if self.closed or self.security_manager.is_armed:
            return
        if self.arming_after_id is not None or self._audio_dialog_is_open():
            return
        if self._pin_change_dialog_is_open():
            self.pin_change_window.lift()
            self.pin_change_window.focus_set()
            return
        self.pin_change_window = PinChangeWindow(self.root, self.change_pin)

    def change_pin(self, old_pin, new_pin):
        # Kaydetme aninda da koruma durumunu kontrol et.
        if self.closed or self.security_manager.is_armed or self.arming_after_id is not None:
            raise RuntimeError("PIN değiştirmek için korumanın kapalı olması gerekir.")
        changed = self.pin_manager.change_pin(old_pin, new_pin)
        if changed:
            self.status_var.set("PIN başarıyla değiştirildi. Koruma kapalı.")
        return changed

    def open_audio_settings(self):
        if self._pin_change_dialog_is_open():
            return
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
        if self._pin_change_dialog_is_open():
            return
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

        try:
            self.security_manager.arm()
            self.power_monitor.start_session()
            self.usb_monitor.start_session()
            self.input_monitor.start_session()
        except Exception as error:
            self.stop_monitors()
            try:
                self.security_manager.disarm()
            except Exception as cleanup_error:
                print(f"Koruma kapatılırken hata: {cleanup_error}")
            self.arm_button.configure(state="normal")
            self.status_var.set(f"Koruma başlatılamadı: {error}")
            return

        self.next_power_check = time.monotonic()
        self.status_var.set("Koruma aktif.")
        self.root.withdraw()

    def show_pin_window(self):
        if self.security_manager.is_armed and not self.pin_window.is_visible:
            self.pin_window.show()

    def tick(self):
        if self.closed:
            return

        try:
            self.process_update_results()
        except Exception as error:
            print(f"Güncelleme sonucu işlenemedi: {error}")

        try:
            if self.security_manager.is_armed:
                self.usb_monitor.process_events()

                now = time.monotonic()
                if now >= self.next_power_check:
                    self.power_monitor.check_power()
                    self.next_power_check = time.monotonic() + 0.5

                self.input_monitor.check_input()
                self.security_manager.check_pin_timeout()
        except Exception as error:
            if not self.monitor_fault:
                self.monitor_fault = True
                print(f"SentinelGuard izleme hatası: {error}")
                try:
                    self.alarm_manager.start_alarm()
                except Exception as alarm_error:
                    print(f"Alarm başlatma hatası: {alarm_error}")
                self.show_pin_window()
        finally:
            if not self.closed:
                self.root.after(50, self.tick)

    # ------------------------------------------------------------------
    # Guncelleme
    # ------------------------------------------------------------------

    def _update_blocked_reason(self):
        """Guncelleme kurulamiyorsa nedenini, kurulabiliyorsa None dondur."""
        if self.closed:
            return "Uygulama kapanıyor."
        if self.security_manager.is_armed:
            return "Koruma aktifken güncelleme yapılamaz."
        if self.arming_after_id is not None:
            return "Koruma başlatılırken güncelleme yapılamaz."
        if self._audio_dialog_is_open() or self._pin_change_dialog_is_open():
            return "Önce açık ayar penceresini kapatın."
        return None

    def _run_in_background(self, kind, func, *args):
        def worker():
            try:
                result = func(*args)
            except Exception as error:
                self.update_queue.put((kind, False, error))
            else:
                self.update_queue.put((kind, True, result))

        threading.Thread(target=worker, daemon=True).start()

    def on_update_button(self):
        if self.update_state in ("available", "ready"):
            self.install_update()
        else:
            self.check_for_updates(manual=True)

    def check_for_updates(self, manual=False):
        if self.closed or self.update_state not in ("idle", "available"):
            return
        self.update_state = "checking"
        self.update_manual = manual
        self.main_window.set_update_state(
            "Güncellemeler denetleniyor...", enabled=False
        )
        self._run_in_background("check", update_manager.check_for_update)

    def install_update(self):
        reason = self._update_blocked_reason()
        if reason is not None:
            self.main_window.set_update_state(reason, enabled=True)
            return
        info = self.available_update
        if info is None:
            return

        if self.downloaded_installer is not None:
            self._launch_downloaded_installer()
            return

        confirmed = messagebox.askyesno(
            "Güncelleme",
            f"SentinelGuard v{info.version} indirilip kurulacak.\n"
            "Kurulum sırasında uygulama kapanıp yeniden açılacak.\n\n"
            "Devam edilsin mi?",
            parent=self.root,
        )
        if not confirmed:
            return

        self.update_state = "downloading"
        self.main_window.set_update_state(
            f"v{info.version} indiriliyor...", enabled=False
        )
        self._run_in_background("download", update_manager.download_update, info)

    def _launch_downloaded_installer(self):
        # Son kontrol: indirme surerken koruma acilmis olabilir.
        reason = self._update_blocked_reason()
        if reason is not None:
            self.main_window.set_update_state(
                f"Güncelleme hazır, ancak kurulmadı: {reason} "
                "Koruma kapandıktan sonra tekrar deneyin.",
                button_text="Şimdi Kur",
            )
            return
        try:
            update_manager.launch_installer(self.downloaded_installer)
        except Exception as error:
            self.downloaded_installer = None
            self.update_state = "available"
            self.main_window.set_update_state(
                f"Kurulum başlatılamadı: {error}", button_text="Tekrar Dene"
            )
            return
        self.close()

    def process_update_results(self):
        while True:
            try:
                kind, ok, payload = self.update_queue.get_nowait()
            except queue.Empty:
                return
            if self.closed:
                return
            if kind == "check":
                self._on_check_finished(ok, payload)
            elif kind == "download":
                self._on_download_finished(ok, payload)

    def _on_check_finished(self, ok, payload):
        manual = self.update_manual
        if not ok:
            self.update_state = "idle"
            message = (
                f"Güncelleme denetlenemedi: {payload}"
                if manual else f"Yüklü sürüm: v{__version__}"
            )
            self.main_window.set_update_state(
                message, button_text="Güncellemeleri Denetle"
            )
            return
        if payload is None:
            self.update_state = "idle"
            self.main_window.set_update_state(
                f"SentinelGuard güncel (v{__version__}).",
                button_text="Güncellemeleri Denetle",
            )
            return

        self.available_update = payload
        self.update_state = "available"
        self.main_window.set_update_state(
            f"Yeni sürüm mevcut: v{payload.version} "
            f"(yüklü: v{__version__}).",
            button_text="İndir ve Kur",
        )
        if not self.security_manager.is_armed and self.arming_after_id is None:
            self.status_var.set(
                f"Yeni sürüm mevcut: v{payload.version}. Ayarlar > Güncellemeler."
            )

    def _on_download_finished(self, ok, payload):
        if not ok:
            self.update_state = "available"
            self.main_window.set_update_state(
                f"İndirme başarısız: {payload}", button_text="Tekrar Dene"
            )
            return
        self.downloaded_installer = payload
        self.update_state = "ready"
        self._launch_downloaded_installer()

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
        if self._pin_change_dialog_is_open():
            self.pin_change_window.destroy()
        self.pin_window.destroy()
        self.root.destroy()
