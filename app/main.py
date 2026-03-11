"""
FastAPI application for KnowYourRightAutoLanguageCards API.

=============================================================================
APPLICATION FLOW OVERVIEW
=============================================================================

This is the main entry point for the Red Card Generator backend API.
The application follows this flow:

1. STARTUP PHASE (lifespan context manager):
   - Initialize the TranslationsStore with language data from JSON
   - Load all translations into memory
   - Log startup status

2. REQUEST HANDLING PHASE:
   - /api/health      -> Check if service is running and translations loaded
   - /api/config      -> Return valid layout options and defaults
   - /api/languages   -> List all languages with font support status
   - /api/card/{code} -> Get card content for a specific language
   - /api/render/{code} -> Generate PDF for a specific language

3. SHUTDOWN PHASE:
   - Clean up resources
   - Log shutdown status

=============================================================================
DEPENDENCIES FLOW
=============================================================================

main.py
    ├── config.py           -> Application settings (paths, defaults)
    ├── translations_store.py -> Load/parse translations JSON
    ├── schemas.py          -> Pydantic models for request/response validation
    ├── pdf_renderer.py     -> Generate PDF bytes from card data
    ├── layout.py           -> Calculate card positions on page
    ├── back_content.py     -> Get English back content
    ├── fonts/              -> Font management for multi-language support
    │   ├── font_manager.py -> Register and pick fonts
    │   └── script_detector.py -> Detect Unicode script from language code
    └── exceptions.py       -> Custom error classes

=============================================================================
"""

import re
import unicodedata
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from typing import List

from .config import TRANSLATIONS_JSON_PATH, settings
from .translations_store import TranslationsStore
from .schemas import LanguageItem, CardPayload
from .pdf_renderer import render_print_sheet_pdf, render_fold_sheet_pdf
from .layout import CardLayout
from .back_content import get_back_content
from .logging_config import get_logger
from .exceptions import (
    RedCardError,
    TranslationLoadError,
    LanguageNotFoundError,
    PDFRenderError,
)
from .fonts import FontNotAvailableError, get_font_manager
from .fonts.script_detector import detect_script

# Initialize logger for this module
logger = get_logger("main")

# =============================================================================
# GLOBAL STATE
# =============================================================================
# The translations store is initialized once at startup and shared across
# all requests. This avoids re-loading the JSON file on every request.
store: TranslationsStore = None


def _slugify_filename_part(text: str, fallback: str = "unknown") -> str:
    """Convert free text into a filesystem-safe ASCII slug."""
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or fallback


# =============================================================================
# APPLICATION LIFESPAN (STARTUP/SHUTDOWN)
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup/shutdown events.

    This is the modern FastAPI way to handle startup/shutdown (replaces
    @app.on_event decorators which are deprecated).

    STARTUP FLOW:
    1. Create TranslationsStore instance with path to JSON file
    2. Call store.load() to parse and normalize the translations
    3. Log the number of languages loaded
    4. If any error occurs, raise TranslationLoadError (app won't start)

    SHUTDOWN FLOW:
    1. Log shutdown message
    2. Any cleanup would go here (currently none needed)
    """
    global store

    # === STARTUP ===
    logger.info("Starting KnowYourRightAutoLanguageCards API...")
    try:
        # Create store instance with path to translations file
        store = TranslationsStore(TRANSLATIONS_JSON_PATH)

        # Load and parse the JSON file (this normalizes all language entries)
        store.load()

        # Log success with count
        language_count = len(store.list_languages())
        logger.info(f"Loaded {language_count} languages from {TRANSLATIONS_JSON_PATH}")

    except FileNotFoundError as e:
        # Translations.json doesn't exist at the expected path
        logger.error(f"Translations file not found: {TRANSLATIONS_JSON_PATH}")
        raise TranslationLoadError("Translations file not found", str(TRANSLATIONS_JSON_PATH))

    except ValueError as e:
        # JSON parsing failed or invalid structure
        logger.error(f"Failed to parse translations: {e}")
        raise TranslationLoadError(f"Invalid translations format: {e}", str(TRANSLATIONS_JSON_PATH))

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error loading translations: {e}")
        raise TranslationLoadError(str(e), str(TRANSLATIONS_JSON_PATH))

    # Yield control - application runs while this is suspended
    yield

    # === SHUTDOWN ===
    logger.info("Shutting down KnowYourRightAutoLanguageCards API...")


# =============================================================================
# FASTAPI APPLICATION INSTANCE
# =============================================================================
app = FastAPI(
    title="KnowYourRightAutoLanguageCards API",
    description="Generate print-ready Know Your Rights cards in multiple languages",
    version="1.0.0",
    lifespan=lifespan,  # Register our lifespan handler
)


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================
# These handlers convert our custom exceptions into proper HTTP responses.
# FastAPI will automatically call these when the corresponding exception is raised.

@app.exception_handler(LanguageNotFoundError)
async def language_not_found_handler(request: Request, exc: LanguageNotFoundError):
    """
    Handle requests for non-existent language codes.

    Returns 404 with the requested language code in the response
    so the frontend can display a meaningful error message.
    """
    logger.warning(f"Language not found: {exc.code}")
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc), "code": exc.code},
    )


@app.exception_handler(PDFRenderError)
async def pdf_render_error_handler(request: Request, exc: PDFRenderError):
    """
    Handle errors that occur during PDF generation.

    Returns 500 as this is typically an internal error (e.g., ReportLab
    failed to generate the PDF for some reason).
    """
    logger.error(f"PDF render error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.exception_handler(FontNotAvailableError)
async def font_not_available_handler(request: Request, exc: FontNotAvailableError):
    """
    Handle requests for languages that don't have fonts installed.

    Returns 400 (bad request) with detailed information about which
    script is missing, allowing the frontend to display a helpful message.

    Response includes:
    - detail: Human-readable error message
    - error_type: "font_not_available" for frontend identification
    - script: The Unicode script name (e.g., "KOREAN", "CJK_SIMPLIFIED")
    - language: The requested language code
    """
    logger.error(f"Font not available for {exc.script.name} script (language: {exc.lang_code})")
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "error_type": "font_not_available",
            "script": exc.script.name,
            "language": exc.lang_code,
        },
    )


@app.exception_handler(RedCardError)
async def redcard_error_handler(request: Request, exc: RedCardError):
    """
    Catch-all handler for any RedCardError that isn't handled by
    more specific handlers above.

    Returns 500 as these are typically unexpected application errors.
    """
    logger.error(f"Application error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


# =============================================================================
# CORS MIDDLEWARE
# =============================================================================
# Enable Cross-Origin Resource Sharing so the frontend (running on a different
# port during development) can make requests to this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # List of allowed origins from config
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/api/health")
def health():
    """
    Health check endpoint for monitoring and load balancers.

    FLOW:
    1. Check if store is initialized and has languages
    2. Return status and count

    RETURNS:
    {
        "ok": true/false,           # Whether the service is healthy
        "languages_loaded": number  # Count of loaded languages
    }

    USE CASES:
    - Kubernetes liveness/readiness probes
    - Load balancer health checks
    - Frontend connectivity testing
    """
    is_loaded = store is not None and len(store.list_languages()) > 0
    return {
        "ok": is_loaded,
        "languages_loaded": len(store.list_languages()) if store else 0,
    }


@app.get("/api/config")
def get_config():
    """
    Get available configuration options for the frontend.

    FLOW:
    1. Read settings from config module
    2. Return as JSON object

    RETURNS:
    {
        "valid_layouts": [4, 6, 8, 12],  # Valid cards-per-page options
        "default_cards_per_page": 4,      # Default layout
        "page_size": "letter"             # Page size (letter or a4)
    }

    USE CASES:
    - Frontend populates layout dropdown with valid options
    - Frontend can use defaults when user hasn't selected
    """
    return {
        "valid_layouts": settings.get_valid_layouts(),
        "default_cards_per_page": settings.default_cards_per_page,
        "page_size": settings.page_size,
        "render_modes": ["legacy", "fold"],
        "fold_layouts": settings.get_valid_fold_layouts(),
        "default_fold_cards_per_page": settings.default_fold_cards_per_page,
    }


@app.get("/api/languages", response_model=List[LanguageItem])
def list_languages():
    """
    List all available languages with their font support status.

    FLOW:
    1. Check if store is initialized (return 503 if not)
    2. Get all languages from store
    3. For each language:
       a. Detect its Unicode script (Latin, Arabic, CJK, etc.)
       b. Check if we have fonts installed for that script
       c. Add fontSupported field to response
    4. Return list of LanguageItem objects

    RETURNS:
    [
        {
            "code": "en",
            "name": "English",
            "rtl": false,
            "official": true,
            "fontSupported": true  # Whether PDF can be generated
        },
        ...
    ]

    USE CASES:
    - Frontend populates language dropdown
    - Frontend shows warning icon for unsupported languages
    - Frontend can filter/sort languages
    """
    # Ensure service is ready
    if store is None:
        logger.error("Store not initialized")
        raise HTTPException(status_code=503, detail="Service not ready")

    # Get all languages from the store
    langs = store.list_languages()
    logger.debug(f"Returning {len(langs)} languages")

    # Get font manager singleton to check font availability
    font_manager = get_font_manager()

    # Build response with font support status for each language
    result = []
    for lang in langs:
        # Detect which Unicode script this language uses
        # e.g., "ko" -> KOREAN, "ar" -> ARABIC, "en" -> LATIN
        script = detect_script(lang["code"])

        # Check if we have fonts installed for this script
        font_supported = font_manager.is_script_supported(script)

        # Create response item with font support flag
        result.append(LanguageItem(
            **lang,  # Spread existing fields (code, name, rtl, official, source)
            fontSupported=font_supported
        ))

    return result


@app.get("/api/card/{code}", response_model=CardPayload)
def get_card_payload(code: str):
    """
    Get card content for a specific language (for preview).

    FLOW:
    1. Check if store is initialized (return 503 if not)
    2. Look up language by code (case-insensitive)
    3. If not found, raise LanguageNotFoundError (-> 404)
    4. Return card payload with front content

    PARAMETERS:
    - code: Language code (e.g., "en", "es", "zh-CN")

    RETURNS:
    {
        "code": "es",
        "name": "Spanish",
        "rtl": false,
        "official": true,
        "front": {
            "header": "CONOZCA SUS DERECHOS",
            "bullets": ["Point 1", "Point 2", ...]
        }
    }

    USE CASES:
    - Frontend displays card preview when language selected
    - Preview before generating PDF
    """
    # Ensure service is ready
    if store is None:
        logger.error("Store not initialized")
        raise HTTPException(status_code=503, detail="Service not ready")

    # Look up language (case-insensitive, returns None if not found)
    item = store.get_language(code)
    if not item:
        raise LanguageNotFoundError(code)

    logger.debug(f"Returning card payload for language: {code}")

    # Return card payload (back content is only included in PDF, not preview)
    return CardPayload(
        code=item["code"],
        name=item["name"],
        rtl=item["rtl"],
        official=item.get("official", True),
        front=item.get("front", {}),
        source=item.get("source"),
    )


@app.get("/api/render/{code}")
def render_pdf(
    code: str,
    cards_per_page: int = Query(
        default=None,
        ge=4,
        le=12,
        description="Number of cards per page. Legacy: 4, 6, 8, or 12. Fold: 4, 5, or 6 rows."
    ),
    mode: str = Query(
        default="legacy",
        description='Render mode: "legacy" (2-page front/back) or "fold" (single-page front|back side-by-side).',
    ),
):
    """
    Generate and download a printable PDF for the specified language.

    Supports two render modes:
    - legacy (default): Two-page PDF. Page 1 = front grid, Page 2 = back grid.
    - fold: Single-page official fold format. Each row has front (left) and
      back (right) side-by-side, max 2 columns.

    PARAMETERS:
    - code: Language code (e.g., "en", "es", "zh-CN")
    - cards_per_page: Layout option. Legacy: 4, 6, 8, 12. Fold: 4, 5, 6 (rows).
    - mode: "legacy" or "fold"

    RETURNS:
    - Binary PDF file as attachment

    ERRORS:
    - 400: Invalid mode or font not available
    - 404: Language code not found
    - 500: PDF generation failed
    - 503: Service not ready
    """
    # === VALIDATE INPUTS ===

    if store is None:
        logger.error("Store not initialized")
        raise HTTPException(status_code=503, detail="Service not ready")

    if mode not in ("legacy", "fold"):
        raise HTTPException(
            status_code=400,
            detail=f'Invalid mode "{mode}". Must be "legacy" or "fold".',
        )

    item = store.get_language(code)
    if not item:
        raise LanguageNotFoundError(code)

    # === CREATE LAYOUT ===

    if mode == "fold":
        if cards_per_page is None:
            cards_per_page = settings.default_fold_cards_per_page
        else:
            cards_per_page = settings.validate_fold_rows(cards_per_page)

        logger.info(
            f"Rendering FOLD PDF for {code}: {cards_per_page} rows, "
            f"page_size={settings.page_size}"
        )
        layout = CardLayout.from_fold_rows(
            rows=cards_per_page,
            page_size=settings.page_size,
            margin_inches=settings.margin_inches,
        )
    else:
        if cards_per_page is None:
            cards_per_page = settings.default_cards_per_page
        else:
            cards_per_page = settings.validate_cards_per_page(cards_per_page)

        logger.info(
            f"Rendering LEGACY PDF for {code}: {cards_per_page} cards/page, "
            f"page_size={settings.page_size}"
        )
        layout = CardLayout.from_cards_per_page(
            count=cards_per_page,
            page_size=settings.page_size,
            margin_inches=settings.margin_inches,
            gutter_inches=settings.gutter_inches,
            footer_height_inches=settings.footer_height_inches,
        )

    # === RENDER PDF ===

    payload = {
        "code": item["code"],
        "name": item["name"],
        "rtl": item["rtl"],
        "official": True,
        "source": item.get("source"),
        "front": item.get("front", {}),
        "back": get_back_content(item["code"]),
    }

    try:
        if mode == "fold":
            pdf_bytes = render_fold_sheet_pdf(payload=payload, layout=layout)
        else:
            pdf_bytes = render_print_sheet_pdf(payload=payload, layout=layout)
    except FontNotAvailableError:
        raise
    except Exception as e:
        logger.error(f"Failed to render PDF for {code} (mode={mode}): {e}")
        raise PDFRenderError(str(e), code)

    # === RETURN PDF ===

    mode_suffix = "-fold" if mode == "fold" else ""
    lang_code = item["code"]
    lang_name_slug = _slugify_filename_part(item.get("name", ""), fallback=lang_code.lower())
    filename = (
        f"know-your-rights-{lang_code}-{lang_name_slug}-{cards_per_page}up{mode_suffix}.pdf"
    )
    logger.info(f"Successfully rendered PDF: {filename}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
