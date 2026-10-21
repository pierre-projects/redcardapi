"""Low-level line drawing shared by card faces and page furniture."""

from reportlab.pdfgen.canvas import Canvas

from ..text import shape, text_width


def draw_line(pdf: Canvas, text: str, left: float, right: float, y: float,
              font: str, size: float, rtl: bool = False) -> None:
    """Draw one wrapped line: left-aligned, or right-aligned for RTL."""
    shaped = shape(text, font, size)
    x = right - text_width(text, font, size) if rtl else left
    pdf.drawString(x, y, shaped)
