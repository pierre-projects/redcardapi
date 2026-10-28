"""Page furniture: cut and fold guides, footer, fold-sheet header."""

from urllib.parse import urlparse

from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

from ..data import Language
from ..layout import CardLayout
from .constants import BASE_FOOTER_SIZE

GRID_FOOTER = (
    "To print at home, use heavy weight paper, or card stock. Cut out the cards along the dotted lines. If",
    "you're unable to print on both sides, you can simply fold on the center line to make a 2-sided card.",
    "If you use a professional printer, we suggest you print 2-sided cards with white text on red card stock",
    "with rounded corners.",
)
COLOR_GRID_FOOTER = (
    "To print at home, use heavy weight paper, or card stock. Cut out the cards along the dotted lines. If",
    "you're unable to print on both sides, you can simply fold on the center line to make a 2-sided card.",
    "This sheet is already in color, so plain white paper or card stock works.",
)
FOLD_INSTRUCTIONS = (
    "To print at home, use heavy weight paper or card stock.",
    "Cut out the cards along the dotted lines.",
    "If you cannot print both sides, fold on the center line to make a two-sided card.",
)


def _truncate(text: str, font: str, size: float, max_width: float) -> str:
    if pdfmetrics.stringWidth(text, font, size) <= max_width:
        return text
    while text and pdfmetrics.stringWidth(text + "...", font, size) > max_width:
        text = text[:-1]
    return text + "..."


def source_summary(language: Language) -> str:
    """e.g. "ILRC / official, verified [ilrc.org]"."""
    source = language.source
    parts = [p for p in (source.origin, source.type) if p]
    summary = " / ".join(dict.fromkeys(parts)) or "unknown"
    summary += ", verified" if source.verified else ", unverified"
    domain = urlparse(source.url or "").netloc.lower().removeprefix("www.")
    return f"{summary} [{domain}]" if domain else summary


def draw_cut_lines(pdf: Canvas, rect) -> None:
    left, bottom, width, height = rect
    pdf.saveState()
    pdf.setLineWidth(0.8)
    pdf.setDash(2, 2)
    pdf.rect(left, bottom, width, height, stroke=1, fill=0)
    pdf.restoreState()


def draw_grid_guides(pdf: Canvas, layout: CardLayout) -> None:
    """Dashed lines through the gutters between cards."""
    pdf.saveState()
    pdf.setLineWidth(0.5)
    pdf.setDash(3, 3)
    m = layout.margin
    for col in range(1, layout.cols):
        x = m + col * (layout.card_width + layout.gutter) - layout.gutter / 2
        pdf.line(x, m, x, layout.page_height - m)
    for row in range(1, layout.rows):
        y = m + layout.footer_height + row * (layout.card_height + layout.gutter) - layout.gutter / 2
        pdf.line(m, y, layout.page_width - m, y)
    pdf.restoreState()


def draw_grid_footer(pdf: Canvas, layout: CardLayout, font: str, color_print: bool = False) -> None:
    size = max(7, int(BASE_FOOTER_SIZE * layout.font_scale))
    pdf.saveState()
    pdf.setFont(font, size)
    y = layout.margin + 0.1 * inch
    # Drawn bottom-up, so the last line of the text sits lowest.
    for line in reversed(COLOR_GRID_FOOTER if color_print else GRID_FOOTER):
        pdf.drawString(layout.margin, y, line)
        y += size + 2
    pdf.restoreState()


def draw_fold_header(pdf: Canvas, layout: CardLayout, language: Language, font: str | None) -> None:
    """Language/source details and instructions on the left, cut/fold legend on the right."""
    m, page_w = layout.margin, layout.page_width
    top = layout.page_height - m
    size = 8
    text_right = m + (page_w - 2 * m) * 0.62
    max_width = max(1.0, text_right - m - 2)

    pdf.setFont(font, size)
    y = top - size - 2
    lines = (
        f"Language: {language.name}",
        f"Code: {language.display_code}",
        f"Source: {source_summary(language)}",
        *FOLD_INSTRUCTIONS,
    )
    for line in lines:
        pdf.drawString(m, y, _truncate(line, font, size, max_width))
        y -= size

    box_x = text_right + 0.06 * inch
    box_w = page_w - m - box_x - 0.08 * inch
    box_h = 0.28 * inch
    for index, (label, dashed) in enumerate((("Cut", True), ("Fold", False))):
        box_top = top - 4 - index * (box_h + 0.08 * inch)
        pdf.saveState()
        pdf.setLineWidth(0.8)
        if dashed:
            pdf.setDash(2, 2)
        pdf.rect(box_x, box_top - box_h, box_w, box_h, stroke=1, fill=0)
        pdf.restoreState()
        pdf.setFont(font, 7)
        pdf.drawCentredString(box_x + box_w / 2, box_top - box_h / 2 - 7 / 3, label)

    pdf.saveState()
    pdf.setLineWidth(0.5)
    header_bottom = top - layout.header_height
    pdf.line(m, header_bottom, page_w - m, header_bottom)
    pdf.restoreState()


def draw_fold_center_line(pdf: Canvas, layout: CardLayout) -> None:
    x = layout.margin + layout.card_width
    pdf.saveState()
    pdf.setLineWidth(0.6)
    pdf.setDash(4, 3)
    pdf.line(x, layout.margin, x, layout.page_height - layout.margin - layout.header_height)
    pdf.restoreState()
