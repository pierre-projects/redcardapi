"""Print sheet geometry: card sizes and positions for each layout."""

from dataclasses import dataclass, field

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch

# The single source of truth for valid layouts (API validation, /api/config).
# Grid mode: cards per page -> (columns, rows); fronts on page 1, backs on page 2.
GRID_LAYOUTS: dict[int, tuple[int, int]] = {4: (2, 2), 6: (2, 3), 8: (2, 4), 12: (3, 4)}
# Fold mode: rows per page, each row = front | back side by side.
FOLD_ROWS: tuple[int, ...] = (4, 5, 6)

MODE_GRID = "grid"
MODE_FOLD = "fold"
# "legacy" was the original name of grid mode; still accepted from clients.
MODE_ALIASES = {"legacy": MODE_GRID, MODE_GRID: MODE_GRID, MODE_FOLD: MODE_FOLD}

FOLD_HEADER_INCHES = 0.8

# (x, y, width, height) of a card, in points from the page's bottom-left.
Rect = tuple[float, float, float, float]


def _page_size(name: str) -> tuple[float, float]:
    return A4 if name.lower() == "a4" else letter


def _font_scale(card_w: float, card_h: float, page_w: float, page_h: float,
                margin: float, gutter: float, footer_h: float) -> float:
    """Typography scale relative to a 4-up grid card, clamped to [0.6, 1]."""
    base_area = ((page_w - 2 * margin - gutter) / 2) * ((page_h - 2 * margin - gutter - footer_h) / 2)
    return max(0.6, min(1.0, (card_w * card_h / base_area) ** 0.5))


@dataclass
class CardLayout:
    mode: str
    cols: int
    rows: int
    card_width: float
    card_height: float
    font_scale: float
    page_width: float
    page_height: float
    margin: float
    gutter: float = 0.0
    footer_height: float = 0.0
    header_height: float = 0.0
    positions: list[Rect] = field(default_factory=list)

    @property
    def cards_per_page(self) -> int:
        return len(self.positions) if self.mode == MODE_GRID else self.rows

    @classmethod
    def grid(cls, count: int, page_size: str = "letter", margin_inches: float = 0.5,
             gutter_inches: float = 0.25, footer_height_inches: float = 0.55) -> "CardLayout":
        cols, rows = GRID_LAYOUTS[count]
        page_w, page_h = _page_size(page_size)
        margin, gutter, footer_h = margin_inches * inch, gutter_inches * inch, footer_height_inches * inch

        card_w = (page_w - 2 * margin - (cols - 1) * gutter) / cols
        card_h = (page_h - 2 * margin - (rows - 1) * gutter - footer_h) / rows
        positions = [
            (margin + c * (card_w + gutter), margin + footer_h + r * (card_h + gutter), card_w, card_h)
            for r in range(rows)
            for c in range(cols)
        ]
        return cls(
            mode=MODE_GRID, cols=cols, rows=rows, card_width=card_w, card_height=card_h,
            font_scale=_font_scale(card_w, card_h, page_w, page_h, margin, gutter, footer_h),
            page_width=page_w, page_height=page_h, margin=margin, gutter=gutter,
            footer_height=footer_h, positions=positions,
        )

    @classmethod
    def fold(cls, rows: int, page_size: str = "letter", margin_inches: float = 0.5,
             gutter_inches: float = 0.25, footer_height_inches: float = 0.55) -> "CardLayout":
        if rows not in FOLD_ROWS:
            raise KeyError(rows)
        page_w, page_h = _page_size(page_size)
        margin, header_h = margin_inches * inch, FOLD_HEADER_INCHES * inch

        card_w = (page_w - 2 * margin) / 2
        card_h = (page_h - 2 * margin - header_h) / rows
        # Positions alternate front, back for each row.
        positions = [
            rect
            for r in range(rows)
            for rect in ((margin, margin + r * card_h, card_w, card_h),
                         (margin + card_w, margin + r * card_h, card_w, card_h))
        ]
        # Scale against the grid reference card so both modes size text alike.
        scale = _font_scale(card_w, card_h, page_w, page_h, margin,
                            gutter_inches * inch, footer_height_inches * inch)
        return cls(
            mode=MODE_FOLD, cols=2, rows=rows, card_width=card_w, card_height=card_h,
            font_scale=scale, page_width=page_w, page_height=page_h, margin=margin,
            header_height=header_h, positions=positions,
        )
