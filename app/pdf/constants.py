"""Shared typography/scaling constants for PDF rendering."""

# Base sizes for typography. These are scaled by CardLayout.font_scale
# based on the number of cards per page (more cards = smaller text).
BASE_TITLE_SIZE = 12   # Header/title font size (points)
BASE_BODY_SIZE = 10    # Body text font size (points)
BASE_LEADING = 12      # Line height (points)
BASE_FOOTER_SIZE = 9   # Footer text size (points)

# Adaptive scaling limits.
MIN_FONT_SCALE_FACTOR = 0.5
MIN_ABSOLUTE_FONT_SIZE = 6
SCALE_STEP = 0.05

