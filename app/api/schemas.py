"""Response models (the public JSON contract)."""


from pydantic import BaseModel

from ..data import Bullet, Language, Source


class FrontOut(BaseModel):
    header: str
    bullets: list[Bullet]


class LanguageItem(BaseModel):
    code: str  # lowercase, e.g. "zh-cn"
    name: str  # English name
    native: str  # name in the language itself
    rtl: bool
    official: bool
    fontSupported: bool  # whether /api/render can produce a PDF
    source: Source | None = None


class CardPayload(BaseModel):
    code: str
    name: str
    native: str
    rtl: bool
    official: bool
    front: FrontOut
    source: Source | None = None

    @classmethod
    def of(cls, language: Language) -> "CardPayload":
        return cls(
            code=language.code, name=language.name, native=language.native, rtl=language.rtl,
            official=language.official, source=language.source,
            front=FrontOut(header=language.front.header, bullets=language.front.bullets),
        )


class ConfigResponse(BaseModel):
    valid_layouts: list[int]
    default_cards_per_page: int
    page_size: str
    render_modes: list[str]
    fold_layouts: list[int]
    default_fold_cards_per_page: int
    color_presets: list[str]  # "#RRGGBB" swatches for color prints
    default_color: str


class HealthResponse(BaseModel):
    ok: bool
    languages_loaded: int


class ReadyResponse(BaseModel):
    ready: bool
    languages_loaded: int
    fonts_loaded: bool
