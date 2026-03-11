"""Page guides and shared drawing helpers."""

from typing import Optional, Dict, Any
from urllib.parse import urlparse

from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from ..layout import CardLayout
from ..logging_config import get_logger
from .constants import BASE_FOOTER_SIZE
from .fonts import get_font

logger = get_logger("pdf_guides")


def _truncate_to_width(text: str, font_name: str, font_size: int, max_width: float) -> str:
    """Trim text with ellipsis to fit within max width."""
    if not text:
        return ""
    if pdfmetrics.stringWidth(text, font_name, font_size) <= max_width:
        return text

    ellipsis = "..."
    if pdfmetrics.stringWidth(ellipsis, font_name, font_size) > max_width:
        return ""

    trimmed = text
    while trimmed and pdfmetrics.stringWidth(trimmed + ellipsis, font_name, font_size) > max_width:
        trimmed = trimmed[:-1]

    return (trimmed + ellipsis) if trimmed else ellipsis


def _coerce_source_dict(source: Optional[Any]) -> Dict[str, Any]:
    """Normalize source payloads from dict/model/string to a dict."""
    if source is None:
        return {}

    if isinstance(source, dict):
        return source

    if isinstance(source, str):
        text = source.strip()
        return {"origin": text} if text else {}

    model_dump = getattr(source, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped

    as_dict = getattr(source, "dict", None)
    if callable(as_dict):
        dumped = as_dict()
        if isinstance(dumped, dict):
            return dumped

    out: Dict[str, Any] = {}
    for key in ("origin", "type", "url", "verified"):
        if hasattr(source, key):
            out[key] = getattr(source, key)
    return out


def _source_summary(source: Optional[Any]) -> str:
    """Build a compact source string for fold-mode header metadata."""
    source_data = _coerce_source_dict(source)
    if not source_data:
        return "unknown"

    origin = str(source_data.get("origin") or "").strip()
    source_type = str(source_data.get("type") or "").strip().lower()
    verified = source_data.get("verified")
    url = str(source_data.get("url") or "").strip()

    parts = []
    if origin:
        parts.append(origin)
    if source_type and source_type != origin.lower():
        parts.append(source_type)
    if not parts and source_type:
        parts.append(source_type)

    summary = " / ".join(parts) if parts else "unknown"

    verification_state: Optional[str] = None
    if isinstance(verified, bool):
        verification_state = "verified" if verified else "unverified"
    elif isinstance(verified, str):
        token = verified.strip().lower()
        if token in {"verified", "true", "1", "yes"}:
            verification_state = "verified"
        elif token in {"unverified", "false", "0", "no"}:
            verification_state = "unverified"

    if verification_state:
        summary = f"{summary}, {verification_state}"

    if url:
        parsed = urlparse(url)
        domain = (parsed.netloc or "").lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain:
            summary = f"{summary} [{domain}]"

    return summary


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


# =============================================================================
# FOLD MODE GUIDES
# =============================================================================

def draw_fold_header(
    pdf_canvas: canvas.Canvas,
    layout: CardLayout,
    lang_code: Optional[str] = None,
    lang_name: Optional[str] = None,
    source: Optional[Any] = None,
) -> None:
    """Draw instruction header and cut/fold guide legend at top of page."""
    margin = layout.margin
    page_w = layout.page_width
    header_top = layout.page_height - margin
    header_bottom = header_top - layout.header_height

    regular_font = get_font("en", bold=False)

    # -- Metadata + instruction text (left area) --
    text_size = 8
    line_h = 8
    pdf_canvas.setFont(regular_font, text_size)

    text_x = margin
    text_area_right = margin + (page_w - 2 * margin) * 0.62
    max_text_w = max(1.0, text_area_right - text_x - 2)
    cursor_y = header_top - text_size - 2

    language_value = (lang_name or "").strip() or "unknown"
    code_value = (lang_code or "").strip() or "unknown"
    source_value = _source_summary(source)

    metadata_lines = [
        f"Language: {language_value}",
        f"Code: {code_value}",
        f"Source: {source_value}",
    ]

    for line in metadata_lines:
        clipped = _truncate_to_width(line, regular_font, text_size, max_text_w)
        pdf_canvas.drawString(text_x, cursor_y, clipped)
        cursor_y -= line_h

    instructions = [
        "To print at home, use heavy weight paper or card stock.",
        "Cut out the cards along the dotted lines.",
        "If you cannot print both sides, fold on the center line to make a two-sided card.",
    ]
    pdf_canvas.setFont(regular_font, text_size)
    for line in instructions:
        clipped = _truncate_to_width(line, regular_font, text_size, max_text_w)
        pdf_canvas.drawString(text_x, cursor_y, clipped)
        cursor_y -= line_h

    # -- Guide legend boxes (right side) --
    box_area_left = text_area_right + 0.06 * inch
    box_w = (page_w - margin - box_area_left - 0.08 * inch)
    box_h = 0.28 * inch
    box_gap = 0.08 * inch
    box_x = box_area_left
    box_y_top = header_top - 4

    label_size = 7

    # Cut guide box (dashed border)
    pdf_canvas.saveState()
    pdf_canvas.setLineWidth(0.8)
    pdf_canvas.setDash(2, 2)
    pdf_canvas.rect(box_x, box_y_top - box_h, box_w, box_h, stroke=1, fill=0)
    pdf_canvas.restoreState()
    pdf_canvas.setFont(regular_font, label_size)
    pdf_canvas.drawCentredString(box_x + box_w / 2, box_y_top - box_h / 2 - label_size / 3, "Cut")

    # Fold guide box (solid border)
    fold_box_top = box_y_top - box_h - box_gap
    pdf_canvas.saveState()
    pdf_canvas.setLineWidth(0.8)
    pdf_canvas.rect(box_x, fold_box_top - box_h, box_w, box_h, stroke=1, fill=0)
    pdf_canvas.restoreState()
    pdf_canvas.setFont(regular_font, label_size)
    pdf_canvas.drawCentredString(box_x + box_w / 2, fold_box_top - box_h / 2 - label_size / 3, "Fold")

    # -- Separator line below header --
    pdf_canvas.saveState()
    pdf_canvas.setLineWidth(0.5)
    pdf_canvas.line(margin, header_bottom, page_w - margin, header_bottom)
    pdf_canvas.restoreState()

    logger.debug(
        f"Fold header drawn: header_h={layout.header_height:.1f}pt, "
        f"rows={layout.rows}, lang={lang_code}, source={source_value}"
    )


def draw_fold_center_line(
    pdf_canvas: canvas.Canvas,
    layout: CardLayout,
) -> None:
    """Draw a dashed fold guide down the center of the card grid."""
    center_x = layout.margin + layout.card_width
    grid_bottom = layout.margin
    grid_top = layout.page_height - layout.margin - layout.header_height

    pdf_canvas.saveState()
    pdf_canvas.setLineWidth(0.6)
    pdf_canvas.setDash(4, 3)
    pdf_canvas.line(center_x, grid_bottom, center_x, grid_top)
    pdf_canvas.restoreState()
