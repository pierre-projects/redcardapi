"""Front of the card: header and bullets in the card's language."""

import logging
from dataclasses import dataclass

from reportlab.pdfgen.canvas import Canvas

from ..data import Language
from ..fonts import Script, detect_script
from ..layout import Rect
from ..text import wrap_text
from .constants import BASE_BODY_SIZE, BASE_TITLE_SIZE
from .draw import draw_line
from .fitting import Typography, find_best_fit_scale, typography

logger = logging.getLogger(__name__)

BULLET = "•"

# Scripts whose stacked vowels and medials extend far above and below the
# baseline; at the Latin line height their lines overlap.
LINE_HEIGHT = {Script.MYANMAR: 1.55, Script.KHMER: 1.35, Script.LAO: 1.2, Script.THAI: 1.2}


@dataclass(frozen=True)
class FrontPlan:
    """Wrapped lines and typography, computed once and drawn on every card."""
    typo: Typography
    bold_font: str
    regular_font: str
    rtl: bool
    title_lines: list[str]
    bullet_lines: list[list[str]]
    height: float


def plan_front(language: Language, card_width: float, card_height: float,
               base_scale: float, regular_font: str, bold_font: str) -> FrontPlan:
    script = detect_script(language.code)
    line_height = LINE_HEIGHT.get(script, 1.0)
    header = language.front.header
    bullets = [b.text for b in language.front.bullets]
    cache: dict[float, FrontPlan] = {}

    def layout_at(scale: float) -> FrontPlan:
        if scale not in cache:
            t = typography(scale, line_height)
            width = max(1.0, card_width - 2 * t.pad)
            title = wrap_text(header, bold_font, t.title_size, width, script, language.rtl)
            body = [wrap_text(b, regular_font, t.body_size, width - t.bullet_indent, script, language.rtl)
                    for b in bullets]
            height = (
                2 * t.pad
                + len(title) * t.leading + 4 * scale
                + sum(len(lines) * t.leading + 2 * scale for lines in body)
            )
            cache[scale] = FrontPlan(t, bold_font, regular_font, language.rtl, title, body, height)
        return cache[scale]

    fit = find_best_fit_scale(
        base_scale=base_scale,
        available_height=card_height,
        base_font_sizes=(BASE_TITLE_SIZE, BASE_BODY_SIZE),
        measure_height=lambda s: layout_at(s).height,
    )
    if not fit.fits:
        logger.warning("Front text for %s overflows the card and will be clipped", language.code)
    return layout_at(fit.scale)


def draw_front(pdf: Canvas, rect: Rect, plan: FrontPlan) -> None:
    left, bottom, width, height = rect
    t = plan.typo
    inner_left, inner_right = left + t.pad, left + width - t.pad
    floor = bottom + t.pad
    y = bottom + height - t.pad

    pdf.setFont(plan.bold_font, t.title_size)
    for line in plan.title_lines:
        if y < floor:
            return
        draw_line(pdf, line, inner_left, inner_right, y, plan.bold_font, t.title_size, plan.rtl)
        y -= t.leading
    y -= 4 * t.scale

    pdf.setFont(plan.regular_font, t.body_size)
    for lines in plan.bullet_lines:
        for index, line in enumerate(lines):
            if y < floor:
                return
            if index == 0:
                if plan.rtl:
                    pdf.drawRightString(inner_right, y, BULLET)
                else:
                    pdf.drawString(inner_left, y, BULLET)
            draw_line(pdf, line, inner_left + t.bullet_indent, inner_right - t.bullet_indent, y,
                      plan.regular_font, t.body_size, plan.rtl)
            y -= t.leading
        y -= 2 * t.scale
