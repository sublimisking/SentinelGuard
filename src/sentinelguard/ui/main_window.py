"""SentinelGuard ana penceresi: yalnizca gorunum ve kullanici eylemleri.

Güvenlik mantığı bu dosyada bulunmaz. Butonlar app.py'den gelen
callback'leri çağırır; uygulama durumu status_var üzerinden güncellenir.
"""

import customtkinter as ctk

from sentinelguard.ui.theme import (
    BACKGROUND,
    CARD,
    BORDER,
    PRIMARY,
    PRIMARY_HOVER,
    TEXT,
    MUTED,
    SUCCESS,
)

SIDEBAR = "#101B2D"
SUCCESS_HOVER = "#16A34A"
ACTIVE_NAV = "#1D3B62"


class MainWindow(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        on_arm,
        on_audio_settings,
        on_pin_change=None,
        on_check_update=None,
        on_install_update=None,
    ):
        super().__init__(parent, fg_color=BACKGROUND, corner_radius=0)

        # Butonlar olusturulmadan once callback'leri sakla.
        self.on_arm = on_arm
        self.on_audio_settings = on_audio_settings
        self.on_pin_change = on_pin_change
        self.on_check_update = on_check_update
        self.on_install_update = on_install_update
        self.update_status_var = ctk.StringVar(value="Henüz kontrol edilmedi.")

        # app.py bu iki alani kullanir.
        self.status_var = ctk.StringVar(value="Koruma kapalı.")
        self.arm_button = None

        self.pages = {}
        self.nav_buttons = {}
        self.current_page = None

        self.pack(fill="both", expand=True)
        self._build_sidebar()
        self._build_content()
        self.show_page("home")

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self, width=210, fg_color=SIDEBAR, corner_radius=0
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="◈  SentinelGuard",
            font=ctk.CTkFont(size=21, weight="bold"),
            text_color=TEXT,
        ).pack(pady=(34, 6))

        ctk.CTkLabel(
            sidebar,
            text="SECURITY CENTER",
            font=ctk.CTkFont(size=10),
            text_color=MUTED,
        ).pack(pady=(0, 36))

        for key, name in (("home", "Ana Sayfa"), ("settings", "Ayarlar")):
            button = ctk.CTkButton(
                sidebar,
                text=name,
                width=182,
                height=44,
                corner_radius=10,
                fg_color="transparent",
                hover_color=ACTIVE_NAV,
                text_color=MUTED,
                anchor="w",
                command=lambda page=key: self.show_page(page),
            )
            button.pack(padx=14, pady=5)
            self.nav_buttons[key] = button

        ctk.CTkButton(
            sidebar,
            text="Olay Geçmişi (yakında)",
            width=182,
            height=44,
            state="disabled",
        ).pack(padx=14, pady=5)

        ctk.CTkLabel(
            sidebar,
            text="v0.1.0-beta  •  Test sürümü",
            font=ctk.CTkFont(size=11),
            text_color=MUTED,
        ).pack(side="bottom", pady=22)

    def _build_content(self):
        content = ctk.CTkFrame(
            self, fg_color=BACKGROUND, corner_radius=0
        )
        content.pack(side="left", fill="both", expand=True)

        self.page_title = ctk.CTkLabel(
            content,
            text="",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=TEXT,
        )
        self.page_title.pack(anchor="w", padx=30, pady=(26, 4))

        self.page_subtitle = ctk.CTkLabel(
            content, text="", font=ctk.CTkFont(size=13), text_color=MUTED
        )
        self.page_subtitle.pack(anchor="w", padx=30, pady=(0, 18))

        self.page_container = ctk.CTkFrame(
            content, fg_color="transparent"
        )
        self.page_container.pack(
            fill="both", expand=True, padx=30, pady=(0, 22)
        )

        self._build_home_page()
        self._build_settings_page()

    def _build_home_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["home"] = page

        hero = ctk.CTkFrame(
            page, fg_color=CARD, corner_radius=16,
            border_width=1, border_color=BORDER,
        )
        hero.pack(fill="x", pady=(0, 18))

        # Guncelleme varsa sag ustte yesil indirme ikonu gorunur.
        self.update_badge = ctk.CTkButton(
            hero, text="⬇", width=38, height=38, corner_radius=19,
            fg_color=SUCCESS, hover_color=SUCCESS_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=18, weight="bold"),
            command=lambda: self.show_page("settings"),
        )

        ctk.CTkLabel(
            hero, text="◈", font=ctk.CTkFont(size=42, weight="bold"),
            text_color=PRIMARY,
        ).pack(pady=(12, 0))

        ctk.CTkLabel(
            hero, text="Güvenlik Durumu",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT,
        ).pack(pady=(0, 6))

        ctk.CTkLabel(
            hero, textvariable=self.status_var,
            font=ctk.CTkFont(size=14), text_color=MUTED,
            wraplength=480,
        ).pack(pady=(0, 18))

        ctk.CTkLabel(
            page, text="Güvenlik Sensörleri",
            font=ctk.CTkFont(size=17, weight="bold"), text_color=TEXT,
        ).pack(anchor="w", pady=(0, 10))

        sensor_frame = ctk.CTkFrame(page, fg_color="transparent")
        sensor_frame.pack(fill="x")
        for column in range(3):
            sensor_frame.grid_columnconfigure(column, weight=1, uniform="sensor")

        sensors = (
            ("GÜÇ", "Adaptör bağlantısı"),
            ("USB", "Cihaz değişimleri"),
            ("GİRİŞ", "Klavye ve fare"),
        )
        for column, (name, description) in enumerate(sensors):
            card = ctk.CTkFrame(
                sensor_frame, fg_color=CARD, corner_radius=12,
                border_width=1, border_color=BORDER,
            )
            card.grid(row=0, column=column, sticky="nsew", padx=5)
            ctk.CTkLabel(
                card, text=name, font=ctk.CTkFont(size=16, weight="bold"),
                text_color=PRIMARY,
            ).pack(pady=(15, 5))
            ctk.CTkLabel(
                card, text=description, font=ctk.CTkFont(size=11),
                text_color=MUTED,
            ).pack(pady=(0, 15))

        self.arm_button = ctk.CTkButton(
            page, text="Korumayı Etkinleştir", height=50,
            corner_radius=12, fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.on_arm,
        )
        self.arm_button.pack(fill="x", pady=(24, 8))

    def _build_settings_page(self):
        # Kartlar 600px pencereye sigmiyor; kaydirilabilir sayfa.
        page = ctk.CTkScrollableFrame(self.page_container, fg_color="transparent")
        self.pages["settings"] = page

        speaker_card = ctk.CTkFrame(
            page, fg_color=CARD, corner_radius=16,
            border_width=1, border_color=BORDER,
        )
        speaker_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            speaker_card, text="Alarm Hoparlörü",
            font=ctk.CTkFont(size=19, weight="bold"), text_color=TEXT,
        ).pack(anchor="w", padx=24, pady=(23, 7))
        ctk.CTkLabel(
            speaker_card,
            text="Siren için bilgisayarınızın dahili hoparlörünü seçin.",
            font=ctk.CTkFont(size=12), text_color=MUTED,
        ).pack(anchor="w", padx=24, pady=(0, 17))

        self.audio_button = ctk.CTkButton(
            speaker_card, text="Ses Çıkışını Ayarla",
            width=215, height=43,
            fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
            command=self.on_audio_settings,
        )
        self.audio_button.pack(anchor="w", padx=24, pady=(0, 24))

        pin_card = ctk.CTkFrame(
            page, fg_color=CARD, corner_radius=16,
            border_width=1, border_color=BORDER,
        )
        pin_card.pack(fill="x")
        ctk.CTkLabel(
            pin_card, text="PIN Güvenliği",
            font=ctk.CTkFont(size=19, weight="bold"), text_color=TEXT,
        ).pack(anchor="w", padx=24, pady=(24, 7))
        ctk.CTkLabel(
            pin_card,
            text="Mevcut PIN’inizi doğrulayarak yeni bir PIN belirleyin.",
            font=ctk.CTkFont(size=12), text_color=MUTED,
        ).pack(anchor="w", padx=24, pady=(0, 24))

        self.pin_change_button = ctk.CTkButton(
            pin_card, text="PIN Değiştir", width=215, height=43,
            fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
            command=self.on_pin_change,
            state="normal" if self.on_pin_change is not None else "disabled",
        )
        self.pin_change_button.pack(anchor="w", padx=24, pady=(0, 20))

        update_card = ctk.CTkFrame(
            page, fg_color=CARD, corner_radius=16,
            border_width=1, border_color=BORDER,
        )
        update_card.pack(fill="x", pady=(16, 0))
        ctk.CTkLabel(
            update_card, text="Güncellemeler",
            font=ctk.CTkFont(size=19, weight="bold"), text_color=TEXT,
        ).pack(anchor="w", padx=24, pady=(24, 7))
        ctk.CTkLabel(
            update_card, textvariable=self.update_status_var,
            font=ctk.CTkFont(size=12), text_color=MUTED,
        ).pack(anchor="w", padx=24, pady=(0, 17))

        buttons = ctk.CTkFrame(update_card, fg_color="transparent")
        buttons.pack(anchor="w", padx=24, pady=(0, 20))

        self.check_update_button = ctk.CTkButton(
            buttons, text="Kontrol Et", width=150, height=43,
            fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
            command=self.on_check_update,
            state="normal" if self.on_check_update is not None else "disabled",
        )
        self.check_update_button.pack(side="left", padx=(0, 10))

        self.install_update_button = ctk.CTkButton(
            buttons, text="Güncelle", width=150, height=43,
            fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
            command=self.on_install_update,
            state="disabled",
        )
        self.install_update_button.pack(side="left")

    def set_update_status(self, text):
        self.update_status_var.set(text)

    def set_update_available(self, release):
        self.install_update_button.configure(
            state="normal" if release is not None else "disabled"
        )
        if release is not None:
            self.update_badge.place(relx=1.0, x=-14, y=14, anchor="ne")
        else:
            self.update_badge.place_forget()

    def show_page(self, page_name):
        if page_name not in self.pages:
            raise ValueError(f"Bilinmeyen sayfa: {page_name}")

        for page in self.pages.values():
            page.pack_forget()
        self.pages[page_name].pack(fill="both", expand=True)
        self.current_page = page_name

        titles = {
            "home": ("Ana Sayfa", "Bilgisayarınızın güvenlik kontrol merkezi"),
            "settings": ("Ayarlar", "SentinelGuard yapılandırması"),
        }
        title, subtitle = titles[page_name]
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)

        for name, button in self.nav_buttons.items():
            button.configure(
                fg_color=ACTIVE_NAV if name == page_name else "transparent",
                text_color=TEXT if name == page_name else MUTED,
            )
