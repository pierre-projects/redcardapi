"""Red Card API: printable know-your-rights card PDFs in many languages.

Run with:
    uvicorn app.main:app --proxy-headers --forwarded-allow-ips="*"
"""

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.limits import PdfCache, RateLimiter
from .api.routes import router
from .api.state import AppState
from .config import Settings
from .config import settings as default_settings
from .data import TranslationStore
from .exceptions import RedCardError
from .fonts import init_font_manager
from .logging_config import configure_logging

logger = logging.getLogger(__name__)

_LOCALHOST_ORIGIN = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$")
# Card, language and config JSON only change on redeploy.
_CACHEABLE_JSON = ("/api/languages", "/api/card/", "/api/config")


def check_production_settings(settings: Settings) -> None:
    """Fail fast on settings that would silently break a production deploy."""
    if settings.environment.lower() != "production":
        return
    origins = settings.cors_origins
    if not origins or all(_LOCALHOST_ORIGIN.match(o) for o in origins):
        raise RuntimeError(
            "CARD_ENVIRONMENT=production but CARD_CORS_ORIGINS only allows localhost. "
            "Set it to the frontend origin(s), e.g. CARD_CORS_ORIGINS='[\"https://cards.example.org\"]'."
        )
    if "*" in origins:
        raise RuntimeError("CARD_CORS_ORIGINS must list origins explicitly in production, not '*'.")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or default_settings
    configure_logging(settings.log_level)
    check_production_settings(settings)
    # Load and validate the dataset now: a bad file fails the deploy, not a request.
    store = TranslationStore.load(settings.translations_json_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state = AppState(
            settings=settings,
            store=store,
            pdf_cache=PdfCache(settings.pdf_cache_size),
            limiter=RateLimiter(settings.render_rate_limit_per_minute),
            render_pool=ThreadPoolExecutor(max_workers=settings.render_workers,
                                           thread_name_prefix="render"),
        )
        app.state.redcard = state
        logger.info("Loaded %d languages from %s", len(store.languages()), settings.translations_json_path)

        async def load_fonts():
            # ~1 s of font parsing; done off the event loop so /api/health
            # answers immediately and /api/ready reports when PDFs can render.
            state.fonts = await asyncio.to_thread(init_font_manager, settings.fonts_dir)

        font_task = asyncio.create_task(load_fonts())
        yield
        font_task.cancel()
        state.render_pool.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(
        title="Red Card API",
        description="Printable know-your-rights card PDFs in many languages.",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Read-only API without cookies: GET only, no credentials.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def cache_json(request: Request, call_next):
        response = await call_next(request)
        if (request.method == "GET" and response.status_code == 200
                and request.url.path.startswith(_CACHEABLE_JSON)):
            response.headers.setdefault("Cache-Control", f"public, max-age={settings.json_cache_seconds}")
        return response

    @app.exception_handler(RedCardError)
    async def redcard_error(request: Request, exc: RedCardError):
        return JSONResponse(status_code=exc.status_code, content=exc.body(), headers=exc.headers)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500,
                            content={"detail": "Internal server error.", "code": "internal_error"})

    app.include_router(router)
    return app


app = create_app()
