"""Low-level line drawing shared by card faces and page furniture."""

from reportlab.pdfgen.canvas import Canvas

from ..text import shape, text_width
from ..text.bidi import is_arabic_script, visual_runs


def draw_line(pdf: Canvas, text: str, left: float, right: float, y: float,
              font: str, size: float, rtl: bool = False) -> None:
    """Draw one wrapped line: left-aligned, or right-aligned for RTL."""
    if rtl and is_arabic_script(text):
        # Logical-order line: lay out its runs right to left, each shaped
        # (HarfBuzz returns an Arabic run's glyphs already in visual order).
        runs = visual_runs(text)
        widths = [text_width(run, font, size) for run in runs]
        x = right - sum(widths)
        for run, width in zip(runs, widths, strict=True):
            pdf.drawString(x, y, shape(run, font, size))
            x += width
        return

    x = right - text_width(text, font, size) if rtl else left
    pdf.drawString(x, y, shape(text, font, size))
