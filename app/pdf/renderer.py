"""Main PDF orchestration for print-sheet rendering."""

from io import BytesIO
from typing import Dict, Any, Optional

from reportlab.pdfgen import canvas

from ..fonts import is_rtl_language
from ..layout import CardLayout, get_default_layout
from ..logging_config import get_logger
from .back import draw_back
from .front import draw_front
from .guides import (
    draw_cut_lines,
    draw_fold_guides,
    draw_footer,
    draw_fold_header,
    draw_fold_center_line,
)

logger = get_logger("pdf_renderer")


def render_print_sheet_pdf(
    payload: Dict[str, Any],
    layout: Optional[CardLayout] = None,
) -> bytes:
    """Create a 2-page PDF with front and back sides of cards."""
    if layout is None:
        layout = get_default_layout()

    lang_code = payload.get("code", "en")
    if "rtl" in payload:
        is_rtl = bool(payload["rtl"])
    else:
        is_rtl = is_rtl_language(lang_code)

    logger.debug(f"Rendering PDF for {lang_code}, {layout.cards_per_page} cards/page, RTL={is_rtl}")

    pdf_buffer = BytesIO()
    pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=(layout.page_width, layout.page_height))

    # Page 1: front.
    draw_fold_guides(pdf_canvas, layout)
    for (card_left, card_bottom, card_width, card_height) in layout.positions:
        draw_cut_lines(pdf_canvas, card_left, card_bottom, card_width, card_height)
        draw_front(
            pdf_canvas,
            card_left,
            card_bottom,
            card_width,
            card_height,
            payload.get("front", {}),
            layout,
            rtl=is_rtl,
            lang_code=lang_code,
        )
    draw_footer(pdf_canvas, layout, lang_code=lang_code)
    pdf_canvas.showPage()

    # Page 2: back (always English content in current design).
    draw_fold_guides(pdf_canvas, layout)
    back_payload = payload.get("back") or {}
    back_paragraphs = back_payload.get("paragraphs") or payload.get("back_paragraphs") or []
    for (card_left, card_bottom, card_width, card_height) in layout.positions:
        draw_cut_lines(pdf_canvas, card_left, card_bottom, card_width, card_height)
        draw_back(
            pdf_canvas,
            card_left,
            card_bottom,
            card_width,
            card_height,
            back_paragraphs,
            layout,
            rtl=False,
            lang_code="en",
        )
    draw_footer(pdf_canvas, layout, lang_code="en")

    pdf_canvas.save()
    return pdf_buffer.getvalue()


def render_fold_sheet_pdf(
    payload: Dict[str, Any],
    layout: CardLayout,
) -> bytes:
    """Create a single-page fold-format PDF with front|back side-by-side per row.

    Each row contains:
      - Left cell:  translated front (RTL-aware)
      - Right cell: English back (always LTR)

    This matches the official red card fold sheet layout used by the
    frontend browser print mode.
    """
    lang_code = payload.get("code", "en")
    lang_name = payload.get("name", lang_code)
    source_info = payload.get("source")
    if "rtl" in payload:
        is_rtl = bool(payload["rtl"])
    else:
        is_rtl = is_rtl_language(lang_code)

    logger.info(
        f"Rendering FOLD PDF for {lang_code}: {layout.rows} rows, "
        f"font_scale={layout.font_scale:.2f}, RTL={is_rtl}"
    )

    pdf_buffer = BytesIO()
    pdf_canvas = canvas.Canvas(
        pdf_buffer,
        pagesize=(layout.page_width, layout.page_height),
    )

    front_content = payload.get("front", {})
    back_payload = payload.get("back") or {}
    back_paragraphs = (
        back_payload.get("paragraphs")
        or payload.get("back_paragraphs")
        or []
    )

    # Header with instructions and cut/fold guide legend
    draw_fold_header(
        pdf_canvas, layout, lang_code=lang_code, lang_name=lang_name, source=source_info,
    )

    # Card grid: iterate rows; positions are stored as pairs (front, back)
    for row_idx in range(layout.rows):
        front_pos = layout.positions[row_idx * 2]
        back_pos = layout.positions[row_idx * 2 + 1]

        fl, fb, fw, fh = front_pos
        bl, bb, bw, bh = back_pos

        # Dashed cut borders around each cell
        draw_cut_lines(pdf_canvas, fl, fb, fw, fh)
        draw_cut_lines(pdf_canvas, bl, bb, bw, bh)

        # Front card (translated, possibly RTL)
        draw_front(
            pdf_canvas, fl, fb, fw, fh,
            front_content, layout,
            rtl=is_rtl, lang_code=lang_code,
        )

        # Back card (English, always LTR)
        draw_back(
            pdf_canvas, bl, bb, bw, bh,
            back_paragraphs, layout,
            rtl=False, lang_code="en",
        )

    # Center fold guide line
    draw_fold_center_line(pdf_canvas, layout)

    pdf_canvas.save()
    return pdf_buffer.getvalue()
