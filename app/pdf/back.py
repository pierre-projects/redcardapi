"""Back-side card rendering."""

from typing import List, Optional

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from ..layout import CardLayout
from .constants import BASE_BODY_SIZE, BASE_LEADING
from .fonts import get_font
from .guides import draw_text_line
from .wrapping import wrap_lines


def draw_back(
    pdf_canvas: canvas.Canvas,
    left: float,
    bottom: float,
    width: float,
    height: float,
    back_paragraphs: List[str],
    layout: CardLayout,
    rtl: bool = False,
    lang_code: Optional[str] = None,
) -> None:
    """Draw the back side of a card."""
    pad = 0.12 * inch * layout.font_scale + 0.06 * inch
    body_size = layout.get_scaled_font_size(BASE_BODY_SIZE)
    leading = layout.get_scaled_leading(BASE_LEADING)
    cursor_y = bottom + height - pad

    regular_font = get_font("en", bold=False)
    pdf_canvas.setFont(regular_font, body_size)

    for paragraph in back_paragraphs:
        paragraph = (paragraph or "").strip()
        if not paragraph:
            continue

        lines = wrap_lines(paragraph, regular_font, body_size, width - 2 * pad, rtl=rtl, lang_code=lang_code)
        for line in lines:
            if cursor_y < bottom + pad:
                return
            draw_text_line(pdf_canvas, line, left, cursor_y, width, pad, rtl=rtl)
            cursor_y -= leading

        cursor_y -= 4 * layout.font_scale
