"""SentinelGuard ana penceresi: yalnizca gorunum ve kullanici eylemleri.

Güvenlik mantığı bu dosyada bulunmaz. Butonlar app.py'den gelen
callback'leri çağırır; uygulama durumu status_var üzerinden güncellenir.
"""

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from sentinelguard.core.camera_capture import make_png_base64

from sentinelguard.ui.theme import (
    BACKGROUND,
    CARD,
    BORDER,
    PRIMARY,
    PRIMARY_HOVER,
    TEXT,
    MUTED,
    SUCCESS,
    DANGER,
)

SIDEBAR = "#101B2D"
EVENT_BG = "#101B2D"
SUCCESS_HOVER = "#16A34A"
ACTIVE_NAV = "#1D3B62"


class MainWindow(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        on_arm,
        on_audio_settings,
        on_pin_change=None,
        on_get_events=None,
        on_list_photos=None,
        on_delete_photo=None,
        on_get_camera_enabled=None,
        on_set_camera_enabled=None,
        on_check_update=None,
        on_install_update=None,
    ):
        super().__init__(parent, fg_color=BACKGROUND, corner_radius=0)

        # Butonlar olusturulmadan once callback'leri sakla.
        self.on_arm = on_arm
        self.on_audio_settings = on_audio_settings
        self.on_pin_change = on_pin_change
        self.on_get_events = on_get_events or (lambda: [])
        self.on_list_photos = on_list_photos or (lambda: [])
        self.on_delete_photo = on_delete_photo
        self.on_get_camera_enabled = on_get_camera_enabled
        self.on_set_camera_enabled = on_set_camera_enabled
        # PhotoImage referanslari tutulmazsa Tk resmi siler.
        self._photo_refs = []
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

        for key, name in (
            ("home", "Ana Sayfa"),
            ("events", "Olay Geçmişi"),
            ("photos", "Fotoğraflar"),
            ("settings", "Ayarlar"),
        ):
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

        ctk.CTkLabel(
            sidebar,
            text="v0.1.1",
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
        self._build_events_page()
        self._build_photos_page()
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

    def _build_events_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["events"] = page

        toolbar = ctk.CTkFrame(page, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            toolbar, text="Son 10 olay",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT,
        ).pack(side="left")

        ctk.CTkButton(
            toolbar, text="Yenile", width=90, height=34,
            fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
            command=self.refresh_events,
        ).pack(side="right")

        self.events_list = ctk.CTkScrollableFrame(
            page, fg_color=CARD, corner_radius=14,
            border_width=1, border_color=BORDER,
        )
        self.events_list.pack(fill="both", expand=True)

        ctk.CTkLabel(
            page,
            text="Kayıtlar bu bilgisayarda saklanır. PIN değerleri kaydedilmez.",
            font=ctk.CTkFont(size=11), text_color=MUTED,
        ).pack(anchor="w", pady=(10, 0))

    def refresh_events(self):
        """Olay sayfasi acilinca ve Yenile'ye basilinca calisir."""
        self._photo_refs = []
        for widget in self.events_list.winfo_children():
            widget.destroy()

        try:
            records = self.on_get_events()
        except Exception as error:
            ctk.CTkLabel(
                self.events_list,
                text=f"Olay geçmişi okunamadı: {error}",
                text_color=DANGER, wraplength=470,
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
                self.events_list, fg_color=EVENT_BG, corner_radius=10
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
                header, text=timestamp,
                font=ctk.CTkFont(size=11), text_color=MUTED,
            ).pack(side="right")

            ctk.CTkLabel(
                item, text=event.message,
                font=ctk.CTkFont(size=13), text_color=TEXT,
                anchor="w", justify="left", wraplength=470,
            ).pack(fill="x", padx=14, pady=(0, 12))

            photo_path = getattr(event, "photo_path", None)
            if photo_path:
                self._add_photo_preview(item, photo_path)

    def _add_photo_preview(self, item, photo_path):
        """Olay satirina kucuk resim ekler; tiklaninca tam boy acar."""
        encoded = (
            make_png_base64(photo_path, 96) if Path(photo_path).is_file() else None
        )
        if encoded is None:
            ctk.CTkLabel(
                item, text="Fotoğraf silinmiş veya açılamıyor.",
                font=ctk.CTkFont(size=11), text_color=MUTED, anchor="w",
            ).pack(fill="x", padx=14, pady=(0, 12))
            return

        image = tk.PhotoImage(data=encoded)
        self._photo_refs.append(image)
        thumb = tk.Label(
            item, image=image, cursor="hand2", bd=0, bg=EVENT_BG,
        )
        thumb.pack(anchor="w", padx=14, pady=(0, 12))
        thumb.bind("<Button-1>", lambda _e, p=photo_path: self.open_photo(p))

    def open_photo(self, photo_path):
        encoded = make_png_base64(photo_path, 800)
        if encoded is None:
            return
        window = ctk.CTkToplevel(self)
        window.title("Alarm Fotoğrafı")
        image = tk.PhotoImage(data=encoded)
        label = tk.Label(window, image=image, bd=0)
        label.image = image  # referansi pencereye bagla
        label.pack()
        window.after(100, window.lift)

    def _build_photos_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pages["photos"] = page

        toolbar = ctk.CTkFrame(page, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            toolbar, text="Alarm fotoğrafları (en fazla 5)",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT,
        ).pack(side="left")

        ctk.CTkButton(
            toolbar, text="Yenile", width=90, height=34,
            fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
            command=self.refresh_photos,
        ).pack(side="right")

        self.photos_list = ctk.CTkScrollableFrame(
            page, fg_color=CARD, corner_radius=14,
            border_width=1, border_color=BORDER,
        )
        self.photos_list.pack(fill="both", expand=True)

        ctk.CTkLabel(
            page,
            text="Fotoğraflar yalnızca bu bilgisayarda saklanır.",
            font=ctk.CTkFont(size=11), text_color=MUTED,
        ).pack(anchor="w", pady=(10, 0))

    def refresh_photos(self):
        """Fotograflar sayfasi acilinca, Yenile'de ve silmeden sonra calisir."""
        self._photo_page_refs = []
        for widget in self.photos_list.winfo_children():
            widget.destroy()

        try:
            photos = list(self.on_list_photos())
        except Exception as error:
            ctk.CTkLabel(
                self.photos_list,
                text=f"Fotoğraflar okunamadı: {error}",
                text_color=DANGER, wraplength=470,
            ).pack(padx=12, pady=20)
            return

        if not photos:
            ctk.CTkLabel(
                self.photos_list,
                text="Henüz alarm fotoğrafı yok.",
                text_color=MUTED,
            ).pack(padx=12, pady=24)
            return

        for photo in photos:
            self._add_photo_card(photo)

    @staticmethod
    def _photo_time_text(photo):
        stem = Path(photo).stem[:19]
        try:
            return datetime.strptime(stem, "%Y-%m-%d_%H-%M-%S").strftime(
                "%d.%m.%Y  %H:%M:%S"
            )
        except ValueError:
            return Path(photo).name

    def _add_photo_card(self, photo):
        item = ctk.CTkFrame(
            self.photos_list, fg_color=EVENT_BG, corner_radius=10
        )
        item.pack(fill="x", padx=7, pady=5)

        encoded = make_png_base64(photo, 150)
        if encoded is not None:
            image = tk.PhotoImage(data=encoded)
            self._photo_page_refs.append(image)
            thumb = tk.Label(
                item, image=image, cursor="hand2", bd=0, bg=EVENT_BG
            )
            thumb.bind("<Button-1>", lambda _e, p=photo: self.open_photo(p))
        else:
            thumb = ctk.CTkLabel(
                item, text="Önizleme yok", text_color=MUTED, width=150
            )
        thumb.pack(side="left", padx=14, pady=12)

        info = ctk.CTkFrame(item, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=12)

        ctk.CTkLabel(
            info, text=self._photo_time_text(photo),
            font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT,
            anchor="w",
        ).pack(fill="x")

        buttons = ctk.CTkFrame(info, fg_color="transparent")
        buttons.pack(anchor="w", pady=(10, 0))

        ctk.CTkButton(
            buttons, text="Büyüt", width=90, height=32,
            fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
            command=lambda p=photo: self.open_photo(p),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            buttons, text="Sil", width=90, height=32,
            fg_color=DANGER, hover_color="#B91C1C",
            command=lambda p=photo: self.delete_photo(p),
        ).pack(side="left")

    def _confirm_delete(self):
        return messagebox.askyesno(
            "Fotoğrafı sil",
            "Bu fotoğraf kalıcı olarak silinsin mi?",
            parent=self,
        )

    def delete_photo(self, photo):
        if self.on_delete_photo is None or not self._confirm_delete():
            return
        try:
            self.on_delete_photo(photo)
        except Exception as error:
            messagebox.showerror(
                "Silinemedi", f"Fotoğraf silinemedi: {error}", parent=self
            )
        self.refresh_photos()

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

        camera_card = ctk.CTkFrame(
            page, fg_color=CARD, corner_radius=16,
            border_width=1, border_color=BORDER,
        )
        camera_card.pack(fill="x", pady=(16, 0))
        ctk.CTkLabel(
            camera_card, text="Alarm Fotoğrafı",
            font=ctk.CTkFont(size=19, weight="bold"), text_color=TEXT,
        ).pack(anchor="w", padx=24, pady=(24, 7))
        ctk.CTkLabel(
            camera_card,
            text=(
                "Alarm çaldığında kamerayla tek fotoğraf çekilir. "
                "En fazla 5 fotoğraf saklanır; fotoğraflar yalnızca bu "
                "bilgisayarda kalır."
            ),
            font=ctk.CTkFont(size=12), text_color=MUTED,
            wraplength=430, justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 17))

        self.camera_switch = ctk.CTkSwitch(
            camera_card, text="Alarmda kamera fotoğrafı çek",
            text_color=TEXT, command=self._on_camera_switch,
            state="normal" if self.on_set_camera_enabled else "disabled",
        )
        self.camera_switch.pack(anchor="w", padx=24, pady=(0, 24))
        try:
            if self.on_get_camera_enabled is None or self.on_get_camera_enabled():
                self.camera_switch.select()
        except Exception:
            self.camera_switch.select()

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

    def _on_camera_switch(self):
        if self.on_set_camera_enabled is None:
            return
        try:
            self.on_set_camera_enabled(bool(self.camera_switch.get()))
        except Exception as error:
            print(f"Kamera ayarı kaydedilemedi: {error}")
            # Kayit basarisizsa anahtar gercek durumu gostersin.
            if self.on_get_camera_enabled is not None:
                if self.on_get_camera_enabled():
                    self.camera_switch.select()
                else:
                    self.camera_switch.deselect()

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

        if page_name == "events":
            self.refresh_events()
        elif page_name == "photos":
            self.refresh_photos()

        titles = {
            "home": ("Ana Sayfa", "Bilgisayarınızın güvenlik kontrol merkezi"),
            "events": ("Olay Geçmişi", "Kaydedilen güvenlik ve alarm olayları"),
            "photos": ("Fotoğraflar", "Alarm anında çekilen kamera fotoğrafları"),
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
