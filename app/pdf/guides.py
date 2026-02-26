"""Page guides and shared drawing helpers."""

from typing import Optional

from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from ..layout import CardLayout
from .constants import BASE_FOOTER_SIZE
from .fonts import get_font


def draw_cut_lines(
    pdf_canvas: canvas.Canvas,
    left: float,
    bottom: float,
    width: float,
    height: float,
) -> None:
    """Draw dotted cut lines around a single card."""
    pdf_canvas.saveState()
    pdf_canvas.setLineWidth(0.8)
    pdf_canvas.setDash(2, 2)
    pdf_canvas.rect(left, bottom, width, height, stroke=1, fill=0)
    pdf_canvas.restoreState()


def draw_fold_guides(pdf_canvas: canvas.Canvas, layout: CardLayout) -> None:
    """Draw fold/cut guides across the entire page."""
    pdf_canvas.saveState()
    pdf_canvas.setLineWidth(0.5)
    pdf_canvas.setDash(3, 3)

    page_w = layout.page_width
    page_h = layout.page_height
    margin = layout.margin

    for col in range(1, layout.cols):
        guide_x = margin + col * (layout.card_width + layout.gutter) - layout.gutter / 2
        pdf_canvas.line(guide_x, margin, guide_x, page_h - margin)

    for row in range(1, layout.rows):
        guide_y = margin + layout.footer_height + row * (layout.card_height + layout.gutter) - layout.gutter / 2
        pdf_canvas.line(margin, guide_y, page_w - margin, guide_y)

    pdf_canvas.restoreState()


def draw_text_line(
    pdf_canvas: canvas.Canvas,
    text: str,
    left: float,
    baseline_y: float,
    width: float,
    pad: float,
    rtl: bool = False,
) -> None:
    """Draw one line, left-aligned for LTR and right-aligned for RTL."""
    if rtl:
        text_width = pdfmetrics.stringWidth(text, pdf_canvas._fontname, pdf_canvas._fontsize)
        pdf_canvas.drawString(left + width - pad - text_width, baseline_y, text)
    else:
        pdf_canvas.drawString(left + pad, baseline_y, text)


def draw_footer(
    pdf_canvas: canvas.Canvas,
    layout: CardLayout,
    lang_code: Optional[str] = None,
) -> None:
    """Draw printing instructions footer at bottom of page."""
    footer_text = (
        "To print at home, use heavy weight paper, or card stock. Cut out the cards along the dotted lines. If\n"
        "you're unable to print on both sides, you can simply fold on the center line to make a 2-sided card.\n"
        "If you use a professional printer, we suggest you print 2-sided cards with white text on red card stock\n"
        "with rounded corners."
    )

    pdf_canvas.saveState()
    footer_size = max(7, int(BASE_FOOTER_SIZE * layout.font_scale))
    pdf_canvas.setFont(get_font("en", bold=False), footer_size)

    text_x = layout.margin
    text_y = layout.margin + 0.1 * inch
    line_height = footer_size + 2

    for line in footer_text.split("\n"):
        pdf_canvas.drawString(text_x, text_y, line)
        text_y += line_height

    pdf_canvas.restoreState()
