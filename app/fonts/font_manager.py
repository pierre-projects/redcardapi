"""
Font Manager for PDF Rendering.

=============================================================================
MODULE OVERVIEW
=============================================================================

This module manages font registration, selection, and coverage for PDF
generation. It provides a centralized FontManager that:

1. Registers TrueType (.ttf) fonts with ReportLab
2. Selects the appropriate font for each language/script
3. Reports font coverage status
4. Raises errors when required fonts are missing

=============================================================================
FONT SELECTION FLOW
=============================================================================

When rendering PDF text, the font is selected as follows:

1. get_font_manager().pick("ar", bold=True)
   ↓
2. detect_script("ar")  →  Script.ARABIC
   ↓
3. SCRIPT_TO_FONTS[ARABIC] = ["NotoSansArabic", "NotoSans"]
   ↓
4. Check if "NotoSansArabic-Bold" is registered
   ↓
5. If yes: return "NotoSansArabic-Bold"
   If no:  try next font or raise FontNotAvailableError

=============================================================================
FONT REGISTRATION
=============================================================================

Fonts are registered with ReportLab using pdfmetrics.registerFont().
Once registered, font names can be used with canvas.setFont().

Registration happens:
- Lazily on first call to get_font_manager()
- From .ttf files in the assets/fonts directory
- For both regular and bold variants

=============================================================================
SINGLETON PATTERN
=============================================================================

The FontManager uses a module-level singleton accessed via get_font_manager().
This ensures:
- Fonts are only registered once
- Consistent state across the application
- Lazy initialization (fonts loaded on first use)

=============================================================================
"""

from pathlib import Path
from typing import Dict, Optional, Set

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from ..logging_config import get_logger
from ..exceptions import FontLoadError
from .script_detector import Script, detect_script
from .font_config import (
    FONT_FAMILIES,
    SCRIPT_TO_FONTS,
    FALLBACK_FONT_REGULAR,
    FALLBACK_FONT_BOLD,
    FontFamily,
)

logger = get_logger("fonts")


# =============================================================================
# EXCEPTIONS
# =============================================================================

class FontNotAvailableError(FontLoadError):
    """
    Raised when no font is available for a required script.

    This exception is raised by FontManager.pick() when trying to render
    text in a script (e.g., Korean) without having the required font
    installed (e.g., NotoSansKR).

    ATTRIBUTES:
        script: The Script enum value that couldn't be rendered
        lang_code: The language code that was requested

    HANDLING:
        This exception should bubble up to the API layer, where it's
        converted to a 400 response with details about the missing font.
    """

    def __init__(self, script: Script, lang_code: str):
        self.script = script
        self.lang_code = lang_code
        super().__init__(
            f"No font available for {script.name} script (language: {lang_code}). "
            f"Please install the required font files."
        )


# =============================================================================
# FONT MANAGER CLASS
# =============================================================================

class FontManager:
    """
    Manages font registration and selection for PDF rendering.

    This class handles:
    - Discovering font files in the fonts directory
    - Registering fonts with ReportLab's pdfmetrics
    - Selecting the best font for each language/script
    - Tracking which scripts have font support

    USAGE:
        # Get the singleton instance (auto-registers fonts)
        manager = get_font_manager()

        # Select font for a language
        font_name = manager.pick("ar", bold=True)  # "NotoSansArabic-Bold"
        canvas.setFont(font_name, 12)

        # Check if a script is supported
        if manager.is_script_supported(Script.KOREAN):
            render_korean_text()
        else:
            show_warning()

    FONT NAMING CONVENTION:
        - Regular: "NotoSans", "NotoSansArabic", "NotoSansJP"
        - Bold: "NotoSans-Bold", "NotoSansArabic-Bold", "NotoSansJP-Bold"
    """

    def __init__(self, fonts_dir: Path):
        """
        Initialize font manager with path to fonts directory.

        Does NOT register fonts automatically - call register_all() first.

        PARAMETERS:
            fonts_dir: Path to directory containing .ttf font files

        EXAMPLE:
            manager = FontManager(Path("Backend/assets/fonts"))
            manager.register_all()
        """
        self.fonts_dir = fonts_dir

        # Track registered fonts: font_name -> success (True/False)
        self._registered: Dict[str, bool] = {}

        # Track which font families have at least one variant loaded
        self._families_loaded: Set[str] = set()

    def register_all(self) -> Dict[str, bool]:
        """
        Register all available fonts from the fonts directory.

        This method iterates through all configured font families (from
        font_config.py) and attempts to register both regular and bold
        variants.

        FLOW:
        1. For each font family in FONT_FAMILIES:
           a. Try to register regular font (e.g., "NotoSans")
           b. Try to register bold font (e.g., "NotoSans-Bold")
           c. Track success/failure
        2. Log coverage report

        RETURNS:
            Dict mapping font names to registration success (True/False)

        EXAMPLE:
            results = manager.register_all()
            # results = {"NotoSans": True, "NotoSans-Bold": True, ...}
        """
        results = {}

        for family_name, family in FONT_FAMILIES.items():
            # Register regular weight
            regular_success = self._register_font(
                family_name,           # e.g., "NotoSans"
                family.regular_file    # e.g., "NotoSans-Regular.ttf"
            )

            # Register bold weight
            bold_success = self._register_font(
                f"{family_name}-Bold",  # e.g., "NotoSans-Bold"
                family.bold_file        # e.g., "NotoSans-Bold.ttf"
            )

            results[family_name] = regular_success
            results[f"{family_name}-Bold"] = bold_success

            # Track if this family has any usable fonts
            if regular_success or bold_success:
                self._families_loaded.add(family_name)

        # Log summary of font coverage
        self._log_coverage_report()

        return results

    def _register_font(self, font_name: str, filename: str) -> bool:
        """
        Register a single font file with ReportLab.

        FLOW:
        1. Check if already registered (avoid duplicate registration)
        2. Check if font file exists
        3. Register with pdfmetrics.registerFont()
        4. Cache result

        PARAMETERS:
            font_name: Name to register the font as (used with setFont)
            filename: Font filename in fonts_dir (e.g., "NotoSans-Regular.ttf")

        RETURNS:
            True if registration succeeded, False otherwise

        SIDE EFFECTS:
            - Registers font with ReportLab's pdfmetrics module
            - Updates self._registered cache
            - Logs success/failure
        """
        # Check if already attempted registration
        if font_name in self._registered:
            return self._registered[font_name]

        # Build full path to font file
        font_path = self.fonts_dir / filename

        # Check if file exists
        if not font_path.exists():
            logger.debug(f"Font file not found: {font_path}")
            self._registered[font_name] = False
            return False

        # Attempt registration
        try:
            # TTFont loads the font file and registers it with ReportLab
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
            self._registered[font_name] = True
            logger.info(f"Registered font: {font_name}")
            return True

        except Exception as e:
            # Font file might be corrupted or in wrong format
            logger.warning(f"Failed to register font '{font_name}': {e}")
            self._registered[font_name] = False
            return False

    def pick(self, lang_code: Optional[str] = None, bold: bool = False) -> str:
        """
        Select the best available font for a language.

        This is the main font selection method. It determines which
        script the language uses, then finds an available font for
        that script.

        FLOW:
        1. Detect script for language code (e.g., "ar" → ARABIC)
        2. Get list of candidate fonts for that script
        3. Find first registered candidate
        4. Raise error if no font available

        PARAMETERS:
            lang_code: ISO language code (e.g., 'ar', 'zh-CN', 'en')
                       If None or empty, defaults to English ("en")
            bold: Whether to return bold variant of font

        RETURNS:
            Font name string for use with canvas.setFont()
            Examples: "NotoSans", "NotoSansArabic-Bold", "NotoSansJP"

        RAISES:
            FontNotAvailableError: If no font is available for the
                language's script. This should result in a 400 error
                being returned to the client.

        EXAMPLE:
            font = manager.pick("ar", bold=True)
            # Returns "NotoSansArabic-Bold" if available
            # Raises FontNotAvailableError if not
        """
        # Detect which Unicode script this language uses
        script = detect_script(lang_code or "en")

        # Get list of fonts that support this script (in priority order)
        candidates = SCRIPT_TO_FONTS.get(script, ["NotoSans"])

        # Find first available font
        for family_name in candidates:
            font_name = f"{family_name}-Bold" if bold else family_name
            if self._registered.get(font_name):
                return font_name

        # No font available for this script - raise error
        raise FontNotAvailableError(script, lang_code or "en")

    def pick_with_fallback(self, lang_code: Optional[str] = None, bold: bool = False) -> str:
        """
        Select font with system fallback (never raises).

        Unlike pick(), this method falls back to Helvetica if no
        appropriate font is available. Use this for non-critical text
        where using a system font is acceptable.

        WARNING: Helvetica does not support non-Latin scripts!
        Text in Arabic, Chinese, etc. will render as boxes or blanks.

        PARAMETERS:
            lang_code: ISO language code
            bold: Whether to return bold variant

        RETURNS:
            Font name string (may be "Helvetica" or "Helvetica-Bold"
            if no better option is available)

        EXAMPLE:
            # Safe for footer text (always English)
            font = manager.pick_with_fallback("en")
        """
        try:
            return self.pick(lang_code, bold)
        except FontNotAvailableError:
            return FALLBACK_FONT_BOLD if bold else FALLBACK_FONT_REGULAR

    def is_available(self, font_name: str) -> bool:
        """
        Check if a specific font is registered.

        PARAMETERS:
            font_name: Exact font name (e.g., "NotoSansArabic-Bold")

        RETURNS:
            True if font is registered and available
        """
        return self._registered.get(font_name, False)

    def is_script_supported(self, script: Script) -> bool:
        """
        Check if we have fonts available for a script.

        This is used by the /api/languages endpoint to determine
        the fontSupported field for each language.

        PARAMETERS:
            script: Script enum value (e.g., Script.ARABIC, Script.KOREAN)

        RETURNS:
            True if at least one font is available for this script

        EXAMPLE:
            if manager.is_script_supported(Script.KOREAN):
                lang["fontSupported"] = True
        """
        candidates = SCRIPT_TO_FONTS.get(script, [])
        return any(
            self._registered.get(name) or self._registered.get(f"{name}-Bold")
            for name in candidates
        )

    def get_coverage_report(self) -> Dict[str, dict]:
        """
        Get a detailed report of font coverage by script.

        This is useful for debugging and monitoring which scripts
        are supported by the current font installation.

        RETURNS:
            Dict with script names as keys and coverage info as values:
            {
                "LATIN": {
                    "supported": True,
                    "fonts": ["NotoSans"],
                    "required_fonts": ["NotoSans"]
                },
                "KOREAN": {
                    "supported": False,
                    "fonts": [],
                    "required_fonts": ["NotoSansKR"]
                },
                ...
            }
        """
        report = {}

        for script in Script:
            candidates = SCRIPT_TO_FONTS.get(script, ["NotoSans"])

            # Find which candidate fonts are actually available
            available_fonts = [
                name for name in candidates
                if self._registered.get(name) or self._registered.get(f"{name}-Bold")
            ]

            report[script.name] = {
                "supported": len(available_fonts) > 0,
                "fonts": available_fonts,
                "required_fonts": candidates,
            }

        return report

    def _log_coverage_report(self) -> None:
        """
        Log a summary of font coverage.

        Called after register_all() to provide visibility into
        which scripts are supported.

        LOGS:
        - INFO: Summary count (e.g., "17/20 scripts supported")
        - WARNING: List of unsupported scripts
        - DEBUG: Detailed per-script coverage
        """
        report = self.get_coverage_report()

        # Count supported vs unsupported
        supported = [name for name, info in report.items() if info["supported"]]
        unsupported = [name for name, info in report.items() if not info["supported"]]

        # Log summary
        logger.info(f"Font coverage: {len(supported)}/{len(report)} scripts supported")

        # Warn about missing fonts
        if unsupported:
            logger.warning(f"Missing fonts for scripts: {', '.join(unsupported)}")

        # Log detailed coverage at debug level
        for script_name, info in report.items():
            if info["supported"]:
                logger.debug(f"  {script_name}: {info['fonts']}")
            else:
                logger.debug(f"  {script_name}: MISSING (need {info['required_fonts']})")


# =============================================================================
# SINGLETON MANAGEMENT
# =============================================================================
# The font manager uses a singleton pattern to ensure fonts are only
# registered once and to provide consistent state across the application.

# Module-level singleton instance
_font_manager: Optional[FontManager] = None


def get_font_manager() -> FontManager:
    """
    Get the global FontManager singleton instance.

    The manager is initialized lazily on first call. This includes:
    - Creating the FontManager with the fonts directory
    - Calling register_all() to register available fonts

    This singleton pattern ensures:
    - Fonts are only registered once (expensive operation)
    - Same state is shared across all PDF rendering
    - Lazy loading (doesn't slow down startup if fonts not needed)

    RETURNS:
        The global FontManager instance

    USAGE:
        manager = get_font_manager()
        font = manager.pick("ar", bold=True)
    """
    global _font_manager

    if _font_manager is None:
        # Import here to avoid circular dependency
        from ..config import settings

        # Create and initialize the singleton
        _font_manager = FontManager(settings.fonts_dir)
        _font_manager.register_all()

    return _font_manager


def reset_font_manager() -> None:
    """
    Reset the global FontManager singleton.

    This is primarily used for testing to ensure a clean state
    between tests.

    CAUTION:
        After calling this, the next call to get_font_manager()
        will create a new instance and re-register all fonts.
    """
    global _font_manager
    _font_manager = None
