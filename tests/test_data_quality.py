"""Detects text corrupted by PDF extraction, the source of most translations."""

import json

import pytest

from app.config import settings
from app.data import TranslationStore
from scripts import validate_translations
from scripts.known_issues import KNOWN_CORRUPT
from scripts.validate_translations import corruption_issues


def test_no_new_corrupted_translations(store):
    flagged = {lang.code for lang in store.languages() if corruption_issues(lang)}
    assert flagged - set(KNOWN_CORRUPT) == set(), "newly corrupted translations"
    assert set(KNOWN_CORRUPT) - flagged == set(), "fixed translations: remove them from KNOWN_CORRUPT"


def _with_text(tmp_path, code, text):
    """A copy of the dataset with one bullet of one language replaced."""
    data = json.loads(settings.translations_json_path.read_text(encoding="utf-8"))
    data["languages"][code]["front"]["bullets"][0]["text"] = text
    path = tmp_path / "translations.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


# Each example is a pattern found in the original PDF-extracted data.
@pytest.mark.parametrize("code,text", [
    ("ar", "ال تفتح الباب إذا كان رشطي الهجرة يطرق الباب."),            # split lam-alef
    ("ar", "إذا کنت خارج بیتك"),                                         # Persian letters in Arabic
    ("fa", "در را باز نکنید اگر مأمور مهاجرت دِِر خانه را می کوبد."),   # doubled mark
    ("km", "បសិនេបើភា)*ក់ងារ"),                                          # legacy-font junk
    ("ta", "உரி மைை கள்"),                                                # doubled vowel sign
    ("ta", "கதவை ேதி"),                                                   # word starts with a mark
    ("mh", "eļan̄̄n̄̄e"),                                                    # doubled macron
])
def test_validator_rejects_extraction_corruption(tmp_path, code, text):
    path = _with_text(tmp_path, code, text)
    assert corruption_issues(TranslationStore.load(path).get(code))
    assert validate_translations.main(path) == 1


def test_validator_passes_current_data():
    assert validate_translations.main(settings.translations_json_path) == 0


def test_known_issues_are_reported_without_failing(tmp_path, monkeypatch):
    monkeypatch.setattr(validate_translations, "KNOWN_CORRUPT", {"km": "awaiting re-transcription"})
    path = _with_text(tmp_path, "km", "បសិនេបើភា)*ក់ងារ")
    assert validate_translations.main(path) == 0


def test_unverified_translations_carry_a_review_note(store):
    for language in store.languages():
        if not language.source.verified:
            assert language.source.review_note, language.code
