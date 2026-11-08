"""SentinelGuard'in ana grafik arayuzu.

Bu sınıf güvenlik işlemlerini yönetmez; buton olaylarini uygulama
kontrolcusune iletir ve kendisine verilen durum metnini gosterir.
"""

from datetime import datetime

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
)


SIDEBAR = "#101B2D"
ACTIVE_NAV = "#1D3B62"
SENSOR_BG = "#101B2D"


class MainWindow(ctk.CTkFrame):
    """Ana Sayfa ve Ayarlar sayfalarini barindiran gorunum."""

    def __init__(self, parent, on_arm, on_audio_settings, on_get_events=None):
        super().__init__(parent, fg_color=BACKGROUND, corner_radius=0)

        # Önceki sürümde eksik olan kısım: callback'ler, butonlar
        # oluşturulmadan ÖNCE saklanmalıdır.
        self.on_arm = on_arm
        self.on_audio_settings = on_audio_settings
        self.on_get_events = on_get_events or (lambda: [])

        self.status_var = ctk.StringVar(value="Koruma kapalı.")
        self.pages = {}
        self.nav_buttons = {}
        self.current_page = None

        self.pack(fill="both", expand=True)
        self._build_sidebar()
        self._build_content()
        self.show_page("home")

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self,
            width=215,
            fg_color=SIDEBAR,
            corner_radius=0,
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="◈  SentinelGuard",
            font=ctk.CTkFont(size=21, weight="bold"),
            text_color=TEXT,
        ).pack(pady=(34, 5))

        ctk.CTkLabel(
            self.sidebar,
            text="SECURITY CENTER",
            font=ctk.CTkFont(size=10),
            text_color=MUTED,
        ).pack(pady=(0, 35))

        for page_name, title in (
            ("home", "Ana Sayfa"),
            ("events", "Olay Geçmişi"),
            ("settings", "Ayarlar"),
        ):
            button = ctk.CTkButton(
                self.sidebar,
                text=title,
                width=185,
                height=43,
                corner_radius=10,
                anchor="w",
                fg_color="transparent",
                hover_color=ACTIVE_NAV,
                text_color=MUTED,
                command=lambda name=page_name: self.show_page(name),
            )
            button.pack(padx=15, pady=5)
            self.nav_buttons[page_name] = button

        ctk.CTkLabel(
            self.sidebar,
            text="v0.1.0-beta  •  Test sürümü",
            font=ctk.CTkFont(size=11),
            text_color=MUTED,
        ).pack(side="bottom", pady=24)

    def _build_content(self):
        content = ctk.CTkFrame(
            self,
            fg_color=BACKGROUND,
            corner_radius=0,
        )
        content.pack(side="left", fill="both", expand=True)

        self.page_title = ctk.CTkLabel(
            content,
            text="",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=TEXT,
        )
        self.page_title.pack(anchor="w", padx=32, pady=(30, 4))

        self.page_subtitle = ctk.CTkLabel(
            content,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=MUTED,
        )
        self.page_subtitle.pack(anchor="w", padx=32, pady=(0, 20))

        self.page_container = ctk.CTkFrame(
            content,
            fg_color="transparent",
        )
        self.page_container.pack(
            fill="both",
            expand=True,
            padx=32,
            pady=(0, 20),
        )

        self._build_home_page()
        self._build_events_page()
        self._build_settings_page()

    def _build_home_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["home"] = page

        hero = ctk.CTkFrame(
            page,
            fg_color=CARD,
            corner_radius=16,
            border_width=1,
            border_color=BORDER,
        )
        hero.pack(fill="x", pady=(0, 18))

        ctk.CTkLabel(
            hero,
            text="◈",
            font=ctk.CTkFont(size=44, weight="bold"),
            text_color=PRIMARY,
        ).pack(pady=(12, 0))

        ctk.CTkLabel(
            hero,
            text="Güvenlik Durumu",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT,
        ).pack(pady=(0, 7))

        ctk.CTkLabel(
            hero,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=14),
            text_color=MUTED,
            wraplength=510,
        ).pack(pady=(0, 19))

        ctk.CTkLabel(
            page,
            text="Güvenlik Sensörleri",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=TEXT,
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
                sensor_frame,
                fg_color=SENSOR_BG,
                corner_radius=12,
                border_width=1,
                border_color=BORDER,
            )
            card.grid(row=0, column=column, sticky="nsew", padx=5)

            ctk.CTkLabel(
                card,
                text=name,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=PRIMARY,
            ).pack(pady=(16, 5))
            ctk.CTkLabel(
                card,
                text=description,
                font=ctk.CTkFont(size=11),
                text_color=MUTED,
            ).pack(pady=(0, 16))

        self.arm_button = ctk.CTkButton(
            page,
            text="Korumayı Etkinleştir",
            height=50,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.on_arm,
        )
        self.arm_button.pack(fill="x", pady=(24, 8))

    def _build_events_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["events"] = page

        toolbar = ctk.CTkFrame(page, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            toolbar,
            text="Son 100 olay",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT,
        ).pack(side="left")

        ctk.CTkButton(
            toolbar,
            text="Yenile",
            width=90,
            height=34,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            command=self.refresh_events,
        ).pack(side="right")

        self.events_list = ctk.CTkScrollableFrame(
            page,
            fg_color=CARD,
            corner_radius=14,
            border_width=1,
            border_color=BORDER,
        )
        self.events_list.pack(fill="both", expand=True)

        ctk.CTkLabel(
            page,
            text="Kayıtlar bu bilgisayarda saklanır. PIN değerleri kaydedilmez.",
            font=ctk.CTkFont(size=11),
            text_color=MUTED,
        ).pack(anchor="w", pady=(10, 0))

    def refresh_events(self):
        """Olaylar sayfası açıldığında ve Yenile tıklandığında çağrılır."""
        for widget in self.events_list.winfo_children():
            widget.destroy()

        try:
            records = self.on_get_events()
        except Exception as error:
            ctk.CTkLabel(
                self.events_list,
                text=f"Olay geçmişi okunamadı: {error}",
                text_color=DANGER,
                wraplength=470,
            ).pack(padx=12, pady=20)
            return

        if not records:
            ctk.CTkLabel(
                self.events_list,
                text="Henüz kaydedilmiş güvenlik olayı yok.",
                text_color=MUTED,
            ).pack(padx=12, pady=24)
            return

        category_names = {
            "security": "GÜVENLİK",
            "alarm": "ALARM",
            "auth": "PIN",
            "system": "SİSTEM",
        }
        category_colors = {
            "security": PRIMARY,
            "alarm": DANGER,
            "auth": "#38BDF8",
            "system": MUTED,
        }

        for event in records:
            item = ctk.CTkFrame(
                self.events_list,
                fg_color=SENSOR_BG,
                corner_radius=10,
            )
            item.pack(fill="x", padx=7, pady=5)

            header = ctk.CTkFrame(item, fg_color="transparent")
            header.pack(fill="x", padx=14, pady=(11, 3))

            ctk.CTkLabel(
                header,
                text=category_names.get(event.category, "OLAY"),
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=category_colors.get(event.category, MUTED),
            ).pack(side="left")

            try:
                timestamp = datetime.fromisoformat(event.occurred_at).strftime(
                    "%d.%m.%Y  %H:%M:%S"
                )
            except (ValueError, TypeError):
                timestamp = str(event.occurred_at)

            ctk.CTkLabel(
                header,
                text=timestamp,
                font=ctk.CTkFont(size=11),
                text_color=MUTED,
            ).pack(side="right")

            ctk.CTkLabel(
                item,
                text=event.message,
                font=ctk.CTkFont(size=13),
                text_color=TEXT,
                anchor="w",
                justify="left",
                wraplength=470,
            ).pack(fill="x", padx=14, pady=(0, 12))

    def _build_settings_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["settings"] = page

        speaker_card = ctk.CTkFrame(
            page,
            fg_color=CARD,
            corner_radius=16,
            border_width=1,
            border_color=BORDER,
        )
        speaker_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            speaker_card,
            text="Alarm Hoparlörü",
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color=TEXT,
        ).pack(anchor="w", padx=24, pady=(23, 7))

        ctk.CTkLabel(
            speaker_card,
            text="Siren için bilgisayarınızın dahili hoparlörünü seçin.",
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
        ).pack(anchor="w", padx=24, pady=(0, 17))

        self.audio_button = ctk.CTkButton(
            speaker_card,
            text="Ses Çıkışını Ayarla",
            width=215,
            height=43,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            command=self.on_audio_settings,
        )
        self.audio_button.pack(anchor="w", padx=24, pady=(0, 24))

        pin_card = ctk.CTkFrame(
            page,
            fg_color=CARD,
            corner_radius=16,
            border_width=1,
            border_color=BORDER,
        )
        pin_card.pack(fill="x")

        ctk.CTkLabel(
            pin_card,
            text="PIN Güvenliği",
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color=TEXT,
        ).pack(anchor="w", padx=24, pady=(24, 7))

        ctk.CTkLabel(
            pin_card,
            text="PIN değiştirme ekranı sonraki sürümde eklenecek.",
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
        ).pack(anchor="w", padx=24, pady=(0, 24))

    def show_page(self, page_name):
        if page_name not in self.pages:
            raise ValueError("Bilinmeyen sayfa.")

        for page in self.pages.values():
            page.pack_forget()
        self.pages[page_name].pack(fill="both", expand=True)
        self.current_page = page_name
        if page_name == "events":
            self.refresh_events()

        titles = {
            "home": ("Ana Sayfa", "Bilgisayarınızın güvenlik kontrol merkezi"),
            "events": ("Olay Geçmişi", "Kaydedilen güvenlik ve alarm olayları"),
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
