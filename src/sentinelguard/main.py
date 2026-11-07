"""SentinelGuard uygulamasinin giris noktasi.

Bu dosya sadece ilk kurulum ile uygulama bilesenlerinin baslatilmasini yonetir.
Güvenlik döngüsü app.py, görsel arayüz main_window.py içindedir.
"""

import customtkinter as ctk
from tkinter import messagebox

from sentinelguard.app import SecurityEventRouter, SentinelGuardApp
from sentinelguard.core.audio_manager import AudioManager
from sentinelguard.core.pin_manager import PinManager, PinStorageError
from sentinelguard.ui.audio_settings_window import AudioSettingsWindow
from sentinelguard.ui.pin_setup_window import PinSetupWindow
from sentinelguard.ui.theme import BACKGROUND, center_window, configure_theme


# Mevcut testlerin ve importlarin kullanabilmesi icin bu iki fonksiyon
# main.py'de kalir. Güvenlik ve arayüz siniflari burada bulunmaz.
def ensure_alarm_speaker(root, audio_manager):
    """Kullanilabilir dahili hoparlor secilmeden kurulumu bitirme."""
    if audio_manager.load_speaker_selection() is not None:
        return True

    dialog = AudioSettingsWindow(root, audio_manager, required=True)
    root.wait_window(dialog)
    return audio_manager.load_speaker_selection() is not None


def ensure_pin_configured(root, pin_manager):
    """Var olan PIN'i kontrol et; yoksa ilk kurulum ekranini ac."""
    if pin_manager.has_pin():
        # Burada PIN tahmin etmiyoruz; sadece kaydin saglamligini
        # kontrol etmek icin dogrulama mekanizmasini calistiriyoruz.
        pin_manager.verify_pin("000000")
        return True

    dialog = PinSetupWindow(root, pin_manager)
    root.wait_window(dialog)
    return dialog.created


def main():
    configure_theme()

    root = ctk.CTk()
    root.title("SentinelGuard")
    root.configure(fg_color=BACKGROUND)
    root.resizable(False, False)
    center_window(root, 900, 600)

    loading = ctk.CTkLabel(
        root,
        text="SentinelGuard\nGüvenlik sistemi hazırlanıyor...",
        font=ctk.CTkFont(size=23, weight="bold"),
        text_color="#F8FAFC",
    )
    loading.pack(expand=True)

    try:
        audio_manager = AudioManager()
        pin_manager = PinManager()

        if not ensure_alarm_speaker(root, audio_manager):
            root.destroy()
            return

        if not ensure_pin_configured(root, pin_manager):
            root.destroy()
            return

        loading.destroy()
        app = SentinelGuardApp(root, audio_manager, pin_manager)

    except (PinStorageError, OSError, RuntimeError, ValueError) as error:
        messagebox.showerror("SentinelGuard Hatası", str(error), parent=root)
        root.destroy()
        return

    root.deiconify()
    root.lift()
    root.mainloop()


if __name__ == "__main__":
    main()
