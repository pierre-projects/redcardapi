"""Font management package for PDF rendering.

This package provides modular font selection based on language codes
and Unicode scripts. It maps languages to appropriate Noto Sans font
families and handles font registration with ReportLab.

Usage:
    from app.fonts import get_font_manager

    manager = get_font_manager()
    font_name = manager.pick("ar", bold=True)  # "NotoSansArabic-Bold"
    canvas.setFont(font_name, 12)
"""

from .script_detector import (
    Script,
    detect_script,
    is_rtl_script,
    is_rtl_language,
    get_languages_for_script,
)
from .font_config import (
    FontFamily,
    FONT_FAMILIES,
    SCRIPT_TO_FONTS,
    FALLBACK_FONT_REGULAR,
    FALLBACK_FONT_BOLD,
    get_font_families,
    get_fonts_for_script,
)
from .font_manager import (
    FontManager,
    FontNotAvailableError,
    get_font_manager,
    reset_font_manager,
)

__all__ = [
    # Script detection
    "Script",
    "detect_script",
    "is_rtl_script",
    "is_rtl_language",
    "get_languages_for_script",
    # Font configuration
    "FontFamily",
    "FONT_FAMILIES",
    "SCRIPT_TO_FONTS",
    "FALLBACK_FONT_REGULAR",
    "FALLBACK_FONT_BOLD",
    "get_font_families",
    "get_fonts_for_script",
    # Font manager
    "FontManager",
    "FontNotAvailableError",
    "get_font_manager",
    "reset_font_manager",
]
