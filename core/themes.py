"""
Theme system and color utilities for the trading terminal.
Provides dark/light themes and brand colors with helper functions.
"""

import colorsys

# Design constants
BASE_RADIUS = 12
BASE_SPACING = 12
TOUCH_TARGET = 44

THEMES = {
    "dark": {
        "window_bg": "#0a0a0a",
        "panel_bg": "#0a0a0a",
        "surface": "#0a0a0a",
        "surface_alt": "#141414",
        "border": "#ffffff",
        "text": "#ffffff",
        "muted": "#9ca3af",
        "accent": "#ffffff",
        "accent_hover": "#1f1f1f",
        "button_text": "#000000",
        "button_hover_text": "#ffffff",
        "input_bg": "#0a0a0a",
        "tab_bg": "#1a1a1a",
        "tab_text": "#ffffff",
        "chart_theme": "dark",
        "chart_bg": "#0a0a0a",
        "chart_toolbar": "#0a0a0a",
        "divider": "#2a2a2a"
    },
    "light": {
        "window_bg": "#ffffff",
        "panel_bg": "#ffffff",
        "surface": "#ffffff",
        "surface_alt": "#f9fafb",
        "border": "#000000",
        "text": "#000000",
        "muted": "#6b7280",
        "accent": "#000000",
        "accent_hover": "#f3f4f6",
        "button_text": "#ffffff",
        "button_hover_text": "#000000",
        "input_bg": "#ffffff",
        "tab_bg": "#f5f5f5",
        "tab_text": "#000000",
        "chart_theme": "light",
        "chart_bg": "#ffffff",
        "chart_toolbar": "#ffffff",
        "divider": "#e5e7eb"
    }
}

BRAND_COLORS = {
    "NVDA": "#76b900",
    "AAPL": "#a2aaad",
    "TSLA": "#e82127",
    "MSFT": "#00a4ef",
    "AMZN": "#ff9900",
    "META": "#0a66ff",
    "GOOG": "#1a73e8",
    "NFLX": "#e50914",
    "SPY": "#1159a4",
    "QQQ": "#5c6bc0",
    "AMD": "#ff6f00",
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def mix_colors(color_a: str, color_b: str, ratio: float) -> str:
    r1, g1, b1 = hex_to_rgb(color_a)
    r2, g2, b2 = hex_to_rgb(color_b)
    r = int(r1 * (1 - ratio) + r2 * ratio)
    g = int(g1 * (1 - ratio) + g2 * ratio)
    b = int(b1 * (1 - ratio) + b2 * ratio)
    return rgb_to_hex((r, g, b))


def soften_color(color: str, amount: float = 0.4) -> str:
    return mix_colors(color, "#ffffff", amount)


def darken_color(color: str, amount: float = 0.15) -> str:
    return mix_colors(color, "#000000", amount)


def hsv_to_hex(h: float, s: float, v: float) -> str:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def ticker_hash_color(ticker: str) -> str:
    if not ticker:
        return "#888888"
    ticker = ticker.upper()
    seed = 0
    for ch in ticker:
        seed = (seed * 31 + ord(ch)) % 360
    hue = seed / 360.0
    saturation = 0.35
    value = 0.78
    return hsv_to_hex(hue, saturation, value)


def ideal_text_color(hex_color: str) -> str:
    if not hex_color:
        return "#000000"
    r, g, b = hex_to_rgb(hex_color)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    return "#000000" if luminance > 150 else "#ffffff"
