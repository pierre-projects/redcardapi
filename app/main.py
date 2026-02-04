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

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from typing import List

from .config import TRANSLATIONS_JSON_PATH, settings
from .translations_store import TranslationsStore
from .schemas import LanguageItem, CardPayload
from .pdf_renderer import render_print_sheet_pdf
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
            **lang,  # Spread existing fields (code, name, rtl, official)
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
    )


@app.get("/api/render/{code}")
def render_pdf(
    code: str,
    cards_per_page: int = Query(
        default=None,
        ge=4,
        le=12,
        description="Number of cards per page (4, 6, 8, or 12). Defaults to 4."
    ),
):
    """
    Generate and download a printable PDF for the specified language.

    This is the main PDF generation endpoint. It creates a two-page PDF:
    - Page 1: Front of cards (in the requested language)
    - Page 2: Back of cards (in English)

    FLOW:
    1. Validate inputs:
       a. Check if store is initialized (return 503 if not)
       b. Look up language by code (return 404 if not found)
       c. Validate/default cards_per_page parameter

    2. Create layout:
       a. Calculate card positions based on cards_per_page
       b. Account for margins, gutters, and footer space

    3. Render PDF:
       a. Build payload with front content (translated) + back content (English)
       b. Call pdf_renderer.render_print_sheet_pdf()
       c. If FontNotAvailableError, let exception handler return 400
       d. If other error, wrap in PDFRenderError and return 500

    4. Return PDF:
       a. Set Content-Type to application/pdf
       b. Set Content-Disposition for download filename
       c. Return PDF bytes

    PARAMETERS:
    - code: Language code (e.g., "en", "es", "zh-CN")
    - cards_per_page: Layout option (4, 6, 8, or 12). Query param.

    RETURNS:
    - Binary PDF file as attachment
    - Filename: know-your-rights-{code}-{count}up.pdf

    ERRORS:
    - 400: Font not available for requested language
    - 404: Language code not found
    - 500: PDF generation failed
    - 503: Service not ready (store not initialized)
    """
    # === STEP 1: VALIDATE INPUTS ===

    # Ensure service is ready
    if store is None:
        logger.error("Store not initialized")
        raise HTTPException(status_code=503, detail="Service not ready")

    # Look up language
    item = store.get_language(code)
    if not item:
        raise LanguageNotFoundError(code)

    # Validate cards_per_page (use default if not provided)
    if cards_per_page is None:
        cards_per_page = settings.default_cards_per_page
    else:
        # This will clamp to valid values (4, 6, 8, 12)
        cards_per_page = settings.validate_cards_per_page(cards_per_page)

    logger.info(f"Rendering PDF for language: {code} with {cards_per_page} cards per page")

    # === STEP 2: CREATE LAYOUT ===

    # Calculate card positions on the page
    # This returns a CardLayout object with:
    # - positions: List of (x, y, width, height) for each card
    # - font_scale: Scaling factor for text (smaller for more cards)
    layout = CardLayout.from_cards_per_page(
        count=cards_per_page,
        page_size=settings.page_size,
        margin_inches=settings.margin_inches,
        gutter_inches=settings.gutter_inches,
        footer_height_inches=settings.footer_height_inches,
    )

    # === STEP 3: RENDER PDF ===

    try:
        # Build complete payload with front (translated) and back (English)
        pdf_bytes = render_print_sheet_pdf(
            payload={
                "code": item["code"],
                "name": item["name"],
                "rtl": item["rtl"],
                "official": True,
                "front": item.get("front", {}),
                "back": get_back_content(item["code"]),  # English back content
            },
            layout=layout,
        )
    except FontNotAvailableError:
        # Re-raise to let exception handler return proper 400 response
        raise
    except Exception as e:
        # Wrap other errors in PDFRenderError for 500 response
        logger.error(f"Failed to render PDF for {code}: {e}")
        raise PDFRenderError(str(e), code)

    # === STEP 4: RETURN PDF ===

    # Generate descriptive filename
    filename = f"know-your-rights-{item['code']}-{cards_per_page}up.pdf"
    logger.info(f"Successfully rendered PDF: {filename}")

    # Return PDF as downloadable file
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
