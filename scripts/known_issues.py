"""Translations known to be corrupted by PDF extraction.

Re-transcribe each from https://www.ilrc.org/red-cards, run
`python -m scripts.validate_translations`, then remove it from this list.
Tests fail if a language is fixed but still listed, or newly corrupted.
"""

KNOWN_CORRUPT = {
    "ar": "lam-alef split ('ال تفتح' should be 'لا تفتح'); letters swapped ('رشطي' → 'شرطي')",
    "km": "legacy-font junk ()*, 1*, 7*, =), a Thai letter, vowels stored before consonants",
    "ta": "vowel signs stored in visual order; words split by stray spaces",
}
