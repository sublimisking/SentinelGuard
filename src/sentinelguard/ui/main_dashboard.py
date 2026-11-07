import customtkinter as ctk

from sentinelguard.ui.theme import (
    BACKGROUND,
    CARD,
    BORDER,
    PRIMARY,
    PRIMARY_HOVER,
    TEXT,
    MUTED,
    SUCCESS
)


class MainDashboard(ctk.CTkFrame):

    def __init__(
        self,
        parent,
        on_arm,
        on_audio_settings=None
    ):

        super().__init__(
            parent,
            fg_color=BACKGROUND,
            corner_radius=0
        )

        self.pack(
            fill="both",
            expand=True
        )

        # ======================================
        # UST BASLIK
        # ======================================

        header = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        header.pack(
            fill="x",
            padx=36,
            pady=(24, 14)
        )

        ctk.CTkLabel(
            header,
            text="◈  SentinelGuard",
            font=ctk.CTkFont(
                size=25,
                weight="bold"
            ),
            text_color=TEXT
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="WINDOWS SECURITY",
            font=ctk.CTkFont(size=11),
            text_color=MUTED
        ).pack(side="right")

        # ======================================
        # ANA PANEL
        # ======================================

        panel = ctk.CTkFrame(
            self,
            fg_color=CARD,
            corner_radius=18,
            border_width=1,
            border_color=BORDER
        )

        panel.pack(
            fill="x",
            padx=36,
            pady=8
        )

        ctk.CTkLabel(
            panel,
            text="Güvenlik Merkezi",
            font=ctk.CTkFont(
                size=24,
                weight="bold"
            ),
            text_color=TEXT
        ).pack(pady=(22, 8))

        # ======================================
        # KORUMA DURUMU
        # ======================================

        self.status_var = ctk.StringVar(
            value="Koruma kapalı."
        )

        ctk.CTkLabel(
            panel,
            textvariable=self.status_var,
            text_color=MUTED,
            font=ctk.CTkFont(size=14)
        ).pack(pady=(0, 14))

        # ======================================
        # SENSOR KARTLARI
        # ======================================

        sensor_frame = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )

        sensor_frame.pack(
            padx=20,
            pady=8
        )

        sensors = (
            ("⚡", "Güç izleme"),
            ("USB", "USB izleme"),
            ("⌨", "Giriş izleme")
        )

        for icon_text, name in sensors:

            card = ctk.CTkFrame(
                sensor_frame,
                width=185,
                height=105,
                fg_color=BACKGROUND,
                corner_radius=12
            )

            card.pack(
                side="left",
                padx=7
            )

            card.pack_propagate(False)

            ctk.CTkLabel(
                card,
                text=icon_text,
                font=ctk.CTkFont(
                    size=22,
                    weight="bold"
                ),
                text_color=SUCCESS
            ).pack(pady=(13, 5))

            ctk.CTkLabel(
                card,
                text=name,
                text_color=TEXT,
                font=ctk.CTkFont(size=13)
            ).pack()

        # ======================================
        # KORUMAYI ETKINLESTIR BUTONU
        # ======================================

        self.arm_button = ctk.CTkButton(
            panel,
            text="Korumayı Etkinleştir",
            width=360,
            height=46,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            font=ctk.CTkFont(
                size=15,
                weight="bold"
            ),
            command=on_arm
        )

        self.arm_button.pack(
            pady=(18, 10)
        )

        # ======================================
        # SES AYARLARI BUTONU
        # ======================================

        self.audio_button = None

        if on_audio_settings is not None:

            self.audio_button = ctk.CTkButton(
                panel,
                text="Ses Ayarları",
                width=360,
                height=42,
                corner_radius=12,
                fg_color="#263750",
                hover_color="#344760",
                text_color=TEXT,
                font=ctk.CTkFont(size=14),
                command=on_audio_settings
            )

            self.audio_button.pack(
                pady=(0, 20)
            )

        # ======================================
        # ALT BILGI
        # ======================================

        ctk.CTkLabel(
            self,
            text="SentinelGuard  •  Cihaz güvenliği",
            text_color=MUTED,
            font=ctk.CTkFont(size=12)
        ).pack(pady=(12, 10))
