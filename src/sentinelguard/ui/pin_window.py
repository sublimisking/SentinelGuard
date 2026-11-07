import math
import tkinter as tk
import customtkinter as ctk

from sentinelguard.core.pin_manager import PinStorageError
from sentinelguard.ui.theme import (
    BACKGROUND, CARD, BORDER, PRIMARY,
    PRIMARY_HOVER, TEXT, MUTED, DANGER
)


def get_pin_status_text(security_manager):

    alarm = getattr(
        security_manager,
        "alarm_manager",
        None
    )

    if getattr(alarm, "alarm_active", False):
        return "SIREN AKTIF"

    if security_manager.pin_deadline is None:
        return "SIREN AKTIF"

    if security_manager.pin_timeout_triggered:
        return "SIREN AKTIF"

    remaining = (
        security_manager.pin_deadline
        - security_manager.clock()
    )

    if remaining <= 0:
        return "SIREN AKTIF"

    return f"00:{math.ceil(remaining):02d}"


class PinWindow:

    def __init__(
        self,
        root,
        security_manager,
        on_disarmed=None
    ):
        self.security_manager = security_manager
        self.on_disarmed = on_disarmed

        self.is_visible = False
        self._after_id = None

        self.window = ctk.CTkToplevel(root)
        self.window.withdraw()

        self.window.title("SentinelGuard | Güvenlik")
        self.window.configure(fg_color=BACKGROUND)
        self.window.attributes("-fullscreen", True)
        self.window.attributes("-topmost", True)

        self.window.protocol(
            "WM_DELETE_WINDOW",
            lambda: None
        )

        self.status_var = ctk.StringVar(value="00:10")
        self.feedback_var = ctk.StringVar(value="")

        panel = ctk.CTkFrame(
            self.window,
            width=500,
            height=470,
            fg_color=CARD,
            border_width=1,
            border_color=BORDER,
            corner_radius=20
        )

        panel.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )
        panel.pack_propagate(False)

        ctk.CTkLabel(
            panel,
            text="◈  SentinelGuard",
            font=ctk.CTkFont(size=27, weight="bold"),
            text_color=TEXT
        ).pack(pady=(35, 12))

        ctk.CTkLabel(
            panel,
            text="Güvenlik doğrulaması gerekiyor",
            text_color=MUTED
        ).pack(pady=6)

        ctk.CTkLabel(
            panel,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=48, weight="bold"),
            text_color=DANGER
        ).pack(pady=(20, 18))

        self.pin_entry = ctk.CTkEntry(
            panel,
            width=340,
            height=48,
            show="*",
            placeholder_text="PIN girin",
            justify="center",
            corner_radius=10,
            border_color=BORDER,
            font=ctk.CTkFont(size=20)
        )
        self.pin_entry.pack(pady=8)

        self.pin_entry.bind(
            "<Return>",
            self._submit_pin
        )

        ctk.CTkButton(
            panel,
            text="Kilidi Aç",
            command=self._submit_pin,
            width=340,
            height=48,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            corner_radius=10
        ).pack(pady=14)

        ctk.CTkLabel(
            panel,
            textvariable=self.feedback_var,
            text_color=DANGER,
            wraplength=350
        ).pack(pady=8)

    def show(self):

        if not self.security_manager.is_armed:
            return

        self.is_visible = True

        self.feedback_var.set("")
        self.pin_entry.delete(0, tk.END)

        self.window.deiconify()
        self.window.lift()
        self.window.after(
            50,
            self.pin_entry.focus_force
        )

        if self._after_id is None:
            self._refresh()

    def _refresh(self):

        self._after_id = None

        if not self.is_visible:
            return

        if not self.security_manager.is_armed:
            self.hide()
            return

        self.security_manager.check_pin_timeout()

        self.status_var.set(
            get_pin_status_text(self.security_manager)
        )

        self._after_id = self.window.after(
            100,
            self._refresh
        )

    def _submit_pin(self, event=None):

        pin = self.pin_entry.get()
        self.pin_entry.delete(0, tk.END)

        try:
            accepted = self.security_manager.submit_pin(pin)

        except PinStorageError:
            self.feedback_var.set(
                "PIN kaydı okunamadı. Koruma devam ediyor."
            )
            return

        if accepted:
            self.hide()

            if self.on_disarmed is not None:
                self.on_disarmed()

        else:
            self.feedback_var.set("Yanlış PIN.")

    def hide(self):

        self.is_visible = False

        if self._after_id is not None:
            self.window.after_cancel(self._after_id)
            self._after_id = None

        self.window.withdraw()

    def destroy(self):

        self.hide()
        self.window.destroy()
