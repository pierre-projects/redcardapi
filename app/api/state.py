"""Everything the request handlers need, created once per app."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from fastapi import Request

from ..config import Settings
from ..data import TranslationStore
from ..exceptions import ServiceNotReadyError
from ..fonts import FontManager
from .limits import PdfCache, RateLimiter


@dataclass
class AppState:
    settings: Settings
    store: TranslationStore
    pdf_cache: PdfCache
    limiter: RateLimiter
    render_pool: ThreadPoolExecutor
    # Set by a background task at startup; None until fonts are registered.
    fonts: FontManager | None = field(default=None)

    def require_fonts(self) -> FontManager:
        if self.fonts is None:
            raise ServiceNotReadyError()
        return self.fonts


def get_state(request: Request) -> AppState:
    return request.app.state.redcard
