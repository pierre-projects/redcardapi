"""Back of the card: the English statement shown to the officer."""

import logging
from dataclasses import dataclass

from reportlab.pdfgen.canvas import Canvas

from ..layout import Rect
from ..text import wrap_text
from .constants import BASE_BODY_SIZE
from .draw import draw_line
from .fitting import Typography, find_best_fit_scale, typography

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackPlan:
    typo: Typography
    font: str
    paragraphs: list[list[str]]
    height: float


def plan_back(paragraphs: list[str], card_width: float, card_height: float,
              base_scale: float, font: str) -> BackPlan:
    cache: dict[float, BackPlan] = {}

    def layout_at(scale: float) -> BackPlan:
        if scale not in cache:
            t = typography(scale)
            width = max(1.0, card_width - 2 * t.pad)
            wrapped = [wrap_text(p, font, t.body_size, width) for p in paragraphs]
            height = 2 * t.pad + sum(len(lines) * t.leading + 4 * scale for lines in wrapped)
            cache[scale] = BackPlan(t, font, wrapped, height)
        return cache[scale]

    fit = find_best_fit_scale(
        base_scale=base_scale,
        available_height=card_height,
        base_font_sizes=(BASE_BODY_SIZE,),
        measure_height=lambda s: layout_at(s).height,
    )
    if not fit.fits:
        logger.warning("Back text overflows the card and will be clipped")
    return layout_at(fit.scale)


def draw_back(pdf: Canvas, rect: Rect, plan: BackPlan) -> None:
    left, bottom, width, height = rect
    t = plan.typo
    floor = bottom + t.pad
    y = bottom + height - t.pad

    pdf.setFont(plan.font, t.body_size)
    for lines in plan.paragraphs:
        for line in lines:
            if y < floor:
                return
            draw_line(pdf, line, left + t.pad, left + width - t.pad, y, plan.font, t.body_size)
            y -= t.leading
        y -= 4 * t.scale
