"""Detects text corrupted by PDF extraction, the source of most translations."""

from scripts.validate_translations import corruption_issues
from tests.known_issues import KNOWN_CORRUPT


def test_no_new_corrupted_translations(store):
    flagged = {lang.code for lang in store.languages() if corruption_issues(lang)}
    assert flagged - set(KNOWN_CORRUPT) == set(), "newly corrupted translations"
    assert set(KNOWN_CORRUPT) - flagged == set(), "fixed translations: remove them from KNOWN_CORRUPT"
