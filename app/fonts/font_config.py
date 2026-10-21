"""Font files in assets/fonts and the font used for each script."""

from dataclasses import dataclass

from .script_detector import Script


@dataclass(frozen=True)
class FontFamily:
    regular_file: str
    bold_file: str


def _noto(stem: str) -> FontFamily:
    return FontFamily(f"{stem}-Regular.ttf", f"{stem}-Bold.ttf")


# Registered with ReportLab under the key (regular) and "<key>-Bold".
FONT_FAMILIES: dict[str, FontFamily] = {
    name: _noto(name)
    for name in (
        "NotoSans",
        "NotoSansArabic",
        "NotoSansHebrew",
        "NotoSansSC",
        "NotoSansTC",
        "NotoSansJP",
        "NotoSansKR",
        "NotoSansBengali",
        "NotoSansTamil",
        "NotoSansGurmukhi",
        "NotoSansThai",
        "NotoSansLao",
        "NotoSansKhmer",
        "NotoSansMyanmar",
        "NotoSansEthiopic",
        "NotoSansArmenian",
        "NotoSansGeorgian",
    )
}

# One font per script. A script is only "supported" when its font is
# registered: falling back to another font would print missing glyphs.
# NotoSans includes Latin, Cyrillic, Greek and Devanagari.
SCRIPT_FONT: dict[Script, str] = {
    Script.LATIN: "NotoSans",
    Script.CYRILLIC: "NotoSans",
    Script.GREEK: "NotoSans",
    Script.DEVANAGARI: "NotoSans",
    Script.ARABIC: "NotoSansArabic",
    Script.HEBREW: "NotoSansHebrew",
    Script.CJK_SIMPLIFIED: "NotoSansSC",
    Script.CJK_TRADITIONAL: "NotoSansTC",
    Script.JAPANESE: "NotoSansJP",
    Script.KOREAN: "NotoSansKR",
    Script.BENGALI: "NotoSansBengali",
    Script.TAMIL: "NotoSansTamil",
    Script.GURMUKHI: "NotoSansGurmukhi",
    Script.THAI: "NotoSansThai",
    Script.LAO: "NotoSansLao",
    Script.KHMER: "NotoSansKhmer",
    Script.MYANMAR: "NotoSansMyanmar",
    Script.ETHIOPIC: "NotoSansEthiopic",
    Script.ARMENIAN: "NotoSansArmenian",
    Script.GEORGIAN: "NotoSansGeorgian",
}
