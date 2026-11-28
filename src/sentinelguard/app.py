"""SentinelGuard uygulama denetleyicisi.

Arayuz (MainWindow) ve sensor / guvenlik modulleri arasindaki baglantiyi
burada kuruyoruz. Gercek Windows kilit ekrani saglamaz.
"""

import queue
import time
from tkinter import messagebox

from sentinelguard.core.alarm_manager import AlarmManager
from sentinelguard.core.camera_capture import (
    CameraCapture,
    load_camera_enabled,
    save_camera_enabled,
)
from sentinelguard.core.event_store import EventStore
from sentinelguard.core.pin_manager import check_pin_strength
from sentinelguard.core.security_manager import SecurityManager
from sentinelguard.monitors.input_monitor import InputMonitor
from sentinelguard.monitors.power_monitor import PowerMonitor
from sentinelguard.monitors.usb_monitor import USBMonitor
from sentinelguard.ui.audio_settings_window import AudioSettingsWindow
from sentinelguard.ui.main_window import MainWindow
from sentinelguard.ui.pin_window import PinWindow
from sentinelguard.ui.pin_change_window import PinChangeWindow


# Olay geçmişi sayfasında gösterilen olay sayısı.
RECENT_EVENT_LIMIT = 10


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

    def __init__(self, root, audio_manager, pin_manager, update_controller=None):
        self.root = root
        self.update_controller = update_controller
        self.audio_manager = audio_manager
        self.pin_manager = pin_manager
        self.audio_window = None
        self.pin_change_window = None
        self.arming_after_id = None
        self.next_power_check = 0.0
        self.monitor_fault = False
        self.closed = False
        self._alarm_logged = False

        # Gecmis yazilamazsa guvenlik izlemesi durmamalidir.
        try:
            self.event_store = EventStore()
        except Exception as error:
            self.event_store = None
            print(f"Olay geçmişi başlatılamadı: {error}")

        # Kamera hatasi korumayi asla durdurmamali.
        self._photo_results = queue.Queue()
        try:
            self.camera_capture = CameraCapture()
        except Exception as error:
            self.camera_capture = None
            print(f"Kamera modülü başlatılamadı: {error}")

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
            on_pin_change=self.open_pin_change,
            on_get_events=self.get_recent_events,
            on_list_photos=self.list_photos,
            on_delete_photo=self.delete_photo,
            on_get_camera_enabled=self.get_camera_enabled,
            on_set_camera_enabled=self.set_camera_enabled,
            on_check_update=self.check_updates if update_controller else None,
            on_install_update=self.install_update if update_controller else None,
        )
        # Eski kodun ve testlerin kullanabildigi isimler.
        self.dashboard = self.main_window
        self.status_var = self.main_window.status_var
        self.arm_button = self.main_window.arm_button

        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(50, self.tick)

        if update_controller is not None:
            update_controller.bind(
                on_status=self.main_window.set_update_status,
                on_available=self.main_window.set_update_available,
            )
            # Acilista sessizce bir kez bak.
            root.after(3000, self.check_updates)

    # --- Olay gecmisi: UI SQLite dosyasina dogrudan dokunmaz. ---

    def _log_event(
        self, code, category, message, photo_path=None, repeating=False
    ):
        store = getattr(self, "event_store", None)
        if store is None:
            return
        try:
            if repeating:
                store.add_repeating(code, category, message)
            else:
                store.add(code, category, message, photo_path=photo_path)
        except Exception as error:
            print(f"Olay kaydı yazılamadı: {error}")

    def get_recent_events(self):
        store = getattr(self, "event_store", None)
        if store is None:
            raise RuntimeError("Olay geçmişi kullanılamıyor.")
        return store.recent(limit=RECENT_EVENT_LIMIT)

    # --- Alarm fotografi ---

    def _settings_path(self):
        return getattr(self.audio_manager, "settings_path", None)

    def get_camera_enabled(self):
        return load_camera_enabled(self._settings_path())

    def set_camera_enabled(self, enabled):
        save_camera_enabled(enabled, self._settings_path())

    def list_photos(self):
        camera = getattr(self, "camera_capture", None)
        if camera is None:
            return []
        return camera.list_photos()

    def delete_photo(self, path):
        camera = getattr(self, "camera_capture", None)
        if camera is None:
            raise RuntimeError("Kamera modülü kullanılamıyor.")
        return camera.delete_photo(path)

    def _start_photo_capture(self):
        camera = getattr(self, "camera_capture", None)
        if camera is None:
            return
        try:
            if not self.get_camera_enabled():
                return
            # Thread yalnizca kuyruga yazar; veritabanina ana thread yazar.
            camera.capture_async(
                lambda path, error: self._photo_results.put((path, error))
            )
        except Exception as error:
            self._log_event("PHOTO_FAILED", "system", "Kamera başlatılamadı")
            print(f"Kamera hatası: {error}")

    def _drain_photo_results(self):
        results = getattr(self, "_photo_results", None)
        if results is None:
            return
        while True:
            try:
                path, error = results.get_nowait()
            except queue.Empty:
                return
            if path is not None:
                self._log_event(
                    "PHOTO_CAPTURED", "alarm",
                    "Kamera fotoğrafı kaydedildi", photo_path=path,
                )
            else:
                self._log_event(
                    "PHOTO_FAILED", "system",
                    f"Fotoğraf çekilemedi: {error}",
                )

    def _verify_pin(self, pin):
        # PIN degerini asla kayda yazma.
        try:
            verified = self.pin_manager.verify_pin(pin)
        except Exception:
            self._log_event("PIN_ERROR", "auth", "PIN doğrulama hatası")
            raise

        # Art arda yanlis denemeler tek satirda sayilir; gecmisi doldurmaz.
        self._log_event(
            "PIN_ACCEPTED" if verified else "PIN_REJECTED",
            "auth",
            "Doğru PIN girildi" if verified else "Yanlış PIN denemesi",
            repeating=not verified,
        )
        return verified

    def _lock_pin_record(self):
        lock = getattr(getattr(self, "pin_manager", None), "lock_record", None)
        if lock is not None:
            lock()

    def _unlock_pin_record(self):
        release = getattr(
            getattr(self, "pin_manager", None), "unlock_record", None
        )
        if release is not None:
            try:
                release()
            except Exception as error:
                print(f"PIN kaydı serbest bırakılamadı: {error}")

    def _record_alarm_start(self):
        if getattr(self, "_alarm_logged", False):
            return
        alarm_manager = getattr(self, "alarm_manager", None)
        if alarm_manager is not None and getattr(alarm_manager, "alarm_active", False):
            self._alarm_logged = True
            self._log_event("ALARM_STARTED", "alarm", "Siren başlatıldı")
            self._start_photo_capture()

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

    # --- Guncelleme ---

    def _update_busy(self):
        controller = getattr(self, "update_controller", None)
        return controller is not None and controller.busy

    def _can_install_update(self):
        return (
            not self.closed
            and not self.security_manager.is_armed
            and self.arming_after_id is None
        )

    def check_updates(self):
        if self.update_controller is None or self.closed:
            return
        self.update_controller.check()

    def install_update(self):
        if self.update_controller is None or not self._can_install_update():
            return
        if self._audio_dialog_is_open() or self._pin_change_dialog_is_open():
            return

        release = self.update_controller.release
        if release is None:
            return

        confirmed = messagebox.askyesno(
            "Güncelleme",
            f"{release.tag} indirilip kurulacak.\n"
            "SentinelGuard kurulum sırasında kapanır ve sonra tekrar açılır.\n\n"
            "Devam edilsin mi?",
            parent=self.root,
        )
        if not confirmed:
            return

        self._log_event("UPDATE_STARTED", "system", f"{release.tag} güncellemesi başlatıldı")
        self.update_controller.install(
            can_launch=self._can_install_update,
            shutdown=self.close,
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
        check_pin_strength(new_pin)
        changed = self.pin_manager.change_pin(old_pin, new_pin)
        self._log_event(
            "PIN_CHANGED" if changed else "PIN_CHANGE_FAILED",
            "auth",
            "PIN değiştirildi" if changed else "PIN değiştirme denemesi başarısız",
        )
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
        if self._update_busy():
            self.status_var.set("Güncelleme sürüyor. Bitince korumayı açın.")
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
            # PIN kaydini bellege al: disk dosyasi degistirilse bile gecerli.
            self._lock_pin_record()
            self.security_manager.arm()
            self.power_monitor.start_session()
            self.usb_monitor.start_session()
            self.input_monitor.start_session()
        except Exception as error:
            self._log_event("ARM_FAILED", "system", "Koruma başlatılamadı")
            self._unlock_pin_record()
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

        self._drain_photo_results()

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
        self._unlock_pin_record()
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
        if self._pin_change_dialog_is_open():
            self.pin_change_window.destroy()
        self.pin_window.destroy()
        self.root.destroy()
