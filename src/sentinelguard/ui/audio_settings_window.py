
import customtkinter as ctk

from sentinelguard.ui.theme import (
    BACKGROUND,
    CARD,
    BORDER,
    PRIMARY,
    PRIMARY_HOVER,
    TEXT,
    MUTED,
    DANGER,
    center_window
)


class AudioSettingsWindow(ctk.CTkToplevel):

    def __init__(
        self,
        parent,
        audio_manager,
        required=False
    ):
        super().__init__(parent)

        self.withdraw()

        self.audio_manager = audio_manager
        self.required = required
        self.saved = False

        self.output_ids = {}

        self.title("SentinelGuard | Alarm Hoparlörü")
        self.configure(fg_color=BACKGROUND)
        self.resizable(False, False)
        self.transient(parent)

        center_window(self, 540, 360, parent)

        panel = ctk.CTkFrame(
            self,
            fg_color=CARD,
            corner_radius=18,
            border_width=1,
            border_color=BORDER
        )
        panel.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        ctk.CTkLabel(
            panel,
            text="Alarm Hoparlörü",
            font=ctk.CTkFont(
                size=24,
                weight="bold"
            ),
            text_color=TEXT
        ).pack(pady=(25, 8))

        ctk.CTkLabel(
            panel,
            text="Alarmın çalacağı ses çıkışını seçin.",
            text_color=MUTED
        ).pack(pady=(0, 24))

        ctk.CTkLabel(
            panel,
            text="Ses çıkış cihazı",
            font=ctk.CTkFont(
                size=15,
                weight="bold"
            ),
            text_color=TEXT
        ).pack(anchor="w", padx=35)

        self.output_menu = ctk.CTkOptionMenu(
            panel,
            values=["Yükleniyor..."],
            width=430,
            height=42,
            dynamic_resizing=False,
            fg_color=BACKGROUND
        )
        self.output_menu.pack(pady=(10, 8))

        ctk.CTkLabel(
            panel,
            text="Dahili bilgisayar hoparlörünüzü seçin.",
            text_color=MUTED,
            font=ctk.CTkFont(size=12)
        ).pack(pady=(0, 12))

        self.feedback = ctk.CTkLabel(
            panel,
            text="",
            text_color=DANGER,
            wraplength=430
        )
        self.feedback.pack(pady=4)

        buttons = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )
        buttons.pack(pady=(8, 15))

        ctk.CTkButton(
            buttons,
            text="Yenile",
            width=125,
            command=self.refresh_devices
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            buttons,
            text="Vazgeç",
            width=125,
            fg_color=BACKGROUND,
            command=self.destroy
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            buttons,
            text="Kaydet",
            width=125,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            command=self.save
        ).pack(side="left", padx=5)

        self.refresh_devices()

        self.deiconify()
        self.after(100, self._activate)

    def _activate(self):

        if self.winfo_exists():
            self.lift()
            self.grab_set()
            self.focus_set()

    def refresh_devices(self):

        self.feedback.configure(text="")

        previous_selection = self.output_ids.get(
            self.output_menu.get()
        )

        try:
            outputs = self.audio_manager.get_audio_outputs()

            saved_speaker = (
                self.audio_manager.load_speaker_selection()
            )

        except Exception as error:
            self.feedback.configure(
                text=f"Hoparlörler okunamadı: {error}"
            )
            outputs = []
            saved_speaker = None

        self.output_ids = {
            f"{index}. {device.FriendlyName}": device.id
            for index, device in enumerate(outputs, 1)
        }

        labels = list(self.output_ids)

        self.output_menu.configure(
            values=labels or ["Hoparlör bulunamadı"]
        )

        selected_id = previous_selection or saved_speaker

        selected_label = next(
            (
                label
                for label, device_id in self.output_ids.items()
                if device_id == selected_id
            ),
            None
        )

        self.output_menu.set(
            selected_label
            or (
                labels[0]
                if labels
                else "Hoparlör bulunamadı"
            )
        )

    def save(self):

        speaker_id = self.output_ids.get(
            self.output_menu.get()
        )

        if speaker_id is None:
            self.feedback.configure(
                text="Lütfen bir hoparlör seçin."
            )
            return

        try:
            self.audio_manager.save_speaker_selection(
                speaker_id
            )

        except (OSError, ValueError, RuntimeError) as error:
            self.feedback.configure(
                text=f"Kaydetme hatası: {error}"
            )
            return

        self.saved = True
        self.destroy()
