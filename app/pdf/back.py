"""Back-side card rendering."""

from typing import List, Optional, Tuple

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from ..layout import CardLayout
from ..logging_config import get_logger
from .constants import (
    BASE_BODY_SIZE,
    BASE_LEADING,
    MIN_ABSOLUTE_FONT_SIZE,
    MAX_ABSOLUTE_FONT_SIZE,
)
from .fitting import find_best_fit_scale
from .fonts import get_font
from .guides import draw_text_line
from .wrapping import wrap_lines

logger = get_logger("pdf_renderer")


def _back_sizes_for_scale(scale: float) -> Tuple[int, int]:
    """Compute back typography values for a given scale."""
    body_size = max(MIN_ABSOLUTE_FONT_SIZE, min(MAX_ABSOLUTE_FONT_SIZE, int(BASE_BODY_SIZE * scale)))
    leading = max(8, int(BASE_LEADING * scale))
    return body_size, leading


def _measure_back_content(
    back_paragraphs: List[str],
    regular_font: str,
    body_size: int,
    leading: int,
    max_width: float,
    paragraph_gap: float,
) -> float:
    total_height = 0.0

    for paragraph in back_paragraphs:
        paragraph = (paragraph or "").strip()
        if not paragraph:
            continue

        lines = wrap_lines(paragraph, regular_font, body_size, max_width, rtl=False, lang_code="en")
        if lines:
            total_height += len(lines) * leading
            total_height += paragraph_gap

    return total_height


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
    regular_font = get_font("en", bold=False)

    def measure_at_scale(scale: float) -> float:
        body_size, leading = _back_sizes_for_scale(scale)
        pad = 0.12 * inch * scale + 0.06 * inch
        return _measure_back_content(
            back_paragraphs=back_paragraphs,
            regular_font=regular_font,
            body_size=body_size,
            leading=leading,
            max_width=max(1.0, width - 2 * pad),
            paragraph_gap=4 * scale,
        ) + (2 * pad)

    fit = find_best_fit_scale(
        base_scale=layout.font_scale,
        available_height=height,
        base_font_sizes=(BASE_BODY_SIZE,),
        measure_height=measure_at_scale,
    )

    optimal_scale = fit.scale
    pad = 0.12 * inch * optimal_scale + 0.06 * inch
    body_size, leading = _back_sizes_for_scale(optimal_scale)
    available_height = height - 2 * pad
    available_width = width - 2 * pad
    content_height = _measure_back_content(
        back_paragraphs=back_paragraphs,
        regular_font=regular_font,
        body_size=body_size,
        leading=leading,
        max_width=available_width,
        paragraph_gap=4 * optimal_scale,
    )
    fill_ratio = content_height / available_height if available_height > 0 else 0.0

    if abs(optimal_scale - layout.font_scale) / max(layout.font_scale, 1e-6) > 0.02:
        direction = "increased" if optimal_scale > layout.font_scale else "reduced"
        scale_percent = int((optimal_scale / max(layout.font_scale, 1e-6)) * 100)
        logger.info(
            f"Adaptive fit for back/en: {direction} to {scale_percent}% "
            f"(base: {fit.base_height:.1f}pt, fitted: {fit.fitted_height:.1f}pt, "
            f"available: {height:.1f}pt card, text_fill={fill_ratio:.2f})"
        )
    if not fit.fits:
        logger.warning(
            f"Back content overflow: text will be clipped "
            f"(fitted needs {fit.fitted_height:.1f}pt at min scale, available: {height:.1f}pt card)"
        )

    cursor_y = bottom + height - pad
    pdf_canvas.setFont(regular_font, body_size)

    for paragraph in back_paragraphs:
        paragraph = (paragraph or "").strip()
        if not paragraph:
            continue

        lines = wrap_lines(paragraph, regular_font, body_size, available_width, rtl=False, lang_code="en")
        for line in lines:
            if cursor_y < bottom + pad:
                return
            draw_text_line(pdf_canvas, line, left, cursor_y, width, pad, rtl=False)
            cursor_y -= leading

        cursor_y -= 4 * optimal_scale
