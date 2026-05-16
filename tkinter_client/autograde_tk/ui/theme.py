from __future__ import annotations

from dataclasses import dataclass
import tkinter.font as tkfont
import ttkbootstrap as ttk


@dataclass(frozen=True)
class UiTheme:
    base: tuple
    base_bold: tuple
    title: tuple
    small: tuple
    mono: tuple
    log_bg: str
    log_fg: str
    text_bg: str
    text_fg: str


DEFAULT_THEME = UiTheme(
    base=("Bahnschrift", 10),
    base_bold=("Bahnschrift", 10, "bold"),
    title=("Bahnschrift", 24, "bold"),
    small=("Bahnschrift", 9),
    mono=("Cascadia Mono", 10),
    log_bg="#0f172a",
    log_fg="#a7f3d0",
    text_bg="#f8fafc",
    text_fg="#0f172a",
)


def _pick_font(root: ttk.Window, preferred: list[str], fallback: str) -> str:
    available = set(tkfont.families(root))
    for name in preferred:
        if name in available:
            return name
    return fallback


def _color(style: ttk.Style, name: str, fallback: str) -> str:
    return getattr(style.colors, name, fallback)


def apply_theme(root: ttk.Window) -> UiTheme:
    style = ttk.Style()
    base_name = _pick_font(
        root,
        ["Bahnschrift", "Segoe UI Variable", "Segoe UI", "Helvetica Neue", "Helvetica"],
        "Segoe UI",
    )
    mono_name = _pick_font(
        root,
        ["Cascadia Mono", "JetBrains Mono", "Consolas", "Courier New"],
        "Consolas",
    )

    bg_color = _color(style, "bg", "#f4f6fb")
    card_bg = _color(style, "light", "#ffffff")
    muted = _color(style, "secondary", "#6b7280")

    theme = UiTheme(
        base=(base_name, 10),
        base_bold=(base_name, 10, "bold"),
        title=(base_name, 24, "bold"),
        small=(base_name, 9),
        mono=(mono_name, 10),
        log_bg="#0f172a",
        log_fg="#a7f3d0",
        text_bg="#f8fafc",
        text_fg="#0f172a",
    )

    style.configure(".", font=theme.base)
    style.configure("TButton", font=theme.base_bold, padding=(14, 7))
    style.configure("TNotebook.Tab", font=theme.base_bold, padding=(16, 8))
    style.configure("TLabelframe.Label", font=theme.base_bold)
    style.configure("TEntry", padding=(10, 6))
    style.configure("TCombobox", padding=(10, 6))
    style.configure("TSpinbox", padding=(10, 6))
    style.configure("TMenubutton", padding=(10, 6))
    style.configure("Treeview", font=theme.base, rowheight=26)
    style.configure("Treeview.Heading", font=theme.base_bold)

    style.configure("Card.TFrame", background=card_bg)
    style.configure("Card.TLabelframe", background=card_bg)
    style.configure("Card.TLabelframe.Label", background=card_bg, font=theme.base_bold)
    style.configure("Muted.TLabel", foreground=muted, font=theme.small)

    root.configure(background=bg_color)
    root.ui_theme = theme
    return theme


def get_theme(widget) -> UiTheme:
    root = widget.winfo_toplevel()
    return getattr(root, "ui_theme", DEFAULT_THEME)
