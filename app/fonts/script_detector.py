"""Which writing system each language uses, which decides its font."""

from enum import Enum, auto


class Script(Enum):
    LATIN = auto()
    CYRILLIC = auto()
    GREEK = auto()
    ARABIC = auto()
    HEBREW = auto()
    CJK_SIMPLIFIED = auto()
    CJK_TRADITIONAL = auto()
    JAPANESE = auto()
    KOREAN = auto()
    DEVANAGARI = auto()
    BENGALI = auto()
    TAMIL = auto()
    GURMUKHI = auto()
    THAI = auto()
    LAO = auto()
    KHMER = auto()
    MYANMAR = auto()
    ETHIOPIC = auto()
    ARMENIAN = auto()
    GEORGIAN = auto()


# Languages not listed use LATIN (NotoSans, which also covers Vietnamese
# diacritics). tests/test_fonts.py fails if a card uses a glyph its font
# lacks, so a missing entry here cannot slip through.
LANGUAGE_TO_SCRIPT: dict[str, Script] = {
    "ru": Script.CYRILLIC,
    "uk": Script.CYRILLIC,
    "mn": Script.CYRILLIC,
    "bg": Script.CYRILLIC,
    "sr": Script.CYRILLIC,
    "mk": Script.CYRILLIC,
    "el": Script.GREEK,
    "ar": Script.ARABIC,
    "fa": Script.ARABIC,
    "prs": Script.ARABIC,
    "ps": Script.ARABIC,
    "ur": Script.ARABIC,
    "ku": Script.ARABIC,
    "he": Script.HEBREW,
    "zh-cn": Script.CJK_SIMPLIFIED,
    "zh-tw": Script.CJK_TRADITIONAL,
    "yue": Script.CJK_TRADITIONAL,
    "ja": Script.JAPANESE,
    "ko": Script.KOREAN,
    "hi": Script.DEVANAGARI,
    "ne": Script.DEVANAGARI,
    "mr": Script.DEVANAGARI,
    "bn": Script.BENGALI,
    "ta": Script.TAMIL,
    "pa": Script.GURMUKHI,
    "th": Script.THAI,
    "lo": Script.LAO,
    "km": Script.KHMER,
    "my": Script.MYANMAR,
    "kar": Script.MYANMAR,  # S'gaw Karen is written in Myanmar script
    "am": Script.ETHIOPIC,
    "ti": Script.ETHIOPIC,
    "hy": Script.ARMENIAN,
    "ka": Script.GEORGIAN,
}

def detect_script(lang_code: str) -> Script:
    return LANGUAGE_TO_SCRIPT.get((lang_code or "").lower(), Script.LATIN)
