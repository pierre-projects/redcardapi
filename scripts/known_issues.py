"""Translations known to fail scripts/validate_translations.py.

List a language here only while its text awaits re-transcription from
https://www.ilrc.org/red-cards; the validator then reports it without
failing. Tests fail if a listed language passes, so fixed entries get removed.

Separately, languages whose data sets "verified": false (with a review_note)
were reconstructed from flawed source artwork and need native-speaker review.
"""

KNOWN_CORRUPT: dict[str, str] = {}
