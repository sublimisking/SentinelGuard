
import customtkinter as ctk


BACKGROUND = "#0B1220"
CARD = "#172338"
BORDER = "#263750"
PRIMARY = "#2563EB"
PRIMARY_HOVER = "#1D4ED8"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
SUCCESS = "#22C55E"
DANGER = "#EF4444"


def configure_theme():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")


def center_window(window, width, height, parent=None):
    """Pencereyi ekranda veya gorunur ust pencerede ortala."""

    window.update_idletasks()

    if parent is not None and parent.winfo_viewable():
        x = (
            parent.winfo_rootx()
            + (parent.winfo_width() - width) // 2
        )
        y = (
            parent.winfo_rooty()
            + (parent.winfo_height() - height) // 2
        )
    else:
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 2

    window.geometry(
        f"{width}x{height}+{max(0, x)}+{max(0, y)}"
    )
