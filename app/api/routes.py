"""HTTP endpoints."""

import asyncio
import logging
import re
import unicodedata

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse

from ..data import Language
from ..exceptions import LanguageNotFoundError, PDFRenderError, RedCardError, RenderTimeoutError
from ..fonts import detect_script
from ..layout import FOLD_ROWS, GRID_LAYOUTS, MODE_ALIASES, MODE_FOLD, MODE_GRID, CardLayout
from ..pdf import render_pdf
from .schemas import CardPayload, ConfigResponse, HealthResponse, LanguageItem, ReadyResponse
from .state import AppState, get_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def _language(state: AppState, code: str) -> Language:
    language = state.store.get(code)
    if language is None:
        raise LanguageNotFoundError(code)
    return language


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()


def _invalid(detail: str) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": detail, "code": "invalid_request"})


@router.get("/health", response_model=HealthResponse)
async def health(state: AppState = Depends(get_state)):
    """Liveness: the process is up and serving. Always 200."""
    count = len(state.store.languages())
    return HealthResponse(ok=count > 0, languages_loaded=count)


@router.get("/ready", response_model=ReadyResponse)
async def ready(response: Response, state: AppState = Depends(get_state)):
    """Readiness: 503 until fonts are registered and PDFs can be rendered."""
    is_ready = state.fonts is not None
    if not is_ready:
        response.status_code = 503
    return ReadyResponse(ready=is_ready, languages_loaded=len(state.store.languages()),
                         fonts_loaded=is_ready)


@router.get("/config", response_model=ConfigResponse)
async def config(state: AppState = Depends(get_state)):
    s = state.settings
    return ConfigResponse(
        valid_layouts=sorted(GRID_LAYOUTS),
        default_cards_per_page=s.default_cards_per_page,
        page_size=s.page_size,
        render_modes=[MODE_GRID, MODE_FOLD],
        fold_layouts=list(FOLD_ROWS),
        default_fold_cards_per_page=s.default_fold_cards_per_page,
    )


@router.get("/languages", response_model=list[LanguageItem])
async def languages(state: AppState = Depends(get_state)):
    fonts = state.require_fonts()
    return [
        LanguageItem(
            code=lang.code, name=lang.name, native=lang.native, rtl=lang.rtl,
            official=lang.official, source=lang.source,
            fontSupported=fonts.is_script_supported(detect_script(lang.code)),
        )
        for lang in state.store.languages()
    ]


@router.get("/card/{code}", response_model=CardPayload)
async def card(code: str, state: AppState = Depends(get_state)):
    return CardPayload.of(_language(state, code))


@router.get("/render/{code}")
async def render(
    request: Request,
    code: str,
    cards_per_page: int | None = Query(
        default=None,
        description="Grid mode: cards per page (4, 6, 8, 12). Fold mode: rows (4, 5, 6).",
    ),
    mode: str = Query(default=MODE_GRID, description='"grid" (alias "legacy") or "fold".'),
    state: AppState = Depends(get_state),
):
    """Printable PDF for one language."""
    resolved_mode = MODE_ALIASES.get(mode)
    if resolved_mode is None:
        return _invalid(f'Invalid mode "{mode}". Use "grid" or "fold".')

    s = state.settings
    if resolved_mode == MODE_FOLD:
        count = cards_per_page or s.default_fold_cards_per_page
        if count not in FOLD_ROWS:
            return _invalid(f"Fold mode supports {list(FOLD_ROWS)} rows, not {count}.")
        layout_factory = CardLayout.fold
    else:
        count = cards_per_page or s.default_cards_per_page
        if count not in GRID_LAYOUTS:
            return _invalid(f"Grid mode supports {sorted(GRID_LAYOUTS)} cards per page, not {count}.")
        layout_factory = CardLayout.grid

    language = _language(state, code)
    fonts = state.require_fonts()
    filename = (
        f"know-your-rights-{language.display_code}-{_slug(language.name) or language.code}"
        f"-{count}up{'-fold' if resolved_mode == MODE_FOLD else ''}.pdf"
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": f"public, max-age={s.pdf_cache_seconds}",
    }

    cache_key = (language.code, resolved_mode, count, s.page_size)
    cached = state.pdf_cache.get(cache_key)
    if cached is not None:
        return Response(content=cached[0], media_type="application/pdf", headers=headers)

    # Only renders count against the limit; cached PDFs are cheap to serve.
    state.limiter.check(request.client.host if request.client else "unknown")

    layout = layout_factory(
        count, page_size=s.page_size, margin_inches=s.margin_inches,
        gutter_inches=s.gutter_inches, footer_height_inches=s.footer_height_inches,
    )
    loop = asyncio.get_running_loop()
    job = loop.run_in_executor(state.render_pool, render_pdf, language, state.store.back, layout, fonts)
    try:
        pdf_bytes = await asyncio.wait_for(job, timeout=s.render_timeout_seconds)
    except TimeoutError as exc:
        logger.error("Render timed out for %s (%s, %d)", language.code, resolved_mode, count)
        raise RenderTimeoutError() from exc
    except RedCardError:
        raise
    except Exception as exc:
        logger.exception("Render failed for %s (%s, %d)", language.code, resolved_mode, count)
        raise PDFRenderError() from exc

    state.pdf_cache.put(cache_key, (pdf_bytes, filename))
    logger.info("Rendered %s", filename)
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
