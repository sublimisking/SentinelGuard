
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


class PinSetupWindow(ctk.CTkToplevel):

    def __init__(self, parent, pin_manager):
        super().__init__(parent)

        self.pin_manager = pin_manager
        self.created = False

        # PIN alanlari baslangicta gizli.
        self.pin_visible = False
        self.confirm_visible = False

        self.withdraw()
        self.title("SentinelGuard | PIN Kurulumu")
        self.configure(fg_color=BACKGROUND)
        self.resizable(False, False)

        self.protocol(
            "WM_DELETE_WINDOW",
            self.destroy
        )

        center_window(self, 500, 490, parent)

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
            padx=24,
            pady=24
        )

        # BASLIK
        ctk.CTkLabel(
            panel,
            text="◈  SentinelGuard",
            font=ctk.CTkFont(
                size=25,
                weight="bold"
            ),
            text_color=TEXT
        ).pack(pady=(28, 8))

        ctk.CTkLabel(
            panel,
            text="Güvenlik PIN'inizi oluşturun",
            font=ctk.CTkFont(
                size=17,
                weight="bold"
            ),
            text_color=TEXT
        ).pack(pady=(8, 6))

        ctk.CTkLabel(
            panel,
            text="6-12 haneli bir PIN belirleyin.",
            text_color=MUTED
        ).pack(pady=(0, 22))

        # ======================================
        # YENI PIN ALANI
        # ======================================

        pin_row = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )
        pin_row.pack(pady=8)

        self.pin_entry = ctk.CTkEntry(
            pin_row,
            width=270,
            height=44,
            placeholder_text="Yeni PIN",
            show="*",
            corner_radius=9,
            border_color=BORDER
        )

        self.pin_entry.pack(
            side="left",
            padx=(0, 8)
        )

        self.pin_show_button = ctk.CTkButton(
            pin_row,
            text="Göster",
            width=72,
            height=44,
            fg_color=BACKGROUND,
            hover_color=BORDER,
            command=self.toggle_pin_visibility
        )

        self.pin_show_button.pack(side="left")

        # ======================================
        # PIN TEKRAR ALANI
        # ======================================

        confirm_row = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )
        confirm_row.pack(pady=8)

        self.confirm_entry = ctk.CTkEntry(
            confirm_row,
            width=270,
            height=44,
            placeholder_text="PIN'i tekrar girin",
            show="*",
            corner_radius=9,
            border_color=BORDER
        )

        self.confirm_entry.pack(
            side="left",
            padx=(0, 8)
        )

        self.confirm_show_button = ctk.CTkButton(
            confirm_row,
            text="Göster",
            width=72,
            height=44,
            fg_color=BACKGROUND,
            hover_color=BORDER,
            command=self.toggle_confirm_visibility
        )

        self.confirm_show_button.pack(side="left")

        # ======================================
        # HATA MESAJI
        # ======================================

        self.feedback = ctk.CTkLabel(
            panel,
            text="",
            text_color=DANGER,
            wraplength=350
        )
        self.feedback.pack(pady=8)

        # ======================================
        # PIN OLUSTUR BUTONU
        # ======================================

        ctk.CTkButton(
            panel,
            text="PIN Oluştur",
            width=350,
            height=44,
            corner_radius=9,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            command=self.submit
        ).pack(pady=(6, 12))

        self.confirm_entry.bind(
            "<Return>",
            lambda event: self.submit()
        )

        self.deiconify()
        self.after(100, self._activate)

    # ======================================
    # PIN GOSTER / GIZLE
    # ======================================

    def toggle_pin_visibility(self):

        self.pin_visible = not self.pin_visible

        if self.pin_visible:

            self.pin_entry.configure(show="")

            self.pin_show_button.configure(
                text="Gizle"
            )

        else:

            self.pin_entry.configure(show="*")

            self.pin_show_button.configure(
                text="Göster"
            )

    # ======================================
    # PIN TEKRARINI GOSTER / GIZLE
    # ======================================

    def toggle_confirm_visibility(self):

        self.confirm_visible = not self.confirm_visible

        if self.confirm_visible:

            self.confirm_entry.configure(show="")

            self.confirm_show_button.configure(
                text="Gizle"
            )

        else:

            self.confirm_entry.configure(show="*")

            self.confirm_show_button.configure(
                text="Göster"
            )

    # ======================================
    # PENCEREYI AKTIFLESTIR
    # ======================================

    def _activate(self):

        if self.winfo_exists():
            self.lift()
            self.grab_set()
            self.pin_entry.focus_set()

    # ======================================
    # PIN KAYDET
    # ======================================

    def submit(self):

        pin = self.pin_entry.get()
        confirmation = self.confirm_entry.get()

        if pin != confirmation:

            self.feedback.configure(
                text="PIN'ler eşleşmiyor."
            )
            return

        try:

            self.pin_manager.set_pin(pin)

        except (
            ValueError,
            RuntimeError,
            OSError
        ) as error:

            self.feedback.configure(
                text=str(error)
            )
            return

        self.created = True
        self.destroy()