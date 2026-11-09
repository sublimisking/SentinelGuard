"""Mevcut PIN dogrulanarak yeni PIN belirlenen ayarlar penceresi."""
import customtkinter as ctk

from sentinelguard.ui.theme import (
    BACKGROUND, CARD, BORDER, PRIMARY, PRIMARY_HOVER,
    TEXT, MUTED, DANGER, center_window,
)


class PinChangeWindow(ctk.CTkToplevel):
    def __init__(self, parent, on_change):
        super().__init__(parent)
        self.on_change = on_change
        self._busy = False
        self._activate_id = None
        self.withdraw()
        self.title("SentinelGuard | PIN Değiştir")
        self.configure(fg_color=BACKGROUND)
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        center_window(self, 500, 560, parent)

        panel = ctk.CTkFrame(self, fg_color=CARD, corner_radius=18,
                            border_width=1, border_color=BORDER)
        panel.pack(fill="both", expand=True, padx=24, pady=24)
        ctk.CTkLabel(panel, text="PIN Değiştir", text_color=TEXT,
                     font=ctk.CTkFont(size=23, weight="bold")).pack(pady=(24, 8))
        ctk.CTkLabel(panel, text="Yeni PIN 6-12 haneli ve yalnızca rakamlardan oluşmalı.",
                     text_color=MUTED, wraplength=380).pack(pady=(0, 14))
        self.old_entry = self._entry(panel, "Mevcut PIN")
        self.new_entry = self._entry(panel, "Yeni PIN")
        self.confirm_entry = self._entry(panel, "Yeni PIN (tekrar)")
        self.feedback = ctk.CTkLabel(panel, text="", text_color=DANGER,
                                     wraplength=370)
        self.feedback.pack(padx=20, pady=10)
        self.save_button = ctk.CTkButton(
            panel, text="PIN'i Değiştir", height=42, width=350,
            fg_color=PRIMARY, hover_color=PRIMARY_HOVER, command=self.submit)
        self.save_button.pack(pady=(0, 10))
        ctk.CTkButton(panel, text="İptal", height=36, width=350,
                     fg_color=BACKGROUND, hover_color=BORDER,
                     command=self.destroy).pack(pady=(0, 16))
        self.confirm_entry.bind("<Return>", lambda event: self.submit())
        self.bind("<Escape>", lambda event: self.destroy())
        self.deiconify()
        self._activate_id = self.after(100, self._activate)

    def _entry(self, panel, label):
        ctk.CTkLabel(panel, text=label, text_color=TEXT).pack(anchor="w", padx=40)
        row = ctk.CTkFrame(panel, fg_color="transparent")
        row.pack(pady=(0, 8))
        entry = ctk.CTkEntry(row, width=270, height=40, show="*",
                             border_color=BORDER)
        entry.pack(side="left", padx=(0, 8))
        show_button = ctk.CTkButton(
            row, text="Göster", width=72, height=40,
            fg_color=BACKGROUND, hover_color=BORDER,
            command=lambda: self._toggle_visibility(entry, show_button),
        )
        show_button.pack(side="left")
        return entry

    def _toggle_visibility(self, entry, button):
        visible = bool(entry.cget("show"))
        entry.configure(show="" if visible else "*")
        button.configure(text="Gizle" if visible else "Göster")

    def _activate(self):
        self._activate_id = None
        self.lift()
        self.grab_set()
        self.old_entry.focus_set()

    def submit(self):
        if self._busy:
            return
        old_pin = self.old_entry.get()
        new_pin = self.new_entry.get()
        if new_pin != self.confirm_entry.get():
            self.feedback.configure(text="Yeni PIN'ler eşleşmiyor.")
            return
        self._busy = True
        self.save_button.configure(state="disabled")
        try:
            changed = self.on_change(old_pin, new_pin)
        except (ValueError, RuntimeError, OSError) as error:
            self.feedback.configure(text=str(error))
        else:
            if changed:
                self.destroy()
                return
            self.feedback.configure(text="Mevcut PIN yanlış.")
            self.old_entry.delete(0, "end")
            self.old_entry.focus_set()
        finally:
            self._busy = False
            if self.winfo_exists():
                self.save_button.configure(state="normal")

    def destroy(self):
        if self._activate_id is not None:
            self.after_cancel(self._activate_id)
            self._activate_id = None
        super().destroy()
