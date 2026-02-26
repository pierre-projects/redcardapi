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
    MIN_FONT_SCALE_FACTOR,
    MIN_ABSOLUTE_FONT_SIZE,
    SCALE_STEP,
)
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


def _find_optimal_font_scale(
    front_content: Dict[str, Any],
    available_height: float,
    available_width: float,
    base_scale: float,
    bold_font: str,
    regular_font: str,
    rtl: bool = False,
    lang_code: Optional[str] = None,
) -> Tuple[float, bool, float]:
    current_scale = base_scale
    min_scale = base_scale * MIN_FONT_SCALE_FACTOR

    original_title_size = max(MIN_ABSOLUTE_FONT_SIZE, int(BASE_TITLE_SIZE * base_scale))
    original_body_size = max(MIN_ABSOLUTE_FONT_SIZE, int(BASE_BODY_SIZE * base_scale))
    original_leading = max(8, int(BASE_LEADING * base_scale))
    original_bullet_indent = 8 * base_scale

    original_height = _measure_front_content(
        front_content=front_content,
        bold_font=bold_font,
        regular_font=regular_font,
        title_size=original_title_size,
        body_size=original_body_size,
        leading=original_leading,
        max_width=available_width,
        bullet_indent=original_bullet_indent,
        rtl=rtl,
        lang_code=lang_code,
    )

    while current_scale >= min_scale:
        title_size = max(MIN_ABSOLUTE_FONT_SIZE, int(BASE_TITLE_SIZE * current_scale))
        body_size = max(MIN_ABSOLUTE_FONT_SIZE, int(BASE_BODY_SIZE * current_scale))
        leading = max(8, int(BASE_LEADING * current_scale))
        bullet_indent = 8 * current_scale

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

        if content_height <= available_height:
            return current_scale, True, original_height

        current_scale -= SCALE_STEP

    return min_scale, False, original_height


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

    base_pad = 0.12 * inch * layout.font_scale + 0.06 * inch
    available_height = height - 2 * base_pad
    available_width = width - 2 * base_pad

    optimal_scale, fits, original_height = _find_optimal_font_scale(
        front_content=front_content,
        available_height=available_height,
        available_width=available_width,
        base_scale=layout.font_scale,
        bold_font=bold_font,
        regular_font=regular_font,
        rtl=rtl,
        lang_code=lang_code,
    )

    if optimal_scale < layout.font_scale:
        scale_percent = int((optimal_scale / layout.font_scale) * 100)
        logger.info(
            f"Adaptive scaling for {lang_code}: reduced to {scale_percent}% "
            f"(original height: {original_height:.1f}pt, available: {available_height:.1f}pt)"
        )

    if not fits:
        logger.warning(
            f"Content overflow for {lang_code}: text will be clipped "
            f"(content needs {original_height:.1f}pt, available: {available_height:.1f}pt)"
        )

    pad = 0.12 * inch * optimal_scale + 0.06 * inch
    title_size = max(MIN_ABSOLUTE_FONT_SIZE, int(BASE_TITLE_SIZE * optimal_scale))
    body_size = max(MIN_ABSOLUTE_FONT_SIZE, int(BASE_BODY_SIZE * optimal_scale))
    leading = max(8, int(BASE_LEADING * optimal_scale))
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
    bullet_indent = 8 * optimal_scale
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
