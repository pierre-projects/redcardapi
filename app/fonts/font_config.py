"""
Font Family Configuration for Multi-Language PDF Rendering.

=============================================================================
MODULE OVERVIEW
=============================================================================

This module defines the font configuration for rendering PDFs in multiple
languages. It maps Unicode scripts to specific Noto Sans font families.

KEY CONCEPTS:
- FontFamily: Configuration for a font (name, files, supported scripts)
- FONT_FAMILIES: Registry of all available fonts
- SCRIPT_TO_FONTS: Maps each Script to preferred font families

=============================================================================
FONT SELECTION FLOW
=============================================================================

    1. User requests PDF for language "ko" (Korean)
    2. script_detector.detect_script("ko") -> Script.KOREAN
    3. SCRIPT_TO_FONTS[Script.KOREAN] -> ["NotoSansKR"]
    4. FontManager checks if NotoSansKR files exist
    5. If exists: Register and use NotoSansKR
    6. If not: Raise FontNotAvailableError

=============================================================================
NOTO SANS FONT FAMILY
=============================================================================

We use Google's Noto Sans font family because:

1. COMPREHENSIVE COVERAGE - Supports virtually all writing systems
2. CONSISTENT DESIGN - Harmonious appearance across scripts
3. OPEN SOURCE - Apache 2.0 license, free to use
4. MULTIPLE WEIGHTS - Regular and Bold for each script

Font files are stored in: assets/fonts/

=============================================================================
SCRIPT CATEGORIES
=============================================================================

LATIN-BASED (NotoSans):
    Latin, Cyrillic, Vietnamese, Greek, Mongolian (Cyrillic)

ARABIC SCRIPT (NotoSansArabic):
    Arabic, Persian, Urdu, Pashto, Kurdish

CJK SCRIPTS (Large fonts ~16MB each):
    Simplified Chinese (NotoSansSC)
    Traditional Chinese (NotoSansTC)
    Japanese (NotoSansJP)
    Korean (NotoSansKR)

SOUTH ASIAN:
    Devanagari (Hindi, Nepali, Marathi)
    Bengali, Tamil, Gurmukhi (Punjabi)

SOUTHEAST ASIAN:
    Thai, Lao, Khmer, Myanmar

OTHER:
    Hebrew, Ethiopic, Armenian, Georgian

=============================================================================
ADDING NEW FONTS
=============================================================================

To add support for a new script:

1. Download the Noto Sans font for that script from:
   https://fonts.google.com/noto

2. Place Regular and Bold TTF files in Backend/assets/fonts/

3. Add a FontFamily entry to FONT_FAMILIES:
   "NotoSansNewScript": FontFamily(
       name="NotoSansNewScript",
       regular_file="NotoSansNewScript-Regular.ttf",
       bold_file="NotoSansNewScript-Bold.ttf",
       scripts=[Script.NEW_SCRIPT],
   ),

4. Add mapping to SCRIPT_TO_FONTS:
   Script.NEW_SCRIPT: ["NotoSansNewScript", "NotoSans"],

5. Add Script enum value and language mapping in script_detector.py

=============================================================================
"""

from dataclasses import dataclass, field
from typing import List, Dict
from .script_detector import Script


# =============================================================================
# FONT FAMILY DATACLASS
# =============================================================================

@dataclass
class FontFamily:
    """
    Configuration for a font family.

    Defines the files and scripts supported by a single font family.
    Used by FontManager to register fonts with ReportLab.

    ATTRIBUTES:
        name: Internal name used as ReportLab font identifier
              Example: "NotoSansArabic" -> pdfmetrics.registerFont("NotoSansArabic")

        regular_file: Filename for regular weight (400)
                      Must exist in settings.fonts_dir

        bold_file: Filename for bold weight (700)
                   Used for headers and emphasized text

        scripts: List of Unicode scripts this font can render
                 Used for font selection based on language

    EXAMPLE:
        FontFamily(
            name="NotoSansArabic",
            regular_file="NotoSansArabic-Regular.ttf",
            bold_file="NotoSansArabic-Bold.ttf",
            scripts=[Script.ARABIC],
        )
    """

    name: str                      # Internal name (used as ReportLab font name)
    regular_file: str              # Filename for regular weight
    bold_file: str                 # Filename for bold weight
    scripts: List[Script] = field(default_factory=list)  # Scripts this font supports


# =============================================================================
# FONT FAMILY REGISTRY
# =============================================================================
# All font families bundled with the application.
# Order matters for fallback - first font that exists wins.
#
# IMPORTANT: Font files must exist in Backend/assets/fonts/
# If a font file is missing, FontManager will mark that script as unsupported.

FONT_FAMILIES: Dict[str, FontFamily] = {
    # Base Latin/Cyrillic font
    "NotoSans": FontFamily(
        name="NotoSans",
        regular_file="NotoSans-Regular.ttf",
        bold_file="NotoSans-Bold.ttf",
        scripts=[Script.LATIN, Script.CYRILLIC, Script.VIETNAMESE],
    ),

    # Arabic script
    "NotoSansArabic": FontFamily(
        name="NotoSansArabic",
        regular_file="NotoSansArabic-Regular.ttf",
        bold_file="NotoSansArabic-Bold.ttf",
        scripts=[Script.ARABIC],
    ),

    # Hebrew
    "NotoSansHebrew": FontFamily(
        name="NotoSansHebrew",
        regular_file="NotoSansHebrew-Regular.ttf",
        bold_file="NotoSansHebrew-Bold.ttf",
        scripts=[Script.HEBREW],
    ),

    # CJK fonts (large, ~16MB each)
    "NotoSansSC": FontFamily(
        name="NotoSansSC",
        regular_file="NotoSansSC-Regular.ttf",
        bold_file="NotoSansSC-Bold.ttf",
        scripts=[Script.CJK_SIMPLIFIED],
    ),
    "NotoSansTC": FontFamily(
        name="NotoSansTC",
        regular_file="NotoSansTC-Regular.ttf",
        bold_file="NotoSansTC-Bold.ttf",
        scripts=[Script.CJK_TRADITIONAL],
    ),
    "NotoSansJP": FontFamily(
        name="NotoSansJP",
        regular_file="NotoSansJP-Regular.ttf",
        bold_file="NotoSansJP-Bold.ttf",
        scripts=[Script.JAPANESE],
    ),
    "NotoSansKR": FontFamily(
        name="NotoSansKR",
        regular_file="NotoSansKR-Regular.ttf",
        bold_file="NotoSansKR-Bold.ttf",
        scripts=[Script.KOREAN],
    ),

    # South Asian scripts
    "NotoSansDevanagari": FontFamily(
        name="NotoSansDevanagari",
        regular_file="NotoSansDevanagari-Regular.ttf",
        bold_file="NotoSansDevanagari-Bold.ttf",
        scripts=[Script.DEVANAGARI],
    ),
    "NotoSansBengali": FontFamily(
        name="NotoSansBengali",
        regular_file="NotoSansBengali-Regular.ttf",
        bold_file="NotoSansBengali-Bold.ttf",
        scripts=[Script.BENGALI],
    ),
    "NotoSansTamil": FontFamily(
        name="NotoSansTamil",
        regular_file="NotoSansTamil-Regular.ttf",
        bold_file="NotoSansTamil-Bold.ttf",
        scripts=[Script.TAMIL],
    ),
    "NotoSansGurmukhi": FontFamily(
        name="NotoSansGurmukhi",
        regular_file="NotoSansGurmukhi-Regular.ttf",
        bold_file="NotoSansGurmukhi-Bold.ttf",
        scripts=[Script.GURMUKHI],
    ),

    # Southeast Asian scripts
    "NotoSansThai": FontFamily(
        name="NotoSansThai",
        regular_file="NotoSansThai-Regular.ttf",
        bold_file="NotoSansThai-Bold.ttf",
        scripts=[Script.THAI],
    ),
    "NotoSansLao": FontFamily(
        name="NotoSansLao",
        regular_file="NotoSansLao-Regular.ttf",
        bold_file="NotoSansLao-Bold.ttf",
        scripts=[Script.LAO],
    ),
    "NotoSansKhmer": FontFamily(
        name="NotoSansKhmer",
        regular_file="NotoSansKhmer-Regular.ttf",
        bold_file="NotoSansKhmer-Bold.ttf",
        scripts=[Script.KHMER],
    ),
    "NotoSansMyanmar": FontFamily(
        name="NotoSansMyanmar",
        regular_file="NotoSansMyanmar-Regular.ttf",
        bold_file="NotoSansMyanmar-Bold.ttf",
        scripts=[Script.MYANMAR],
    ),

    # Ethiopic
    "NotoSansEthiopic": FontFamily(
        name="NotoSansEthiopic",
        regular_file="NotoSansEthiopic-Regular.ttf",
        bold_file="NotoSansEthiopic-Bold.ttf",
        scripts=[Script.ETHIOPIC],
    ),

    # Caucasian scripts
    "NotoSansArmenian": FontFamily(
        name="NotoSansArmenian",
        regular_file="NotoSansArmenian-Regular.ttf",
        bold_file="NotoSansArmenian-Bold.ttf",
        scripts=[Script.ARMENIAN],
    ),
    "NotoSansGeorgian": FontFamily(
        name="NotoSansGeorgian",
        regular_file="NotoSansGeorgian-Regular.ttf",
        bold_file="NotoSansGeorgian-Bold.ttf",
        scripts=[Script.GEORGIAN],
    ),
}


# =============================================================================
# SCRIPT TO FONT MAPPING
# =============================================================================
# Maps each Unicode script to a prioritized list of font families.
#
# HOW IT WORKS:
#   1. FontManager receives a Script enum value
#   2. Looks up the list of font family names here
#   3. Tries each font in order until one is available
#   4. First available font wins
#
# WHY FALLBACKS?
#   Some scripts include NotoSans as fallback for mixed content.
#   For example, Arabic text might include Latin numbers/punctuation.
#   The fallback ensures those characters render correctly.
#
# NOTE ON CJK:
#   CJK fonts have NO fallback because:
#   - They're very large (~16MB each)
#   - NotoSans cannot render CJK characters
#   - If CJK font is missing, we should fail fast with clear error

SCRIPT_TO_FONTS: Dict[Script, List[str]] = {
    # === LATIN-BASED SCRIPTS ===
    # These all use the base NotoSans font which includes full coverage
    Script.LATIN: ["NotoSans"],
    Script.CYRILLIC: ["NotoSans"],       # Russian, Ukrainian, Bulgarian
    Script.VIETNAMESE: ["NotoSans"],     # Latin + special diacritics
    Script.GREEK: ["NotoSans"],          # NotoSans includes Greek characters
    Script.MONGOLIAN: ["NotoSans"],      # Modern Mongolian uses Cyrillic script

    # === RIGHT-TO-LEFT SCRIPTS ===
    # Primary font for script, fallback for numbers/punctuation
    Script.ARABIC: ["NotoSansArabic", "NotoSans"],
    Script.HEBREW: ["NotoSansHebrew", "NotoSans"],

    # === CJK SCRIPTS (No fallback - must have dedicated font) ===
    Script.CJK_SIMPLIFIED: ["NotoSansSC"],   # Mainland China
    Script.CJK_TRADITIONAL: ["NotoSansTC"],  # Taiwan, Hong Kong, Cantonese
    Script.JAPANESE: ["NotoSansJP"],         # Kanji, Hiragana, Katakana
    Script.KOREAN: ["NotoSansKR"],           # Hangul

    # === SOUTH ASIAN SCRIPTS ===
    Script.DEVANAGARI: ["NotoSansDevanagari", "NotoSans"],  # Hindi, Nepali, Marathi
    Script.BENGALI: ["NotoSansBengali", "NotoSans"],
    Script.TAMIL: ["NotoSansTamil", "NotoSans"],
    Script.GURMUKHI: ["NotoSansGurmukhi", "NotoSans"],      # Punjabi

    # === SOUTHEAST ASIAN SCRIPTS ===
    Script.THAI: ["NotoSansThai", "NotoSans"],
    Script.LAO: ["NotoSansLao", "NotoSans"],
    Script.KHMER: ["NotoSansKhmer", "NotoSans"],            # Cambodian
    Script.MYANMAR: ["NotoSansMyanmar", "NotoSans"],        # Burmese, Karen

    # === OTHER SCRIPTS ===
    Script.ETHIOPIC: ["NotoSansEthiopic", "NotoSans"],      # Amharic, Tigrinya
    Script.ARMENIAN: ["NotoSansArmenian", "NotoSans"],
    Script.GEORGIAN: ["NotoSansGeorgian", "NotoSans"],
}


# =============================================================================
# SYSTEM FALLBACK FONTS
# =============================================================================
# These fonts are built into ReportLab and always available.
# Used when no Noto fonts are installed (basic ASCII only).
#
# WARNING: These fonts only support basic Latin characters!
# They should only be used as absolute last resort.

FALLBACK_FONT_REGULAR = "Helvetica"
FALLBACK_FONT_BOLD = "Helvetica-Bold"


# =============================================================================
# PUBLIC API FUNCTIONS
# =============================================================================

def get_font_families() -> Dict[str, FontFamily]:
    """
    Get all configured font families.

    Returns a copy of the FONT_FAMILIES dictionary to prevent
    accidental modification of the module-level configuration.

    RETURNS:
        Dictionary mapping font family names to FontFamily objects

    USAGE:
        families = get_font_families()
        for name, family in families.items():
            print(f"{name}: {family.regular_file}")
    """
    return FONT_FAMILIES.copy()


def get_fonts_for_script(script: Script) -> List[str]:
    """
    Get ordered list of font family names for a Unicode script.

    Returns the prioritized list of fonts that can render the given
    script. The first available font should be used.

    PARAMETERS:
        script: Script enum value (e.g., Script.ARABIC, Script.KOREAN)

    RETURNS:
        List of font family names in priority order
        Defaults to ["NotoSans"] if script not in mapping

    USAGE:
        fonts = get_fonts_for_script(Script.ARABIC)
        # Returns: ["NotoSansArabic", "NotoSans"]

        for font_name in fonts:
            if font_manager.is_font_available(font_name):
                return font_name
    """
    return SCRIPT_TO_FONTS.get(script, ["NotoSans"])
