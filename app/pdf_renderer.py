"""
PDF Rendering for Know Your Rights Cards.

=============================================================================
MODULE OVERVIEW
=============================================================================

This module generates printable PDFs for Know Your Rights cards. It creates
two-page documents where:
- Page 1: Front of cards (translated content in the requested language)
- Page 2: Back of cards (English content with printing instructions)

The PDFs support:
- Multiple cards per page (4, 6, 8, or 12)
- Right-to-left (RTL) languages (Arabic, Hebrew, etc.)
- Multiple Unicode scripts via custom font selection
- Cut guides and fold lines for printing

=============================================================================
PDF STRUCTURE
=============================================================================

┌─────────────────────────────────────────────────────────────────────────┐
│ Page 1 (Front)                                                          │
│ ┌─────────────────┬─────────────────┐                                   │
│ │   CARD FRONT    │   CARD FRONT    │                                   │
│ │   (Language)    │   (Language)    │                                   │
│ ├─────────────────┼─────────────────┤                                   │
│ │   CARD FRONT    │   CARD FRONT    │                                   │
│ │   (Language)    │   (Language)    │                                   │
│ └─────────────────┴─────────────────┘                                   │
│ Footer: Printing instructions                                           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ Page 2 (Back)                                                           │
│ ┌─────────────────┬─────────────────┐                                   │
│ │   CARD BACK     │   CARD BACK     │                                   │
│ │   (English)     │   (English)     │                                   │
│ ├─────────────────┼─────────────────┤                                   │
│ │   CARD BACK     │   CARD BACK     │                                   │
│ │   (English)     │   (English)     │                                   │
│ └─────────────────┴─────────────────┘                                   │
│ Footer: Printing instructions                                           │
└─────────────────────────────────────────────────────────────────────────┘

=============================================================================
RENDERING FLOW
=============================================================================

1. render_print_sheet_pdf(payload, layout)     <- Main entry point
   ├── Get language code and RTL setting
   ├── Create PDF canvas with correct page size
   ├── Page 1: Front sides
   │   ├── _draw_fold_guides()                 <- Dashed lines for cutting
   │   ├── For each card position:
   │   │   ├── _draw_cut_lines()               <- Dotted card border
   │   │   └── _draw_front()                   <- Card content
   │   │       ├── _get_font()                 <- Select font for language
   │   │       ├── _wrap_lines()               <- Text wrapping
   │   │       ├── Draw header (bold)
   │   │       └── Draw bullet points
   │   └── _draw_footer()                      <- Printing instructions
   ├── Page 2: Back sides
   │   ├── _draw_fold_guides()
   │   ├── For each card position:
   │   │   ├── _draw_cut_lines()
   │   │   └── _draw_back()                    <- English back content
   │   └── _draw_footer()
   └── Return PDF bytes

=============================================================================
RTL (RIGHT-TO-LEFT) SUPPORT
=============================================================================

For RTL languages (Arabic, Hebrew, Persian, Urdu, etc.):
1. arabic_reshaper: Connects Arabic letters properly (isolated->connected)
2. python-bidi: Reorders characters for visual display (logical->visual)
3. Text alignment: Right-aligned instead of left-aligned
4. Bullet points: Positioned on right side

Example RTL transformation:
   Logical order: A-B-C-D  (as stored in Unicode)
   Visual order:  D-C-B-A  (as displayed on screen/paper)

=============================================================================
DEPENDENCIES
=============================================================================

- reportlab: Core PDF generation library
- arabic-reshaper: Arabic letter shaping (optional, for RTL)
- python-bidi: Bidirectional text algorithm (optional, for RTL)

=============================================================================
"""

from io import BytesIO
from typing import Dict, Any, List, Optional

from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics

from .logging_config import get_logger
from .layout import CardLayout, get_default_layout
from .fonts import get_font_manager, is_rtl_language

logger = get_logger("pdf_renderer")


# =============================================================================
# RTL (RIGHT-TO-LEFT) SUPPORT
# =============================================================================
# RTL libraries are optional dependencies. If not installed, RTL text will
# still render but may not connect letters properly or display in correct order.

# Cached flag for whether RTL libraries are available
_rtl_available = None


def _check_rtl_support() -> bool:
    """
    Check if RTL libraries (arabic-reshaper, python-bidi) are available.

    These libraries are required for proper RTL text rendering:
    - arabic-reshaper: Connects Arabic/Persian letters (isolated -> connected)
    - python-bidi: Reorders text for visual display (logical -> visual order)

    This check is lazy-loaded and cached for performance.

    RETURNS:
        True if RTL libraries are available, False otherwise
    """
    global _rtl_available

    if _rtl_available is None:
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            _rtl_available = True
            logger.info("RTL support enabled (arabic-reshaper + python-bidi)")
        except ImportError as e:
            _rtl_available = False
            logger.warning(f"RTL support disabled: {e}")

    return _rtl_available


def _prepare_rtl_text(text: str) -> str:
    """
    Reshape and reorder RTL text for correct PDF rendering.

    Arabic and other RTL scripts need special processing because:
    1. Letters connect differently based on position (initial/medial/final/isolated)
    2. Text needs to be reordered from logical to visual order

    PROCESSING STEPS:
    1. arabic_reshaper.reshape(): Converts isolated letters to connected forms
       Example: ا ل ع ر ب ي ة -> العربية
    2. bidi.get_display(): Reorders for visual display
       Example: "Hello العربية" -> "العربية Hello" (visually)

    PARAMETERS:
        text: Input text (may contain RTL characters)

    RETURNS:
        Processed text ready for PDF rendering, or original if RTL not available
    """
    if not text or not _check_rtl_support():
        return text

    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        # Step 1: Reshape Arabic characters (connect letters)
        reshaped = arabic_reshaper.reshape(text)

        # Step 2: Reorder for visual display (right-to-left)
        return get_display(reshaped)

    except Exception as e:
        logger.warning(f"RTL text processing failed: {e}")
        return text


# =============================================================================
# FONT SELECTION
# =============================================================================

def _get_font(lang_code: Optional[str] = None, bold: bool = False) -> str:
    """
    Get the appropriate font name for a language.

    This is a wrapper around FontManager.pick() that provides the correct
    font for rendering text in a specific language.

    FLOW:
    1. Get singleton FontManager instance
    2. Call pick() with language code and bold flag
    3. Returns registered font name for use with canvas.setFont()

    PARAMETERS:
        lang_code: ISO language code (e.g., 'ar', 'zh-CN', 'en')
                   If None, returns default (English) font
        bold: Whether to return bold variant

    RETURNS:
        Font name string that can be passed to canvas.setFont()
        Example: "NotoSans", "NotoSansArabic-Bold", "NotoSansJP"

    RAISES:
        FontNotAvailableError: If no font is available for the language's script
    """
    return get_font_manager().pick(lang_code, bold)


# =============================================================================
# TYPOGRAPHY CONSTANTS
# =============================================================================
# Base sizes for typography. These are scaled by CardLayout.font_scale
# based on the number of cards per page (more cards = smaller text).

BASE_TITLE_SIZE = 12   # Header/title font size (points)
BASE_BODY_SIZE = 10    # Body text font size (points)
BASE_LEADING = 12      # Line height (points)
BASE_FOOTER_SIZE = 9   # Footer text size (points)


# =============================================================================
# TEXT WRAPPING
# =============================================================================

def _wrap_lines(text: str, font_name: str, font_size: int, max_width: float, rtl: bool = False) -> List[str]:
    """
    Wrap text to fit within a maximum width, with RTL support.

    This function handles:
    - Multi-line input (splits on newlines)
    - Word wrapping to fit within max_width
    - RTL text preprocessing (reshaping + reordering)

    ALGORITHM:
    1. If RTL, preprocess text with _prepare_rtl_text()
    2. Split input on newlines (preserve paragraphs)
    3. For each paragraph, use ReportLab's simpleSplit() to wrap

    PARAMETERS:
        text: Text to wrap (may contain newlines)
        font_name: Name of font (for width calculation)
        font_size: Font size in points
        max_width: Maximum line width in points
        rtl: Whether this is RTL text (triggers preprocessing)

    RETURNS:
        List of lines that fit within max_width
    """
    # Process RTL text if needed (reshape letters, reorder)
    if rtl:
        text = _prepare_rtl_text(text)

    lines = []

    # Split on explicit newlines first (preserve paragraph breaks)
    for paragraph in (text or "").split("\n"):
        paragraph = paragraph.strip()

        if not paragraph:
            # Empty line -> preserve as blank
            lines.append("")
            continue

        # Use ReportLab's simpleSplit for word wrapping
        # This calculates text width using the font metrics and wraps at word boundaries
        lines.extend(simpleSplit(paragraph, font_name, font_size, max_width))

    return lines


# =============================================================================
# VISUAL ELEMENTS (CUT LINES, FOLD GUIDES)
# =============================================================================

def _draw_cut_lines(c: canvas.Canvas, x: float, y: float, w: float, h: float):
    """
    Draw dotted cut lines around a single card.

    These dashed rectangles show where to cut the printed page
    to separate individual cards.

    PARAMETERS:
        c: ReportLab canvas to draw on
        x: Left edge of card (points)
        y: Bottom edge of card (points)
        w: Card width (points)
        h: Card height (points)
    """
    c.saveState()

    # Style: thin dashed line
    c.setLineWidth(0.8)
    c.setDash(2, 2)  # 2pt dash, 2pt gap

    # Draw rectangle (stroke only, no fill)
    c.rect(x, y, w, h, stroke=1, fill=0)

    c.restoreState()


def _draw_fold_guides(c: canvas.Canvas, layout: CardLayout):
    """
    Draw fold/cut guides across the entire page based on layout.

    These dashed lines run between columns and rows of cards,
    showing where to fold or cut the page.

    VISUAL EXAMPLE (2x2 layout):
    ┌─────────┬─────────┐
    │         │         │
    │   :     │    :    │  <- horizontal guide
    │         │         │
    └─────────┴─────────┘
          ^
          vertical guide

    PARAMETERS:
        c: ReportLab canvas to draw on
        layout: CardLayout with position and size information
    """
    c.saveState()

    # Style: thin dashed line
    c.setLineWidth(0.5)
    c.setDash(3, 3)  # 3pt dash, 3pt gap

    page_w = layout.page_width
    page_h = layout.page_height
    margin = layout.margin

    # Vertical guides between columns
    for col in range(1, layout.cols):
        # Position in the middle of the gutter between columns
        x = margin + col * (layout.card_width + layout.gutter) - layout.gutter / 2
        # Draw from bottom margin to top margin
        c.line(x, margin, x, page_h - margin)

    # Horizontal guides between rows
    for row in range(1, layout.rows):
        # Position in the middle of the gutter between rows
        y = margin + layout.footer_height + row * (layout.card_height + layout.gutter) - layout.gutter / 2
        # Draw from left margin to right margin
        c.line(margin, y, page_w - margin, y)

    c.restoreState()


# =============================================================================
# TEXT DRAWING HELPERS
# =============================================================================

def _draw_text_line(c: canvas.Canvas, text: str, x: float, y: float, w: float, pad: float, rtl: bool = False):
    """
    Draw a single line of text, with RTL alignment support.

    For LTR languages: Text is left-aligned
    For RTL languages: Text is right-aligned

    PARAMETERS:
        c: ReportLab canvas (must have font already set)
        text: Text string to draw
        x: Left edge of text area (points)
        y: Baseline y-position (points)
        w: Width of text area (points)
        pad: Padding from edges (points)
        rtl: If True, right-align the text
    """
    if rtl:
        # Right-align: calculate text width and position from right edge
        text_width = pdfmetrics.stringWidth(text, c._fontname, c._fontsize)
        c.drawString(x + w - pad - text_width, y, text)
    else:
        # Left-align: simple left-padded position
        c.drawString(x + pad, y, text)


# =============================================================================
# CARD CONTENT RENDERING
# =============================================================================

def _draw_front(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    front: Dict[str, Any],
    layout: CardLayout,
    rtl: bool = False,
    lang_code: Optional[str] = None,
):
    """
    Draw the front side of a card (translated content).

    The front contains:
    - Header: Bold title text (e.g., "KNOW YOUR RIGHTS" in target language)
    - Bullets: List of rights/points

    LAYOUT:
    ┌─────────────────────────────────┐
    │ HEADER (bold)                   │
    │                                 │
    │ • Bullet point 1                │
    │ • Bullet point 2                │
    │ • Bullet point 3                │
    │   (continues on next line)      │
    │ • Bullet point 4                │
    │                                 │
    └─────────────────────────────────┘

    EXPECTED INPUT FORMAT:
        front = {
            "header": "KNOW YOUR RIGHTS",  # or "title"
            "bullets": [                    # or "points"
                "Point 1",
                "Point 2",
                {"id": "p3", "text": "Point 3"}  # dict format also supported
            ]
        }

    PARAMETERS:
        c: ReportLab canvas to draw on
        x: Left edge of card area (points)
        y: Bottom edge of card area (points)
        w: Card width (points)
        h: Card height (points)
        front: Dict with header and bullets content
        layout: CardLayout for scaling calculations
        rtl: Whether to use RTL text direction
        lang_code: Language code for font selection
    """
    # === Calculate scaled dimensions ===
    # Padding scales with font size (smaller cards = less padding)
    pad = 0.12 * inch * layout.font_scale + 0.06 * inch

    # Get scaled typography sizes
    title_size = layout.get_scaled_font_size(BASE_TITLE_SIZE)
    body_size = layout.get_scaled_font_size(BASE_BODY_SIZE)
    leading = layout.get_scaled_leading(BASE_LEADING)

    # Start drawing from top of card (minus padding)
    cursor_y = y + h - pad

    # === Extract content (handle multiple field name conventions) ===
    title = front.get("header") or front.get("title") or ""
    bullets = front.get("bullets") or front.get("points") or []

    # === Draw Header (Bold) ===
    bold_font = _get_font(lang_code, bold=True)
    c.setFont(bold_font, title_size)

    # Wrap title text to fit within card width
    title_lines = _wrap_lines(title, bold_font, title_size, w - 2 * pad, rtl=rtl)

    for line in title_lines:
        # Stop if we've run out of vertical space
        if cursor_y < y + pad:
            break
        _draw_text_line(c, line, x, cursor_y, w, pad, rtl=rtl)
        cursor_y -= leading

    # Add extra space after title
    cursor_y -= 4 * layout.font_scale

    # === Draw Bullet Points ===
    regular_font = _get_font(lang_code, bold=False)
    c.setFont(regular_font, body_size)

    # Indent for bullet text (after the bullet character)
    bullet_indent = 8 * layout.font_scale
    bullet_char = u"\u2022"  # Unicode bullet point: •

    for b in bullets:
        # Stop if we've run out of vertical space
        if cursor_y < y + pad:
            break

        # Handle both string and dict formats for bullets
        if isinstance(b, dict):
            b = (b.get("text") or "").strip()
        else:
            b = str(b).strip()

        if not b:
            continue

        # Wrap bullet text (accounting for bullet indent)
        bullet_lines = _wrap_lines(b, regular_font, body_size, w - 2 * pad - bullet_indent, rtl=rtl)

        if not bullet_lines:
            continue

        # === First line: with bullet character ===
        if rtl:
            # RTL: bullet on right side, text flows right-to-left
            text_width = pdfmetrics.stringWidth(bullet_lines[0], regular_font, body_size)
            c.drawString(x + w - pad, cursor_y, bullet_char)
            c.drawString(x + w - pad - bullet_indent - text_width, cursor_y, bullet_lines[0])
        else:
            # LTR: bullet on left side, text flows left-to-right
            c.drawString(x + pad, cursor_y, bullet_char)
            c.drawString(x + pad + bullet_indent, cursor_y, bullet_lines[0])
        cursor_y -= leading

        # === Continuation lines: indented, no bullet ===
        for cont in bullet_lines[1:]:
            if cursor_y < y + pad:
                break
            if rtl:
                text_width = pdfmetrics.stringWidth(cont, regular_font, body_size)
                c.drawString(x + w - pad - bullet_indent - text_width, cursor_y, cont)
            else:
                c.drawString(x + pad + bullet_indent, cursor_y, cont)
            cursor_y -= leading

        # Add small space between bullets
        cursor_y -= 2 * layout.font_scale


def _draw_back(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    back_paragraphs: List[str],
    layout: CardLayout,
    rtl: bool = False,
    lang_code: Optional[str] = None,
):
    """
    Draw the back side of a card (English content).

    The back contains paragraphs of explanatory text. Currently,
    back content is always in English regardless of front language.

    LAYOUT:
    ┌─────────────────────────────────┐
    │ Paragraph 1 text that wraps     │
    │ across multiple lines.          │
    │                                 │
    │ Paragraph 2 text continues      │
    │ with more information.          │
    │                                 │
    │ Paragraph 3...                  │
    └─────────────────────────────────┘

    PARAMETERS:
        c: ReportLab canvas to draw on
        x: Left edge of card area (points)
        y: Bottom edge of card area (points)
        w: Card width (points)
        h: Card height (points)
        back_paragraphs: List of paragraph strings
        layout: CardLayout for scaling calculations
        rtl: Whether to use RTL direction (usually False for back)
        lang_code: Language code for font (usually "en" for back)
    """
    # === Calculate scaled dimensions ===
    pad = 0.12 * inch * layout.font_scale + 0.06 * inch
    body_size = layout.get_scaled_font_size(BASE_BODY_SIZE)
    leading = layout.get_scaled_leading(BASE_LEADING)

    # Start from top of card
    cursor_y = y + h - pad

    # Back is always in English, so use English font
    regular_font = _get_font("en", bold=False)
    c.setFont(regular_font, body_size)

    # === Draw each paragraph ===
    for p in back_paragraphs:
        p = (p or "").strip()
        if not p:
            continue

        # Wrap paragraph to fit card width
        lines = _wrap_lines(p, regular_font, body_size, w - 2 * pad, rtl=rtl)

        for line in lines:
            # Stop if we've run out of space
            if cursor_y < y + pad:
                return
            _draw_text_line(c, line, x, cursor_y, w, pad, rtl=rtl)
            cursor_y -= leading

        # Add extra space between paragraphs
        cursor_y -= 4 * layout.font_scale


def _draw_footer(c: canvas.Canvas, layout: CardLayout, lang_code: Optional[str] = None):
    """
    Draw printing instructions footer at bottom of page.

    The footer contains instructions for printing the cards at home
    or using a professional printer. Always displayed in English.

    PARAMETERS:
        c: ReportLab canvas to draw on
        layout: CardLayout with margin and scale information
        lang_code: Ignored (footer is always English)
    """
    # Printing instructions text
    footer_text = (
        "To print at home, use heavy weight paper, or card stock. Cut out the cards along the dotted lines. If\n"
        "you're unable to print on both sides, you can simply fold on the center line to make a 2-sided card.\n"
        "If you use a professional printer, we suggest you print 2-sided cards with white text on red card stock\n"
        "with rounded corners."
    )

    c.saveState()

    # Footer is always in English, with scaled font size (minimum 7pt)
    footer_size = max(7, int(BASE_FOOTER_SIZE * layout.font_scale))
    c.setFont(_get_font("en", bold=False), footer_size)

    # Position at bottom left, above margin
    x = layout.margin
    y = layout.margin + 0.1 * inch
    line_height = footer_size + 2

    # Draw each line of footer
    for line in footer_text.split("\n"):
        c.drawString(x, y, line)
        y += line_height  # Move up for next line

    c.restoreState()


# =============================================================================
# MAIN PDF RENDERING FUNCTION
# =============================================================================

def render_print_sheet_pdf(
    payload: Dict[str, Any],
    layout: Optional[CardLayout] = None,
) -> bytes:
    """
    Create a 2-page PDF with front and back sides of cards.

    This is the main entry point for PDF generation. It creates a complete
    printable document with:
    - Page 1: Front sides of all cards (in requested language)
    - Page 2: Back sides of all cards (in English)

    Both pages include cut guides and printing instructions.

    FLOW:
    1. Parse payload for language code and RTL setting
    2. Create PDF canvas with correct page size
    3. Render Page 1 (fronts):
       - Draw fold guides
       - Draw each card front with translated content
       - Draw footer
    4. Render Page 2 (backs):
       - Draw fold guides
       - Draw each card back with English content
       - Draw footer
    5. Save and return PDF bytes

    PARAMETERS:
        payload: Card content dictionary with keys:
            - code: Language code (e.g., 'ar', 'zh-CN', 'en')
            - front: {"header": ..., "bullets": [...]}
            - back: {"paragraphs": [...]} or back_paragraphs: [...]
            - rtl: bool (optional, auto-detected from code if missing)

        layout: CardLayout instance defining page size and card positions.
                Defaults to 4-card layout if not provided.

    RETURNS:
        Complete PDF file as bytes (ready to save or stream)

    RAISES:
        FontNotAvailableError: If no font is available for the language's script.
            This is raised by _get_font() when attempting to render text.

    EXAMPLE:
        payload = {
            "code": "es",
            "front": {
                "header": "CONOZCA SUS DERECHOS",
                "bullets": ["Punto 1", "Punto 2"]
            },
            "back": {
                "paragraphs": ["English back content..."]
            }
        }
        pdf_bytes = render_print_sheet_pdf(payload)
        with open("cards.pdf", "wb") as f:
            f.write(pdf_bytes)
    """
    # === Use default layout if not provided ===
    if layout is None:
        layout = get_default_layout()

    # === Extract settings from payload ===

    # Language code for font selection
    lang_code = payload.get("code", "en")

    # RTL detection: use explicit value or auto-detect from language
    if "rtl" in payload:
        rtl = bool(payload["rtl"])
    else:
        rtl = is_rtl_language(lang_code)

    logger.debug(f"Rendering PDF for {lang_code}, {layout.cards_per_page} cards/page, RTL={rtl}")

    # === Create PDF canvas ===
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(layout.page_width, layout.page_height))

    # === PAGE 1: FRONT SIDES ===
    # Draw fold guides across the page
    _draw_fold_guides(c, layout)

    # Draw each card front at its calculated position
    for (px, py, pw, ph) in layout.positions:
        # Draw dotted cut lines around card
        _draw_cut_lines(c, px, py, pw, ph)
        # Draw card content (header + bullets in target language)
        _draw_front(c, px, py, pw, ph, payload.get("front", {}), layout, rtl=rtl, lang_code=lang_code)

    # Draw printing instructions footer
    _draw_footer(c, layout, lang_code=lang_code)

    # Finish page 1
    c.showPage()

    # === PAGE 2: BACK SIDES ===
    # Note: Back content is always in English (LTR) per current design

    # Draw fold guides
    _draw_fold_guides(c, layout)

    # Extract back content (handle multiple field name conventions)
    back = payload.get("back") or {}
    back_paragraphs = back.get("paragraphs") or payload.get("back_paragraphs") or []

    # Draw each card back at its calculated position
    for (px, py, pw, ph) in layout.positions:
        _draw_cut_lines(c, px, py, pw, ph)
        # Note: rtl=False and lang_code="en" because back is always English
        _draw_back(c, px, py, pw, ph, back_paragraphs, layout, rtl=False, lang_code="en")

    # Draw printing instructions footer
    _draw_footer(c, layout, lang_code="en")

    # === Finalize and return ===
    c.save()
    return buf.getvalue()
