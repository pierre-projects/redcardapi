"""Complex-script shaping with HarfBuzz.

Brahmic and Southeast Asian scripts (Devanagari, Bengali, Tamil, Gurmukhi,
Thai, Lao, Khmer, Myanmar) need shaping: conjuncts, reordered vowel signs
and stacked consonants. Drawn unshaped, ReportLab prints the raw code points
and words come out wrong (e.g. "अधिकार" renders as "अधकिार"). Arabic-script
text needs it for joining letters, including Pashto/Urdu letters that
table-based reshapers do not know (ټ, ښ, ځ, ړ).

ReportLab only shapes in drawString when its separate rlbidi package is
installed, so we shape ourselves: shapeStr() returns a ShapedStr whose glyph
data drawString uses as-is. Widths must come from the shaped glyphs too, or
line wrapping is computed for text of a different length than is printed.
"""

from functools import lru_cache

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import ShapedStr, shapeStr

_COMPLEX_RANGES = (
    (0x0600, 0x06FF),  # Arabic (incl. Farsi, Pashto, Urdu letters)
    (0x0750, 0x077F),  # Arabic Supplement
    (0x08A0, 0x08FF),  # Arabic Extended-A
    (0x0900, 0x0DFF),  # Devanagari … Sinhala
    (0x0E00, 0x0EFF),  # Thai, Lao
    (0x1000, 0x109F),  # Myanmar
    (0x1780, 0x17FF),  # Khmer
    (0x19E0, 0x19FF),  # Khmer symbols
    (0xA9E0, 0xA9FF),  # Myanmar Extended-B
    (0xAA60, 0xAA7F),  # Myanmar Extended-A
)


def needs_shaping(text: str) -> bool:
    return any(lo <= ord(ch) <= hi for ch in text for lo, hi in _COMPLEX_RANGES)


@lru_cache(maxsize=8192)
def _shaped(text: str, font_name: str, font_size: float) -> ShapedStr:
    return shapeStr(text, font_name, font_size)


def shape(text: str, font_name: str, font_size: float) -> str | ShapedStr:
    """Text ready for canvas.drawString."""
    if text and needs_shaping(text) and pdfmetrics.getFont(font_name).shapable:
        return _shaped(text, font_name, font_size)
    return text


def text_width(text: str, font_name: str, font_size: float) -> float:
    shaped = shape(text, font_name, font_size)
    if isinstance(shaped, ShapedStr):
        return sum(g.x_advance for g in shaped.__shapeData__) * font_size / 1000
    return pdfmetrics.stringWidth(text, font_name, font_size)
