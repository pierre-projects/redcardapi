"""Font helpers for PDF rendering modules."""

from typing import Optional, Dict

from ..fonts import get_font_manager


def get_font(lang_code: Optional[str] = None, bold: bool = False) -> str:
    """Get the best available font for a language/script."""
    return get_font_manager().pick(lang_code, bold)


def register_fonts() -> Dict[str, bool]:
    """
    Explicitly trigger font registration.

    Kept for compatibility with dev tooling that calls `_register_fonts()`.
    """
    return get_font_manager().register_all()

