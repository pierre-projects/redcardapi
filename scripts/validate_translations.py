"""Validate data/Translations_with_sources.json before committing changes.

Checks:
  1. The file matches the schema (app/data.py) - same check the API runs at startup.
  2. Every character of every card has a glyph in the font its language uses.
  3. Heuristics for text corrupted by PDF extraction (reported as warnings).

Usage: python -m scripts.validate_translations [path/to/translations.json]
Languages listed in scripts/known_issues.py are reported but do not fail;
exit code 1 on a schema error or on problems in any other language.
Languages whose source sets "verified": false are listed for review.
"""

import re
import sys
import unicodedata
from itertools import pairwise
from pathlib import Path

from reportlab.pdfbase import pdfmetrics

from app.config import settings
from app.data import DatasetError, Language, TranslationStore
from app.fonts import init_font_manager
from scripts.known_issues import KNOWN_CORRUPT

_IGNORED = {" ", "\u200b", "\u200c", "\u200d", "\u00a0"}
# Junk from legacy (non-Unicode) fonts: "*", "=" or digits glued to letters of a
# non-Latin script, e.g. Khmer "ភា)*ក់".
_LEGACY_FONT_JUNK = re.compile(r"[\u0500-\uffff][*=0-9)]|[*=0-9(][\u0500-\uffff]")
# Arabic uses ك/ي; Persian-family languages use ک/ی. A mix means letters
# came from a different language's font mapping.
_FOREIGN_LETTERS = {
    "ar": "\u06a9\u06cc",  # Persian kaf and yeh
    "fa": "\u0643\u064a",  # Arabic kaf and yeh
    "prs": "\u0643\u064a",  # Arabic kaf and yeh
    "ps": "\u0643",  # Arabic kaf
    "ur": "\u0643\u064a",  # Arabic kaf and yeh
}


def corruption_issues(language: Language) -> list[str]:
    """Signs that text was mangled by extraction from a PDF."""
    texts = [language.front.header] + [b.text for b in language.front.bullets]
    issues = []
    foreign = _FOREIGN_LETTERS.get(language.code, "")
    for word in (w for text in texts for w in text.split()):
        if unicodedata.category(word[0]).startswith("M"):
            # Text in logical order never starts a word with a combining mark.
            issues.append(f"word starts with a combining mark: {word!r}")
        if any(a == b and unicodedata.category(a).startswith("M") for a, b in pairwise(word)):
            issues.append(f"doubled combining mark: {word!r}")
        if "\ufffd" in word:
            issues.append(f"replacement character: {word!r}")
        # A word wrapped in real parentheses, e.g. Sudanese Arabic "(تمضي)", is fine.
        core = word[1:-1] if word.startswith("(") and word.endswith(")") else word
        if _LEGACY_FONT_JUNK.search(core) and language.code not in ("ti", "yo"):
            issues.append(f"symbols inside a word: {word!r}")
        if foreign and any(ch in foreign for ch in word):
            issues.append(f"letters from another language's alphabet: {word!r}")
        if language.rtl and word == "ال":
            # The definite article never stands alone; usually a split "لا".
            issues.append("standalone 'ال' (split lam-alef?)")
    return issues


def missing_glyphs(store: TranslationStore) -> dict[str, str]:
    """Language code -> description of characters its font cannot draw."""
    fonts = init_font_manager(settings.fonts_dir)
    problems: dict[str, str] = {}
    for language in store.languages():
        for bold in (False, True):
            font_name = fonts.pick(language.code, bold=bold)
            cmap = pdfmetrics.getFont(font_name).face.charToGlyph
            texts = [language.front.header] + [b.text for b in language.front.bullets]
            absent = sorted({ch for t in texts for ch in t
                             if not ch.isspace() and ch not in _IGNORED and ord(ch) not in cmap})
            if absent:
                problems[language.code] = f"{font_name} lacks {''.join(absent)!r}"
    return problems


def main(path: Path) -> int:
    """Fail on schema errors and on problems in languages not already known to be corrupt."""
    try:
        store = TranslationStore.load(path)
    except DatasetError as exc:
        print(f"SCHEMA ERROR\n{exc}")
        return 1
    print(f"Schema OK: {len(store.languages())} languages")

    failed = False
    glyphs = missing_glyphs(store)
    for language in store.languages():
        code = language.code
        known = code in KNOWN_CORRUPT
        issues = corruption_issues(language)
        level = "KNOWN" if known else "ERROR"
        if code in glyphs:
            print(f"{level} {code} ({language.name}): missing glyphs, {glyphs[code]}")
        if issues:
            print(f"{level} {code} ({language.name}): {len(issues)} suspicious words, e.g. {issues[0]}")
        if not known and (code in glyphs or issues):
            failed = True
        if known and code not in glyphs and not issues:
            print(f"NOTE {code}: no longer looks corrupted; remove it from scripts/known_issues.py")
        if language.source.type == "machine":
            source = language.source
            print(f"MACHINE {code} ({language.name}): {source.engine}, {source.translated_on}")
        if not language.source.verified:
            print(f"REVIEW {code} ({language.name}): {language.source.review_note or 'not verified'}")

    print("Translations FAILED validation" if failed else "Translations OK (known issues listed above)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else settings.translations_json_path))
