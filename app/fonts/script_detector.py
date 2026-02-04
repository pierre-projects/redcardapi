"""
Script Detection from Language Codes.

=============================================================================
MODULE OVERVIEW
=============================================================================

This module maps ISO language codes to Unicode writing systems (scripts).
It's the first step in the font selection process:

    Language Code -> Script -> Font Family -> Font Files

EXAMPLE FLOW:
    "ar" (Arabic) -> Script.ARABIC -> NotoSansArabic -> NotoSansArabic-*.ttf

=============================================================================
WHY SCRIPT DETECTION?
=============================================================================

Different languages use different writing systems. A language code like "ar"
(Arabic) tells us:
1. Which script (writing system) is used -> Arabic script
2. Which direction text flows -> Right-to-left
3. Which font family is needed -> NotoSansArabic

This mapping is essential because:
- Unicode doesn't tell us which font to use
- One font can't render all scripts well
- RTL languages need special handling

=============================================================================
SCRIPT CATEGORIES
=============================================================================

LATIN-BASED (39 languages):
    European: en, es, fr, de, it, pt, nl, pl, ro, hu, cs, sk, hr, sl, sq, tr, bs
    African: sw, so, ha, ig, yo, rw, om, ln
    Asian: id, ms, tl, ceb, ilo, hmn
    Pacific: fj, to, sm, mi, haw, mh
    Americas: ht, nah, tzo, kea

CYRILLIC (5 languages): ru, uk, bg, sr, mk

ARABIC SCRIPT (6 languages): ar, fa, ur, ps, prs, ku

CJK (5 codes): zh-CN, zh-TW, yue, ja, ko

SOUTH ASIAN (6 languages): hi, ne, mr, bn, ta, pa

SOUTHEAST ASIAN (5 languages): th, lo, km, my, kar

OTHER (6 languages): vi, el, mn, he, am, ti, hy, ka

=============================================================================
CASE SENSITIVITY NOTES
=============================================================================

Language codes in Translations.json are normalized to lowercase by
TranslationsStore, but some standard codes use mixed case (zh-CN, zh-TW).

The detect_script() function handles this by:
1. First trying exact lowercase match
2. Then trying case-insensitive match for mixed-case codes

=============================================================================
ADDING NEW LANGUAGES
=============================================================================

To add support for a new language:

1. Identify which Unicode script the language uses
2. Add a Script enum value if needed (see Script class)
3. Add the language code mapping to LANGUAGE_TO_SCRIPT
4. Ensure font_config.py has fonts for that script

EXAMPLE:
    # Adding Georgian language
    "ka": Script.GEORGIAN,

=============================================================================
"""

from enum import Enum, auto
from typing import Dict


# =============================================================================
# SCRIPT ENUM
# =============================================================================

class Script(Enum):
    """
    Unicode script systems supported by the application.

    Each enum value represents a distinct writing system that requires
    specific fonts to render correctly. Scripts are mapped to font
    families in font_config.py.

    GROUPINGS:

    European/Latin-based:
        LATIN - Most European languages, many African/Asian languages
        CYRILLIC - Russian, Ukrainian, Serbian, etc.
        GREEK - Greek language
        VIETNAMESE - Latin with special diacritics

    Middle Eastern (RTL):
        ARABIC - Arabic, Persian, Urdu, Kurdish
        HEBREW - Hebrew

    East Asian (CJK):
        CJK_SIMPLIFIED - Simplified Chinese (Mainland China)
        CJK_TRADITIONAL - Traditional Chinese (Taiwan, HK), Cantonese
        JAPANESE - Kanji, Hiragana, Katakana
        KOREAN - Hangul

    South Asian:
        DEVANAGARI - Hindi, Nepali, Marathi
        BENGALI - Bengali/Bangla
        TAMIL - Tamil
        GURMUKHI - Punjabi

    Southeast Asian:
        THAI - Thai
        LAO - Lao
        KHMER - Khmer/Cambodian
        MYANMAR - Burmese, Karen

    Other:
        ETHIOPIC - Amharic, Tigrinya (Ge'ez script)
        ARMENIAN - Armenian
        GEORGIAN - Georgian (Mkhedruli script)
        MONGOLIAN - Modern Mongolian (uses Cyrillic)
    """

    LATIN = auto()          # English, Spanish, French, German, etc.
    CYRILLIC = auto()       # Russian, Ukrainian, etc.
    ARABIC = auto()         # Arabic, Persian, Urdu, Pashto
    HEBREW = auto()         # Hebrew
    CJK_SIMPLIFIED = auto() # Chinese Simplified
    CJK_TRADITIONAL = auto()# Chinese Traditional, Cantonese
    JAPANESE = auto()       # Japanese (includes Hiragana, Katakana, Kanji)
    KOREAN = auto()         # Korean (Hangul)
    DEVANAGARI = auto()     # Hindi, Nepali, Marathi
    BENGALI = auto()        # Bengali
    TAMIL = auto()          # Tamil
    GURMUKHI = auto()       # Punjabi
    THAI = auto()           # Thai
    LAO = auto()            # Lao
    KHMER = auto()          # Khmer (Cambodian)
    MYANMAR = auto()        # Burmese, Karen
    ETHIOPIC = auto()       # Amharic, Tigrinya
    ARMENIAN = auto()       # Armenian
    GEORGIAN = auto()       # Georgian
    VIETNAMESE = auto()     # Vietnamese (uses Latin with diacritics)
    GREEK = auto()          # Greek
    MONGOLIAN = auto()      # Mongolian (Cyrillic-based modern script)


# =============================================================================
# LANGUAGE TO SCRIPT MAPPING
# =============================================================================
# Maps ISO 639-1/639-3 language codes to their Unicode script.
# Based on the 56+ languages in Translations.json.
#
# IMPORTANT: Language codes are case-sensitive in this dict, but
# detect_script() handles case-insensitive lookup.

LANGUAGE_TO_SCRIPT: Dict[str, Script] = {

    # =========================================================================
    # LATIN SCRIPT LANGUAGES (39 languages)
    # =========================================================================
    # These all use the Latin alphabet with various diacritics.
    # Rendered with NotoSans font.

    # Western European
    "en": Script.LATIN,       # English
    "es": Script.LATIN,       # Spanish
    "fr": Script.LATIN,       # French
    "de": Script.LATIN,       # German
    "it": Script.LATIN,       # Italian
    "pt": Script.LATIN,       # Portuguese
    "nl": Script.LATIN,       # Dutch

    # Central/Eastern European (Latin alphabet)
    "pl": Script.LATIN,       # Polish
    "ro": Script.LATIN,       # Romanian
    "hu": Script.LATIN,       # Hungarian
    "cs": Script.LATIN,       # Czech
    "sk": Script.LATIN,       # Slovak
    "hr": Script.LATIN,       # Croatian
    "sl": Script.LATIN,       # Slovenian
    "sq": Script.LATIN,       # Albanian
    "bs": Script.LATIN,       # Bosnian
    "tr": Script.LATIN,       # Turkish

    # Southeast Asian (Latin alphabet)
    "id": Script.LATIN,       # Indonesian
    "ms": Script.LATIN,       # Malay
    "tl": Script.LATIN,       # Tagalog/Filipino
    "ceb": Script.LATIN,      # Cebuano
    "ilo": Script.LATIN,      # Ilocano
    "hmn": Script.LATIN,      # Hmong (Romanized)

    # African (Latin alphabet)
    "sw": Script.LATIN,       # Swahili
    "so": Script.LATIN,       # Somali
    "ha": Script.LATIN,       # Hausa
    "ig": Script.LATIN,       # Igbo
    "yo": Script.LATIN,       # Yoruba
    "rw": Script.LATIN,       # Kinyarwanda
    "om": Script.LATIN,       # Oromo
    "ln": Script.LATIN,       # Lingala

    # Caribbean/Creole
    "ht": Script.LATIN,       # Haitian Creole
    "kea": Script.LATIN,      # Cape Verdean Creole

    # Pacific Islands
    "fj": Script.LATIN,       # Fijian
    "to": Script.LATIN,       # Tongan
    "sm": Script.LATIN,       # Samoan
    "mi": Script.LATIN,       # Maori
    "haw": Script.LATIN,      # Hawaiian
    "mh": Script.LATIN,       # Marshallese

    # Indigenous Americas
    "nah": Script.LATIN,      # Nahuatl
    "tzo": Script.LATIN,      # Tsotsil

    # =========================================================================
    # VIETNAMESE (Special Latin)
    # =========================================================================
    # Uses Latin alphabet with extensive diacritics.
    # NotoSans has full Vietnamese support.
    "vi": Script.VIETNAMESE,

    # =========================================================================
    # CYRILLIC SCRIPT LANGUAGES (5 languages)
    # =========================================================================
    # Eastern European/Slavic languages using Cyrillic alphabet.
    # Rendered with NotoSans (includes Cyrillic).
    "ru": Script.CYRILLIC,    # Russian
    "uk": Script.CYRILLIC,    # Ukrainian
    "bg": Script.CYRILLIC,    # Bulgarian
    "sr": Script.CYRILLIC,    # Serbian (can also use Latin)
    "mk": Script.CYRILLIC,    # Macedonian

    # =========================================================================
    # MONGOLIAN (Cyrillic-based)
    # =========================================================================
    # Modern Mongolian uses Cyrillic script (since 1940s).
    # Traditional vertical script is not supported.
    "mn": Script.MONGOLIAN,

    # =========================================================================
    # ARABIC SCRIPT LANGUAGES (6 languages) - RTL
    # =========================================================================
    # Right-to-left languages using Arabic script.
    # Requires special RTL text processing (arabic-reshaper, python-bidi).
    "ar": Script.ARABIC,      # Arabic
    "fa": Script.ARABIC,      # Persian/Farsi
    "ur": Script.ARABIC,      # Urdu
    "ps": Script.ARABIC,      # Pashto
    "prs": Script.ARABIC,     # Dari (Afghan Persian)
    "ku": Script.ARABIC,      # Kurdish (Sorani dialect uses Arabic script)

    # =========================================================================
    # HEBREW - RTL
    # =========================================================================
    # Right-to-left language with unique alphabet.
    "he": Script.HEBREW,

    # =========================================================================
    # GREEK
    # =========================================================================
    # Uses Greek alphabet. NotoSans includes Greek characters.
    "el": Script.GREEK,

    # =========================================================================
    # CJK LANGUAGES (5 codes)
    # =========================================================================
    # East Asian languages with complex character sets.
    # Each requires large dedicated font files (~16MB each).
    #
    # NOTE: zh-CN and zh-TW are case-sensitive in the original mapping,
    # but detect_script() handles case-insensitive lookup.

    "zh-CN": Script.CJK_SIMPLIFIED,    # Simplified Chinese (Mainland China)
    "zh-TW": Script.CJK_TRADITIONAL,   # Traditional Chinese (Taiwan)
    "yue": Script.CJK_TRADITIONAL,     # Cantonese (uses Traditional characters)
    "ja": Script.JAPANESE,             # Japanese (Kanji + Hiragana + Katakana)
    "ko": Script.KOREAN,               # Korean (Hangul)

    # =========================================================================
    # SOUTH ASIAN SCRIPTS (6 languages)
    # =========================================================================
    # Languages of the Indian subcontinent with unique scripts.

    # Devanagari script (Hindi, Sanskrit-derived)
    "hi": Script.DEVANAGARI,  # Hindi
    "ne": Script.DEVANAGARI,  # Nepali
    "mr": Script.DEVANAGARI,  # Marathi

    # Other South Asian scripts
    "bn": Script.BENGALI,     # Bengali/Bangla
    "ta": Script.TAMIL,       # Tamil
    "pa": Script.GURMUKHI,    # Punjabi (Gurmukhi script)

    # =========================================================================
    # SOUTHEAST ASIAN SCRIPTS (5 languages)
    # =========================================================================
    # Languages with unique scripts derived from Brahmic scripts.

    "th": Script.THAI,        # Thai
    "lo": Script.LAO,         # Lao
    "km": Script.KHMER,       # Khmer (Cambodian)
    "my": Script.MYANMAR,     # Burmese
    "kar": Script.MYANMAR,    # Karen (uses Myanmar script)

    # =========================================================================
    # ETHIOPIC SCRIPT (2 languages)
    # =========================================================================
    # Ge'ez-derived script used in Ethiopia/Eritrea.

    "am": Script.ETHIOPIC,    # Amharic
    "ti": Script.ETHIOPIC,    # Tigrinya

    # =========================================================================
    # CAUCASIAN SCRIPTS (2 languages)
    # =========================================================================
    # Unique scripts from the Caucasus region.

    "hy": Script.ARMENIAN,    # Armenian
    "ka": Script.GEORGIAN,    # Georgian (Mkhedruli script)
}


# =============================================================================
# PUBLIC API FUNCTIONS
# =============================================================================

def detect_script(lang_code: str) -> Script:
    """
    Detect the Unicode script for a language code.

    This is the primary function used by the font selection system.
    Given a language code, returns the Script enum value needed to
    select the appropriate font.

    PARAMETERS:
        lang_code: ISO language code (e.g., "ar", "zh-CN", "en")
                   Case-insensitive - "zh-cn" and "zh-CN" both work

    RETURNS:
        Script enum value for the language
        Defaults to Script.LATIN if language is not in mapping

    ALGORITHM:
        1. Normalize input to lowercase
        2. Try exact match in LANGUAGE_TO_SCRIPT
        3. If not found, try case-insensitive match (for zh-CN, zh-TW)
        4. If still not found, default to LATIN

    EXAMPLE:
        detect_script("ar")     -> Script.ARABIC
        detect_script("zh-CN")  -> Script.CJK_SIMPLIFIED
        detect_script("zh-cn")  -> Script.CJK_SIMPLIFIED (case-insensitive)
        detect_script("xyz")    -> Script.LATIN (default)

    WHY CASE-INSENSITIVE?
        TranslationsStore normalizes language codes to lowercase,
        but some standard codes use mixed case (zh-CN, zh-TW).
        This function handles both conventions.
    """
    # Normalize to lowercase for comparison
    normalized = lang_code.lower() if lang_code else ""

    # Try direct lookup first (most language codes are lowercase)
    if normalized in LANGUAGE_TO_SCRIPT:
        return LANGUAGE_TO_SCRIPT[normalized]

    # Try case-insensitive match for codes like zh-CN, zh-TW
    # These are stored with mixed case in the mapping
    for key, script in LANGUAGE_TO_SCRIPT.items():
        if key.lower() == normalized:
            return script

    # Default to LATIN if language code not found
    # This is a safe fallback as Latin fonts can render basic ASCII
    return Script.LATIN


def is_rtl_script(script: Script) -> bool:
    """
    Check if a script is right-to-left.

    RTL scripts require special text processing:
    - Text direction must be reversed
    - Arabic requires letter reshaping (connected forms)
    - Numbers and punctuation need bidirectional handling

    PARAMETERS:
        script: Script enum value to check

    RETURNS:
        True if the script is RTL (Arabic or Hebrew)

    EXAMPLE:
        is_rtl_script(Script.ARABIC)  -> True
        is_rtl_script(Script.HEBREW)  -> True
        is_rtl_script(Script.LATIN)   -> False
    """
    return script in (Script.ARABIC, Script.HEBREW)


def is_rtl_language(lang_code: str) -> bool:
    """
    Check if a language uses a right-to-left script.

    Convenience function that combines detect_script() and is_rtl_script().

    PARAMETERS:
        lang_code: ISO language code (e.g., "ar", "he", "fa")

    RETURNS:
        True if the language uses RTL script

    EXAMPLE:
        is_rtl_language("ar")   -> True (Arabic)
        is_rtl_language("he")   -> True (Hebrew)
        is_rtl_language("fa")   -> True (Persian/Farsi uses Arabic script)
        is_rtl_language("en")   -> False

    USAGE:
        Used by PDF renderer to determine text alignment and direction.
    """
    return is_rtl_script(detect_script(lang_code))


def get_all_scripts() -> list:
    """
    Get list of all supported Unicode scripts.

    RETURNS:
        List of all Script enum values

    USAGE:
        Useful for iterating over all scripts to check font availability:

        for script in get_all_scripts():
            if font_manager.is_script_supported(script):
                print(f"{script.name}: supported")
    """
    return list(Script)


def get_languages_for_script(script: Script) -> list:
    """
    Get all language codes that use a given script.

    Useful for finding which languages will be affected if a
    particular font is missing.

    PARAMETERS:
        script: Script enum value to search for

    RETURNS:
        List of language codes that use this script

    EXAMPLE:
        get_languages_for_script(Script.ARABIC)
        # Returns: ["ar", "fa", "ur", "ps", "prs", "ku"]

        get_languages_for_script(Script.DEVANAGARI)
        # Returns: ["hi", "ne", "mr"]

    USAGE:
        # Find all affected languages when Arabic fonts are missing
        affected = get_languages_for_script(Script.ARABIC)
        print(f"Missing Arabic font affects: {', '.join(affected)}")
    """
    return [code for code, s in LANGUAGE_TO_SCRIPT.items() if s == script]
