"""Card colors for color prints: hex parsing and a readable text color."""

import re

DEFAULT_CARD_COLOR = "B91C1C"
COLOR_PRESETS = ("B91C1C", "EA580C", "1D4ED8", "15803D", "111111")

RGB = tuple[float, float, float]
WHITE: RGB = (1.0, 1.0, 1.0)
BLACK: RGB = (0.0, 0.0, 0.0)

_HEX = re.compile(r"#?([0-9a-fA-F]{6})")


def normalize_hex(value: str) -> str | None:
    """"#b91c1c" -> "B91C1C"; None when the value is not a 6-digit hex color."""
    match = _HEX.fullmatch(value.strip())
    return match.group(1).upper() if match else None


def hex_to_rgb(value: str) -> RGB:
    """Expects a normalized hex color; channels are 0..1 as ReportLab wants."""
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _luminance(rgb: RGB) -> float:
    """WCAG relative luminance."""
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def text_color_for(background: RGB) -> RGB:
    """White or black, whichever has the higher contrast ratio on the background."""
    lum = _luminance(background)
    on_white = 1.05 / (lum + 0.05)
    on_black = (lum + 0.05) / 0.05
    return WHITE if on_white >= on_black else BLACK
