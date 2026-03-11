"""Front-side card rendering and adaptive scaling."""

from typing import Dict, Any, Optional, Tuple

from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from ..layout import CardLayout
from ..logging_config import get_logger
from .constants import (
    BASE_TITLE_SIZE,
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


def _measure_front_content(
    front_content: Dict[str, Any],
    bold_font: str,
    regular_font: str,
    title_size: int,
    body_size: int,
    leading: int,
    max_width: float,
    bullet_indent: float,
    rtl: bool = False,
    lang_code: Optional[str] = None,
) -> float:
    total_height = 0.0

    title = front_content.get("header") or front_content.get("title") or ""
    if title:
        title_lines = wrap_lines(title, bold_font, title_size, max_width, rtl=rtl, lang_code=lang_code)
        total_height += len(title_lines) * leading
        total_height += 4

    bullets = front_content.get("bullets") or front_content.get("points") or []
    for bullet_item in bullets:
        if isinstance(bullet_item, dict):
            bullet_text = (bullet_item.get("text") or "").strip()
        else:
            bullet_text = str(bullet_item).strip()

        if not bullet_text:
            continue

        bullet_lines = wrap_lines(
            bullet_text,
            regular_font,
            body_size,
            max_width - bullet_indent,
            rtl=rtl,
            lang_code=lang_code,
        )
        if bullet_lines:
            total_height += len(bullet_lines) * leading
            total_height += 2

    return total_height


def _front_sizes_for_scale(scale: float) -> Tuple[int, int, int, float]:
    """Compute front typography values for a given scale."""
    title_size = max(MIN_ABSOLUTE_FONT_SIZE, min(MAX_ABSOLUTE_FONT_SIZE, int(BASE_TITLE_SIZE * scale)))
    body_size = max(MIN_ABSOLUTE_FONT_SIZE, min(MAX_ABSOLUTE_FONT_SIZE, int(BASE_BODY_SIZE * scale)))
    leading = max(8, int(BASE_LEADING * scale))
    bullet_indent = 8 * scale
    return title_size, body_size, leading, bullet_indent


def _fit_front_scale(
    front_content: Dict[str, Any],
    card_height: float,
    card_width: float,
    base_scale: float,
    bold_font: str,
    regular_font: str,
    rtl: bool = False,
    lang_code: Optional[str] = None,
) -> Tuple[float, bool, float, float]:
    def measure_at_scale(scale: float) -> float:
        title_size, body_size, leading, bullet_indent = _front_sizes_for_scale(scale)
        pad = 0.12 * inch * scale + 0.06 * inch
        max_width = max(1.0, card_width - 2 * pad)
        return _measure_front_content(
            front_content=front_content,
            bold_font=bold_font,
            regular_font=regular_font,
            title_size=title_size,
            body_size=body_size,
            leading=leading,
            max_width=max_width,
            bullet_indent=bullet_indent,
            rtl=rtl,
            lang_code=lang_code,
        ) + (2 * pad)

    fit = find_best_fit_scale(
        base_scale=base_scale,
        available_height=card_height,
        base_font_sizes=(BASE_TITLE_SIZE, BASE_BODY_SIZE),
        measure_height=measure_at_scale,
    )
    return fit.scale, fit.fits, fit.base_height, fit.fitted_height


def draw_front(
    pdf_canvas: canvas.Canvas,
    left: float,
    bottom: float,
    width: float,
    height: float,
    front_content: Dict[str, Any],
    layout: CardLayout,
    rtl: bool = False,
    lang_code: Optional[str] = None,
) -> None:
    """Draw the front side of a card (header + bullets)."""
    bold_font = get_font(lang_code, bold=True)
    regular_font = get_font(lang_code, bold=False)

    optimal_scale, fits, base_height, fitted_height = _fit_front_scale(
        front_content=front_content,
        card_height=height,
        card_width=width,
        base_scale=layout.font_scale,
        bold_font=bold_font,
        regular_font=regular_font,
        rtl=rtl,
        lang_code=lang_code,
    )

    pad = 0.12 * inch * optimal_scale + 0.06 * inch
    available_height = height - 2 * pad
    available_width = width - 2 * pad
    title_size, body_size, leading, bullet_indent = _front_sizes_for_scale(optimal_scale)
    content_height = _measure_front_content(
        front_content=front_content,
        bold_font=bold_font,
        regular_font=regular_font,
        title_size=title_size,
        body_size=body_size,
        leading=leading,
        max_width=available_width,
        bullet_indent=bullet_indent,
        rtl=rtl,
        lang_code=lang_code,
    )
    fill_ratio = content_height / available_height if available_height > 0 else 0.0

    if abs(optimal_scale - layout.font_scale) / max(layout.font_scale, 1e-6) > 0.02:
        direction = "increased" if optimal_scale > layout.font_scale else "reduced"
        scale_percent = int((optimal_scale / max(layout.font_scale, 1e-6)) * 100)
        logger.info(
            f"Adaptive fit for {lang_code}: {direction} to {scale_percent}% "
            f"(base: {base_height:.1f}pt, fitted: {fitted_height:.1f}pt, "
            f"available: {height:.1f}pt card, text_fill={fill_ratio:.2f})"
        )
    else:
        logger.debug(
            f"Adaptive fit for {lang_code}: unchanged "
            f"(base: {base_height:.1f}pt, fitted: {fitted_height:.1f}pt, "
            f"available: {height:.1f}pt card, text_fill={fill_ratio:.2f})"
        )

    if not fits:
        logger.warning(
            f"Content overflow for {lang_code}: text will be clipped "
            f"(fitted needs {fitted_height:.1f}pt at min scale, available: {height:.1f}pt card)"
        )

    cursor_y = bottom + height - pad

    title = front_content.get("header") or front_content.get("title") or ""
    bullets = front_content.get("bullets") or front_content.get("points") or []

    pdf_canvas.setFont(bold_font, title_size)
    title_lines = wrap_lines(title, bold_font, title_size, width - 2 * pad, rtl=rtl, lang_code=lang_code)
    for line in title_lines:
        if cursor_y < bottom + pad:
            break
        draw_text_line(pdf_canvas, line, left, cursor_y, width, pad, rtl=rtl)
        cursor_y -= leading

    cursor_y -= 4 * optimal_scale

    pdf_canvas.setFont(regular_font, body_size)
    bullet_char = u"\u2022"

    for bullet_item in bullets:
        if cursor_y < bottom + pad:
            break

        if isinstance(bullet_item, dict):
            bullet_text = (bullet_item.get("text") or "").strip()
        else:
            bullet_text = str(bullet_item).strip()

        if not bullet_text:
            continue

        bullet_lines = wrap_lines(
            bullet_text,
            regular_font,
            body_size,
            width - 2 * pad - bullet_indent,
            rtl=rtl,
            lang_code=lang_code,
        )
        if not bullet_lines:
            continue

        if rtl:
            text_width = pdfmetrics.stringWidth(bullet_lines[0], regular_font, body_size)
            pdf_canvas.drawString(left + width - pad, cursor_y, bullet_char)
            pdf_canvas.drawString(left + width - pad - bullet_indent - text_width, cursor_y, bullet_lines[0])
        else:
            pdf_canvas.drawString(left + pad, cursor_y, bullet_char)
            pdf_canvas.drawString(left + pad + bullet_indent, cursor_y, bullet_lines[0])
        cursor_y -= leading

        for continuation_line in bullet_lines[1:]:
            if cursor_y < bottom + pad:
                break
            if rtl:
                text_width = pdfmetrics.stringWidth(continuation_line, regular_font, body_size)
                pdf_canvas.drawString(left + width - pad - bullet_indent - text_width, cursor_y, continuation_line)
            else:
                pdf_canvas.drawString(left + pad + bullet_indent, cursor_y, continuation_line)
            cursor_y -= leading

        cursor_y -= 2 * optimal_scale
