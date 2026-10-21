"""Right-to-left text (Arabic script, Hebrew) for ReportLab.

ReportLab draws glyphs left to right in the order given, so RTL text needs
two steps: join Arabic letters into their contextual forms (reshape), then
reorder each *line* into visual order. Reordering must happen after line
wrapping; reordering a whole paragraph first would put the end of the
sentence on the first line.
"""

import arabic_reshaper
from bidi.algorithm import get_display


def reshape(text: str) -> str:
    """Contextual Arabic letter forms, still in logical order."""
    return arabic_reshaper.reshape(text) if text else text


def to_visual(line: str) -> str:
    """Visual (left-to-right drawing) order for one already-wrapped line."""
    return get_display(line, base_dir="R") if line else line
