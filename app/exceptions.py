"""
Custom Exceptions for RedCardGenerator Application.

=============================================================================
MODULE OVERVIEW
=============================================================================

This module defines a hierarchy of custom exceptions used throughout the
application. Using custom exceptions provides:

1. SPECIFIC ERROR HANDLING - Catch exactly the errors you expect
2. RICH CONTEXT - Store relevant data (language code, file path, etc.)
3. HTTP MAPPING - Exception handlers in main.py map these to HTTP status codes
4. DEBUGGING - Clear error messages with context for troubleshooting

=============================================================================
EXCEPTION HIERARCHY
=============================================================================

    Exception (Python built-in)
         │
    RedCardError (base for all app errors)
         │
         ├── TranslationLoadError   -> HTTP 503 (startup failure)
         │       Raised during: Application startup
         │       Cause: Missing/invalid Translations.json
         │
         ├── LanguageNotFoundError  -> HTTP 404
         │       Raised by: GET /api/card/{code}, GET /api/render/{code}
         │       Cause: User requested non-existent language code
         │
         ├── PDFRenderError         -> HTTP 500
         │       Raised by: GET /api/render/{code}
         │       Cause: ReportLab failed to generate PDF
         │
         └── FontLoadError          -> HTTP 500
                 Raised by: FontManager during font registration
                 Cause: TTF file missing or corrupt

=============================================================================
HTTP STATUS CODE MAPPING (in main.py)
=============================================================================

    LanguageNotFoundError  -> 404 Not Found
    FontNotAvailableError  -> 400 Bad Request (from fonts module)
    PDFRenderError         -> 500 Internal Server Error
    RedCardError (catchall)-> 500 Internal Server Error

=============================================================================
USAGE EXAMPLES
=============================================================================

Raising exceptions:

    # Language lookup failed
    if not language:
        raise LanguageNotFoundError("xyz")

    # PDF generation failed
    try:
        pdf_bytes = render_pdf(...)
    except Exception as e:
        raise PDFRenderError(str(e), language_code="es")

Catching exceptions:

    try:
        store.load()
    except TranslationLoadError as e:
        logger.error(f"Failed to load translations from {e.path}")
        sys.exit(1)

=============================================================================
"""


# =============================================================================
# BASE EXCEPTION
# =============================================================================

class RedCardError(Exception):
    """
    Base exception for all RedCardGenerator application errors.

    All custom exceptions in this application inherit from this class.
    This allows catching all app-specific errors with a single except clause:

        try:
            # ... application code ...
        except RedCardError as e:
            # Handle any application error
            logger.error(f"Application error: {e}")

    The main.py module has a catch-all handler for RedCardError that
    returns HTTP 500 for any unhandled application errors.
    """
    pass


# =============================================================================
# TRANSLATION ERRORS
# =============================================================================

class TranslationLoadError(RedCardError):
    """
    Raised when Translations.json fails to load or parse.

    This is a critical startup error - if translations can't be loaded,
    the application cannot serve any requests.

    ATTRIBUTES:
        path: Path to the translations file that failed to load

    CAUSES:
        - File doesn't exist at the configured path
        - File is not valid JSON
        - JSON structure doesn't match expected format
        - File permissions prevent reading

    RAISED BY:
        - main.py lifespan() during application startup
        - TranslationsStore.load()

    HTTP RESPONSE:
        This error occurs during startup, so it prevents the server from
        starting rather than returning an HTTP response.

    EXAMPLE:
        raise TranslationLoadError("Invalid JSON structure", "/path/to/file.json")
        # -> "Invalid JSON structure: /path/to/file.json"
    """

    def __init__(self, message: str = "Failed to load translations", path: str = None):
        self.path = path
        super().__init__(f"{message}: {path}" if path else message)


# =============================================================================
# LANGUAGE ERRORS
# =============================================================================

class LanguageNotFoundError(RedCardError):
    """
    Raised when a requested language code does not exist.

    This is a user error - they requested a language that isn't in our
    translations database.

    ATTRIBUTES:
        code: The language code that was requested but not found

    RAISED BY:
        - GET /api/card/{code} when language doesn't exist
        - GET /api/render/{code} when language doesn't exist

    HTTP RESPONSE:
        404 Not Found with JSON body:
        {
            "detail": "Language not found: xyz",
            "code": "xyz"
        }

    EXAMPLE:
        if not store.get_language("xyz"):
            raise LanguageNotFoundError("xyz")
    """

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Language not found: {code}")


# =============================================================================
# PDF ERRORS
# =============================================================================

class PDFRenderError(RedCardError):
    """
    Raised when PDF generation fails.

    This is typically an internal error caused by issues with the
    ReportLab PDF library or invalid data passed to the renderer.

    ATTRIBUTES:
        language_code: The language code being rendered when error occurred

    CAUSES:
        - ReportLab internal error
        - Invalid or corrupt font files
        - Out of memory for large PDFs
        - Invalid content data

    RAISED BY:
        - GET /api/render/{code} when render_print_sheet_pdf() fails
        - pdf_renderer.py functions

    HTTP RESPONSE:
        500 Internal Server Error with JSON body:
        {
            "detail": "Error message for language 'es'"
        }

    NOTE:
        FontNotAvailableError (from fonts module) is handled separately
        and returns 400 instead of 500, since it's a user-facing issue
        (requested language doesn't have fonts installed).

    EXAMPLE:
        try:
            pdf_bytes = render_print_sheet_pdf(payload, layout)
        except Exception as e:
            raise PDFRenderError(str(e), language_code="es")
    """

    def __init__(self, message: str = "Failed to render PDF", language_code: str = None):
        self.language_code = language_code
        detail = f" for language '{language_code}'" if language_code else ""
        super().__init__(f"{message}{detail}")


# =============================================================================
# FONT ERRORS
# =============================================================================

class FontLoadError(RedCardError):
    """
    Raised when font files cannot be loaded.

    This error occurs when attempting to register a TTF font file with
    ReportLab's pdfmetrics system.

    ATTRIBUTES:
        font_name: The internal name of the font being loaded
        font_path: Path to the TTF file (if known)

    CAUSES:
        - TTF file doesn't exist
        - TTF file is corrupt or invalid
        - File permissions prevent reading
        - ReportLab doesn't support the font format

    RAISED BY:
        - FontManager._register_font_family() in font_manager.py
        - FontManager initialization

    DISTINCTION FROM FontNotAvailableError:
        - FontLoadError: Font file exists but couldn't be loaded (internal error)
        - FontNotAvailableError: Font for a script isn't installed (user-facing)

    EXAMPLE:
        try:
            pdfmetrics.registerFont(TTFont(name, path))
        except Exception as e:
            raise FontLoadError(name, path)
    """

    def __init__(self, font_name: str, font_path: str = None):
        self.font_name = font_name
        self.font_path = font_path
        path_info = f" from {font_path}" if font_path else ""
        super().__init__(f"Failed to load font '{font_name}'{path_info}")
