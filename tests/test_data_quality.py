"""Detects text corrupted by PDF extraction, the source of most translations."""

from app.config import settings
from scripts import validate_translations
from scripts.known_issues import KNOWN_CORRUPT
from scripts.validate_translations import corruption_issues


def test_no_new_corrupted_translations(store):
    flagged = {lang.code for lang in store.languages() if corruption_issues(lang)}
    assert flagged - set(KNOWN_CORRUPT) == set(), "newly corrupted translations"
    assert set(KNOWN_CORRUPT) - flagged == set(), "fixed translations: remove them from KNOWN_CORRUPT"


def test_validator_passes_with_only_known_issues():
    assert validate_translations.main(settings.translations_json_path) == 0


def test_validator_fails_on_issues_not_listed_as_known(monkeypatch):
    monkeypatch.setattr(validate_translations, "KNOWN_CORRUPT", {})
    assert validate_translations.main(settings.translations_json_path) == 1
