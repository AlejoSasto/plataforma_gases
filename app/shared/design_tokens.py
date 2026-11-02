"""Tokens de color para pruebas de contraste (espejo de tokens.css)."""

from __future__ import annotations

LIGHT = {
    "bg": "#EEF0EF",
    "surface": "#FFFFFF",
    "text": "#1A1E24",
    "text-2": "#4A525E",
    "accent": "#1C5A8E",
}

STATUS = {
    "normal": {"solid": "#1F8A5B", "soft": "#E5F3EC", "text": "#14603F"},
    "vigilar": {"solid": "#B97E00", "soft": "#FBF0D6", "text": "#6E4B00"},
    "actuar": {"solid": "#D2581A", "soft": "#FCE7DA", "text": "#93390A"},
    "evacuar": {"solid": "#C1262E", "soft": "#FAE3E4", "text": "#921A20"},
    "sin_datos": {"solid": "#7D8590", "soft": "#ECEEF0", "text": "#454C56"},
}

SALA = {
    "bg": "#0F1216",
    "surface": "#171B21",
    "text": "#E7EAEE",
    "accent": "#7FB2E5",
}


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.strip().lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r / 255.0, g / 255.0, b / 255.0


def _channel(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
