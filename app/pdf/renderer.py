"""Builds a print sheet PDF for one language.

Text layout is planned once per sheet (every card on a sheet is the same
size) and then drawn into each card position.
"""

from io import BytesIO

from reportlab.pdfgen.canvas import Canvas

from ..data import Back, Language
from ..fonts import FontManager
from ..layout import MODE_GRID, CardLayout
from .back import draw_back, plan_back
from .colors import hex_to_rgb, text_color_for
from .front import draw_front, plan_front
from .guides import (
    draw_cut_lines,
    draw_fold_center_line,
    draw_fold_header,
    draw_grid_footer,
    draw_grid_guides,
)


def _draw_card(pdf: Canvas, rect, draw, plan, colors) -> None:
    """Draws one card face; colors is (background, text) for color prints, else None."""
    pdf.saveState()
    if colors is not None:
        background, text = colors
        pdf.setFillColorRGB(*background)
        pdf.rect(*rect, stroke=0, fill=1)
        pdf.setFillColorRGB(*text)
    draw(pdf, rect, plan)
    pdf.restoreState()


def render_pdf(language: Language, back: Back, layout: CardLayout, fonts: FontManager,
               color: str | None = None) -> bytes:
    """Raises FontNotAvailableError when the language's script has no font.

    With a normalized hex color, both card faces are filled with it and the
    text is drawn in white or black for contrast; otherwise black on white.
    """
    english = fonts.pick("en")
    front_plan = plan_front(
        language, layout.card_width, layout.card_height, layout.font_scale,
        regular_font=fonts.pick(language.code), bold_font=fonts.pick(language.code, bold=True),
        notice_font=english,
    )
    back_plan = plan_back(back.paragraphs, layout.card_width, layout.card_height,
                          layout.font_scale, english)

    buffer = BytesIO()
    pdf = Canvas(buffer, pagesize=(layout.page_width, layout.page_height))
    pdf.setTitle(f"Know Your Rights - {language.name}")
    colors = None
    if color:
        background = hex_to_rgb(color)
        colors = (background, text_color_for(background))

    if layout.mode == MODE_GRID:
        # Page 1 fronts, page 2 backs, for duplex printing.
        for draw, plan in ((draw_front, front_plan), (draw_back, back_plan)):
            draw_grid_guides(pdf, layout)
            for rect in layout.positions:
                _draw_card(pdf, rect, draw, plan, colors)
                draw_cut_lines(pdf, rect)
            draw_grid_footer(pdf, layout, english, color_print=colors is not None)
            pdf.showPage()
    else:
        # One page: each row is front | back, folded down the middle.
        draw_fold_header(pdf, layout, language, english)
        fronts, backs = layout.positions[0::2], layout.positions[1::2]
        for front_rect, back_rect in zip(fronts, backs, strict=True):
            _draw_card(pdf, front_rect, draw_front, front_plan, colors)
            _draw_card(pdf, back_rect, draw_back, back_plan, colors)
            draw_cut_lines(pdf, front_rect)
            draw_cut_lines(pdf, back_rect)
        draw_fold_center_line(pdf, layout)
        pdf.showPage()

    pdf.save()
    return buffer.getvalue()
