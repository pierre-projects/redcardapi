import io

import pytest
from pypdf import PdfReader

from app.config import Settings
from app.data import TranslationStore
from app.layout import CardLayout
from app.pdf import render_pdf

CODES = [lang.code for lang in TranslationStore.load(Settings().translations_json_path).languages()]


def _text(pdf_bytes: bytes) -> str:
    """Extracted text with whitespace collapsed (wrapping inserts line breaks)."""
    pages = PdfReader(io.BytesIO(pdf_bytes)).pages
    return " ".join(" ".join(page.extract_text() for page in pages).split())


@pytest.mark.parametrize("code", CODES)
def test_every_language_renders_grid_and_fold(code, store, fonts):
    language = store.get(code)

    grid = render_pdf(language, store.back, CardLayout.grid(4), fonts)
    assert len(PdfReader(io.BytesIO(grid)).pages) == 2
    assert "5th Amendment" in _text(grid)

    fold = render_pdf(language, store.back, CardLayout.fold(4), fonts)
    fold_text = _text(fold)
    assert len(PdfReader(io.BytesIO(fold)).pages) == 1
    assert f"Code: {language.display_code}" in fold_text
    assert "5th Amendment" in fold_text


@pytest.mark.parametrize("code", ["es", "fr", "ru", "vi", "el", "hy", "ka", "am"])
def test_front_text_is_extractable(code, store, fonts):
    # Scripts without shaping or bidi extract back to the source text.
    language = store.get(code)
    text = "".join(_text(render_pdf(language, store.back, CardLayout.grid(4), fonts)).split())
    first_bullet_start = "".join(language.front.bullets[0].text.split())[:12]
    assert first_bullet_start in text


@pytest.mark.parametrize("count", [4, 6, 8, 12])
def test_grid_layouts_have_matching_card_count(count):
    assert len(CardLayout.grid(count).positions) == count
