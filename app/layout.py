"""
Card Layout Calculation for Flexible PDF Generation.

=============================================================================
MODULE OVERVIEW
=============================================================================

This module handles the mathematical calculations for placing cards on a
PDF page. It supports multiple layout configurations (4, 6, 8, or 12 cards
per page) and automatically calculates:

- Card dimensions (width/height)
- Card positions on the page
- Font scaling factors for readability
- Margins, gutters, and footer spacing

=============================================================================
LAYOUT PRESETS
=============================================================================

The system supports four layout configurations:

┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ 4 Cards (2x2)   │   │ 6 Cards (2x3)   │   │ 8 Cards (2x4)   │   │ 12 Cards (3x4)  │
│ ┌─────┬─────┐   │   │ ┌─────┬─────┐   │   │ ┌─────┬─────┐   │   │ ┌───┬───┬───┐   │
│ │     │     │   │   │ │     │     │   │   │ │     │     │   │   │ │   │   │   │   │
│ ├─────┼─────┤   │   │ ├─────┼─────┤   │   │ ├─────┼─────┤   │   │ ├───┼───┼───┤   │
│ │     │     │   │   │ │     │     │   │   │ │     │     │   │   │ │   │   │   │   │
│ └─────┴─────┘   │   │ ├─────┼─────┤   │   │ ├─────┼─────┤   │   │ ├───┼───┼───┤   │
│ font_scale: 1.0 │   │ │     │     │   │   │ │     │     │   │   │ │   │   │   │   │
└─────────────────┘   │ └─────┴─────┘   │   │ ├─────┼─────┤   │   │ ├───┼───┼───┤   │
                      │ font_scale: 0.85│   │ │     │     │   │   │ │   │   │   │   │
                      └─────────────────┘   │ └─────┴─────┘   │   │ └───┴───┴───┘   │
                                            │ font_scale: 0.75│   │ font_scale: 0.6 │
                                            └─────────────────┘   └─────────────────┘

=============================================================================
PAGE STRUCTURE
=============================================================================

The page is divided as follows:

┌─────────────────────────────────────────────────────────────────────────┐
│                              TOP MARGIN                                  │
│  ┌──────────┐  GUTTER  ┌──────────┐                                     │
│  │          │          │          │                                     │
│  │  CARD    │          │  CARD    │                                     │
│  │          │          │          │                                     │
│  └──────────┘          └──────────┘                                     │
│       GUTTER                                                            │
│  ┌──────────┐          ┌──────────┐                                     │
│  │          │          │          │                                     │
│  │  CARD    │          │  CARD    │                                     │
│  │          │          │          │                                     │
│  └──────────┘          └──────────┘                                     │
│                           FOOTER HEIGHT                                 │
│  [ Printing instructions footer text ]                                  │
│                            BOTTOM MARGIN                                │
└─────────────────────────────────────────────────────────────────────────┘

=============================================================================
COORDINATE SYSTEM
=============================================================================

PDF uses a bottom-left origin coordinate system:
- (0, 0) is at the bottom-left corner of the page
- X increases to the right
- Y increases upward

Card positions are stored as (x, y, width, height) where:
- x: Left edge of card
- y: Bottom edge of card
- width: Card width
- height: Card height

=============================================================================
FONT SCALING
=============================================================================

Font size is scaled based on card area to maintain readability:
- 4 cards: font_scale = 1.0 (full size)
- 6 cards: font_scale ≈ 0.85
- 8 cards: font_scale ≈ 0.75
- 12 cards: font_scale = 0.6 (minimum)

The formula: font_scale = sqrt(current_card_area / base_card_area)
This ensures text scales proportionally with available space.

=============================================================================
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch


# =============================================================================
# LAYOUT PRESETS
# =============================================================================

class LayoutPreset(Enum):
    """
    Predefined card layout configurations.

    Each preset defines a grid of (columns, rows) for card placement.
    The total cards per page is columns * rows.

    AVAILABLE PRESETS:
        CARDS_4:  2x2 grid = 4 cards  (largest cards, best readability)
        CARDS_6:  2x3 grid = 6 cards
        CARDS_8:  2x4 grid = 8 cards
        CARDS_12: 3x4 grid = 12 cards (smallest cards, maximum density)
    """
    CARDS_4 = (2, 2)   # 2 columns x 2 rows = 4 cards
    CARDS_6 = (2, 3)   # 2 columns x 3 rows = 6 cards
    CARDS_8 = (2, 4)   # 2 columns x 4 rows = 8 cards
    CARDS_12 = (3, 4)  # 3 columns x 4 rows = 12 cards

    @classmethod
    def from_count(cls, count: int) -> "LayoutPreset":
        """
        Get layout preset from desired card count.

        PARAMETERS:
            count: Number of cards per page (4, 6, 8, or 12)

        RETURNS:
            Matching LayoutPreset, defaults to CARDS_4 if count is invalid

        EXAMPLE:
            preset = LayoutPreset.from_count(6)  # Returns CARDS_6
            cols, rows = preset.value            # (2, 3)
        """
        mapping = {
            4: cls.CARDS_4,
            6: cls.CARDS_6,
            8: cls.CARDS_8,
            12: cls.CARDS_12,
        }
        return mapping.get(count, cls.CARDS_4)


# =============================================================================
# CARD LAYOUT CLASS
# =============================================================================

@dataclass
class CardLayout:
    """
    Calculated card layout with dimensions and positions.

    This class holds all the computed values needed to render cards
    on a PDF page. It's created by the from_cards_per_page() factory
    method which handles all the calculations.

    ATTRIBUTES:
        cols: Number of columns in the grid
        rows: Number of rows in the grid
        card_width: Width of each card (in points)
        card_height: Height of each card (in points)
        font_scale: Scaling factor for text (0.6 to 1.0)
        positions: List of (x, y, width, height) tuples for each card
        page_width: Total page width (in points)
        page_height: Total page height (in points)
        margin: Page margin (in points)
        gutter: Space between cards (in points)
        footer_height: Height reserved for footer (in points)

    UNIT NOTE:
        All dimensions are in "points" (1 point = 1/72 inch).
        This is the standard PDF unit used by ReportLab.

    USAGE:
        layout = CardLayout.from_cards_per_page(6)
        for (x, y, w, h) in layout.positions:
            draw_card(x, y, w, h)
    """

    cols: int                                          # Number of columns
    rows: int                                          # Number of rows
    card_width: float                                  # Card width in points
    card_height: float                                 # Card height in points
    font_scale: float                                  # Text scaling factor (0.6-1.0)
    positions: List[Tuple[float, float, float, float]] # (x, y, w, h) for each card
    page_width: float                                  # Page width in points
    page_height: float                                 # Page height in points
    margin: float                                      # Page margin in points
    gutter: float                                      # Space between cards in points
    footer_height: float                               # Footer area height in points

    @property
    def cards_per_page(self) -> int:
        """
        Total number of cards per page.

        RETURNS:
            cols * rows (e.g., 4, 6, 8, or 12)
        """
        return self.cols * self.rows

    @classmethod
    def from_cards_per_page(
        cls,
        count: int,
        page_size: str = "letter",
        margin_inches: float = 0.5,
        gutter_inches: float = 0.25,
        footer_height_inches: float = 0.55,
    ) -> "CardLayout":
        """
        Create a CardLayout from desired cards per page.

        This is the main factory method for creating layouts. It calculates
        all dimensions based on the page size and desired card count.

        CALCULATION FLOW:
        1. Determine page dimensions (Letter or A4)
        2. Convert margins/gutters to points
        3. Get grid dimensions (cols x rows) from preset
        4. Calculate available space after margins/gutters/footer
        5. Calculate card dimensions (divide available space by grid)
        6. Calculate font scale based on card area ratio
        7. Calculate position for each card in the grid

        PARAMETERS:
            count: Number of cards per page (4, 6, 8, or 12)
            page_size: Paper size - "letter" (8.5x11") or "a4" (210x297mm)
            margin_inches: Page margin on all sides (default: 0.5")
            gutter_inches: Space between adjacent cards (default: 0.25")
            footer_height_inches: Height reserved for footer (default: 0.55")

        RETURNS:
            CardLayout with all calculated dimensions and positions

        EXAMPLE:
            # Create a 6-card layout on letter paper
            layout = CardLayout.from_cards_per_page(
                count=6,
                page_size="letter",
                margin_inches=0.5
            )

            # Access calculated values
            print(f"Card size: {layout.card_width}x{layout.card_height} points")
            print(f"Font scale: {layout.font_scale}")

            # Iterate over card positions
            for (x, y, w, h) in layout.positions:
                draw_card_at(x, y, w, h)
        """
        # === STEP 1: Determine page dimensions ===
        # ReportLab provides standard page sizes in points
        if page_size.lower() == "a4":
            page_w, page_h = A4      # 595.27 x 841.89 points
        else:
            page_w, page_h = letter  # 612 x 792 points (8.5" x 11")

        # === STEP 2: Convert inches to points ===
        # 1 inch = 72 points in PDF
        margin = margin_inches * inch
        gutter = gutter_inches * inch
        footer_h = footer_height_inches * inch

        # === STEP 3: Get grid dimensions from preset ===
        preset = LayoutPreset.from_count(count)
        cols, rows = preset.value  # e.g., (2, 3) for 6 cards

        # === STEP 4 & 5: Calculate card dimensions ===

        # Available width calculation:
        # Page width - left margin - right margin - gutters between columns
        # For 2 columns: width - 2*margin - 1*gutter
        # For 3 columns: width - 2*margin - 2*gutters
        available_w = page_w - 2 * margin - (cols - 1) * gutter
        card_w = available_w / cols

        # Available height calculation:
        # Page height - top margin - bottom margin - gutters between rows - footer
        # For 2 rows: height - 2*margin - 1*gutter - footer
        # For 4 rows: height - 2*margin - 3*gutters - footer
        available_h = page_h - 2 * margin - (rows - 1) * gutter - footer_h
        card_h = available_h / rows

        # === STEP 6: Calculate font scale ===
        # Font scale is based on the ratio of current card area to base (4-card) area
        # This ensures text remains readable as cards get smaller

        # Base card area (for 4-card 2x2 layout)
        base_card_area = (
            (page_w - 2 * margin - gutter) / 2 *      # Base card width
            (page_h - 2 * margin - gutter - footer_h) / 2  # Base card height
        )

        # Current card area
        current_card_area = card_w * card_h

        # Scale factor: sqrt of area ratio
        # Using sqrt because area scales with square of linear dimension
        font_scale = min(1.0, (current_card_area / base_card_area) ** 0.5)

        # Enforce minimum readable scale (0.6 = 60% of base size)
        font_scale = max(0.6, font_scale)

        # === STEP 7: Calculate card positions ===
        # PDF uses bottom-left origin, so we build positions from bottom-up
        positions = []
        for r in range(rows):
            for c in range(cols):
                # X position: margin + column offset
                x = margin + c * (card_w + gutter)

                # Y position: margin + footer + row offset
                # (row 0 is at bottom, above footer)
                y = margin + footer_h + r * (card_h + gutter)

                positions.append((x, y, card_w, card_h))

        # === Create and return CardLayout instance ===
        return cls(
            cols=cols,
            rows=rows,
            card_width=card_w,
            card_height=card_h,
            font_scale=font_scale,
            positions=positions,
            page_width=page_w,
            page_height=page_h,
            margin=margin,
            gutter=gutter,
            footer_height=footer_h,
        )

    def get_scaled_font_size(self, base_size: int) -> int:
        """
        Get font size scaled for this layout.

        Scales the base font size by the layout's font_scale factor,
        with a minimum of 6 points to ensure readability.

        PARAMETERS:
            base_size: Base font size in points (e.g., 12 for titles)

        RETURNS:
            Scaled font size, minimum 6 points

        EXAMPLE:
            layout = CardLayout.from_cards_per_page(12)  # font_scale = 0.6
            title_size = layout.get_scaled_font_size(12)  # Returns 7 (12 * 0.6 ≈ 7)
        """
        return max(6, int(base_size * self.font_scale))

    def get_scaled_leading(self, base_leading: int) -> int:
        """
        Get line leading (spacing) scaled for this layout.

        Leading is the vertical distance between baselines of text.
        This scales it proportionally with font size.

        PARAMETERS:
            base_leading: Base leading in points (e.g., 12 for body text)

        RETURNS:
            Scaled leading, minimum 8 points

        EXAMPLE:
            layout = CardLayout.from_cards_per_page(8)
            leading = layout.get_scaled_leading(12)  # Returns scaled value
        """
        return max(8, int(base_leading * self.font_scale))


# =============================================================================
# DEFAULT LAYOUT HELPER
# =============================================================================

def get_default_layout() -> CardLayout:
    """
    Get the default 4-card layout.

    This is a convenience function for getting a standard layout
    with default settings (letter paper, 4 cards, 0.5" margins).

    RETURNS:
        CardLayout configured for 4 cards on letter paper

    USAGE:
        layout = get_default_layout()
        pdf_bytes = render_pdf(content, layout)
    """
    return CardLayout.from_cards_per_page(4)
