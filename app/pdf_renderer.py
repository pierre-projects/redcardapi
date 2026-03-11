"""
Compatibility facade for PDF rendering.

This module preserves historical imports while delegating implementation to
the modular `app.pdf` package.
"""

from .pdf.back import draw_back as _draw_back
from .pdf.fonts import register_fonts as _register_fonts
from .pdf.front import draw_front as _draw_front
from .pdf.renderer import render_print_sheet_pdf, render_fold_sheet_pdf

__all__ = [
    "render_print_sheet_pdf",
    "render_fold_sheet_pdf",
    "_draw_front",
    "_draw_back",
    "_register_fonts",
]

