"""Validate data/Translations_with_sources.json before committing changes.

Checks:
  1. The file matches the schema (app/data.py) - same check the API runs at startup.
  2. Every character of every card has a glyph in the font its language uses.
  3. Heuristics for text corrupted by PDF extraction (reported as warnings).

Usage: python -m scripts.validate_translations [path/to/translations.json]
Exit code 1 if 1 or 2 fail.
"""

import re
import sys
import unicodedata
from pathlib import Path

from reportlab.pdfbase import pdfmetrics

from app.config import settings
from app.data import DatasetError, Language, TranslationStore
from app.fonts import init_font_manager

_IGNORED = {" ", "​", "‌", "‍", " "}
# Junk from legacy (non-Unicode) fonts: "*", "=" or digits glued to letters of a
# non-Latin script, e.g. Khmer "ភា)*ក់".
_LEGACY_FONT_JUNK = re.compile(r"[Ԁ-￿][*=0-9)]|[*=0-9(][Ԁ-￿]")


def corruption_issues(language: Language) -> list[str]:
    """Signs that text was extracted from a PDF in visual rather than logical order."""
    texts = [language.front.header] + [b.text for b in language.front.bullets]
    issues = []
    for word in (w for text in texts for w in text.split()):
        if unicodedata.category(word[0]).startswith("M"):
            # Text in logical order never starts a word with a combining mark.
            issues.append(f"word starts with a combining mark: {word!r}")
        if _LEGACY_FONT_JUNK.search(word) and language.code not in ("ti", "yo"):
            issues.append(f"symbols inside a word: {word!r}")
        if language.rtl and word == "ال":
            # The definite article never stands alone; usually a split "لا".
            issues.append("standalone 'ال' (split lam-alef?)")
    return issues


def missing_glyphs(store: TranslationStore) -> list[str]:
    fonts = init_font_manager(settings.fonts_dir)
    problems = []
    for language in store.languages():
        for bold in (False, True):
            font_name = fonts.pick(language.code, bold=bold)
            cmap = pdfmetrics.getFont(font_name).face.charToGlyph
            texts = [language.front.header] + [b.text for b in language.front.bullets]
            absent = sorted({ch for t in texts for ch in t
                             if not ch.isspace() and ch not in _IGNORED and ord(ch) not in cmap})
            if absent:
                problems.append(f"{language.code}: {font_name} lacks {''.join(absent)!r}")
    return problems


def main(path: Path) -> int:
    try:
        store = TranslationStore.load(path)
    except DatasetError as exc:
        print(f"SCHEMA ERROR\n{exc}")
        return 1
    print(f"Schema OK: {len(store.languages())} languages")

    errors = missing_glyphs(store)
    for error in errors:
        print(f"MISSING GLYPHS {error}")
    if not errors:
        print("Glyph coverage OK")

    for language in store.languages():
        issues = corruption_issues(language)
        if issues:
            print(f"WARNING {language.code} ({language.name}): {len(issues)} suspicious words, "
                  f"e.g. {issues[0]}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else settings.translations_json_path))
