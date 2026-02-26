"""
Text Wrapping with CJK Support.

=============================================================================
MODULE OVERVIEW
=============================================================================

Provides intelligent text wrapping that handles:
- Latin/European text: word-boundary wrapping (via simpleSplit)
- No-space scripts: character-boundary wrapping (CJK, Thai, Lao, Khmer, Myanmar)
- Mixed text: hybrid approach

Integrates with existing Script enum from fonts.script_detector.

=============================================================================
WHY SPECIAL CJK HANDLING?
=============================================================================

CJK (Chinese, Japanese, Korean) languages have fundamentally different
word boundaries than European languages:

- European: "Hello world" has a clear space between words
- Chinese: "你好世界" has no spaces - each character can be a break point
- Japanese: "こんにちは" mixes scripts with no clear word boundaries

ReportLab's simpleSplit() wraps at whitespace, which doesn't work for CJK.
This module provides character-by-character wrapping for CJK text.

=============================================================================
USAGE
=============================================================================

    from app.text import wrap_text

    # Automatic detection (examines text for CJK characters)
    lines = wrap_text("你好世界", font_name, font_size, max_width)

    # With language hint (more reliable)
    lines = wrap_text(text, font_name, font_size, max_width, lang_code="zh-TW")

=============================================================================
"""

from typing import List, Optional
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics

from app.fonts.script_detector import Script, detect_script


# =============================================================================
# CJK SCRIPT DETECTION
# =============================================================================

# Scripts that require character-by-character wrapping
CJK_SCRIPTS = frozenset({
    Script.CJK_SIMPLIFIED,
    Script.CJK_TRADITIONAL,
    Script.JAPANESE,
    Script.KOREAN,
})

# Scripts where whitespace-based wrapping is unreliable and character
# wrapping is safer as a default.
NO_SPACE_SCRIPTS = frozenset({
    Script.CJK_SIMPLIFIED,
    Script.CJK_TRADITIONAL,
    Script.JAPANESE,
    Script.KOREAN,
    Script.THAI,
    Script.LAO,
    Script.KHMER,
    Script.MYANMAR,
})


def is_cjk_script(script: Script) -> bool:
    """
    Check if a script requires character-based wrapping.

    Args:
        script: Script enum value from script_detector

    Returns:
        True if the script is CJK (Chinese, Japanese, or Korean)
    """
    return script in CJK_SCRIPTS


def is_no_space_script(script: Script) -> bool:
    """
    Check if script should use character-level wrapping by default.

    Args:
        script: Script enum value from script_detector

    Returns:
        True if the script generally does not rely on spaces for safe wrapping
    """
    return script in NO_SPACE_SCRIPTS


def is_cjk_char(char: str) -> bool:
    """
    Check if a character is CJK (Chinese/Japanese/Korean).

    Unicode ranges covered:
    - CJK Unified Ideographs (Chinese characters used in CN/TW/JP)
    - CJK Extension A (rare characters)
    - CJK Punctuation (fullwidth punctuation marks)
    - Fullwidth Forms (fullwidth ASCII variants)
    - Hiragana (Japanese phonetic script)
    - Katakana (Japanese phonetic script for foreign words)
    - Hangul Syllables (Korean)

    Args:
        char: Single character to check

    Returns:
        True if the character is CJK
    """
    code = ord(char)
    return (
        0x4E00 <= code <= 0x9FFF or    # CJK Unified Ideographs
        0x3400 <= code <= 0x4DBF or    # CJK Extension A
        0x3000 <= code <= 0x303F or    # CJK Punctuation
        0xFF00 <= code <= 0xFFEF or    # Fullwidth Forms
        0x3040 <= code <= 0x309F or    # Hiragana
        0x30A0 <= code <= 0x30FF or    # Katakana
        0xAC00 <= code <= 0xD7AF       # Hangul Syllables
    )


def is_cjk_text(text: str) -> bool:
    """
    Check if text contains CJK characters.

    This is used for automatic detection when no language code is provided.

    Args:
        text: Text to examine

    Returns:
        True if any character in the text is CJK
    """
    return any(is_cjk_char(c) for c in text)


# =============================================================================
# TEXT WRAPPING FUNCTIONS
# =============================================================================

def _wrap_cjk(
    text: str,
    font_name: str,
    font_size: int,
    max_width: float
) -> List[str]:
    """
    Wrap CJK text character-by-character.

    CJK languages can break at almost any character boundary,
    so we measure width as we accumulate characters and break
    when approaching max_width.

    Algorithm:
    1. Start with empty line
    2. For each character:
       a. Measure character width
       b. If adding it exceeds max_width, start new line
       c. Otherwise, append to current line
    3. Return list of lines

    Args:
        text: CJK text to wrap
        font_name: ReportLab font name
        font_size: Font size in points
        max_width: Maximum line width in points

    Returns:
        List of wrapped lines
    """
    return _wrap_by_character(text, font_name, font_size, max_width)


def _wrap_by_character(
    text: str,
    font_name: str,
    font_size: int,
    max_width: float
) -> List[str]:
    """
    Wrap text by character boundaries.

    This is used for scripts where whitespace wrapping is unreliable and as a
    fallback safety mechanism for any line that still overflows.
    """
    if not text:
        return []

    lines: List[str] = []
    current_line = ""
    current_width = 0.0

    for char in text:
        char_width = pdfmetrics.stringWidth(char, font_name, font_size)
        if current_width + char_width > max_width and current_line:
            lines.append(current_line)
            current_line = char
            current_width = char_width
        else:
            current_line += char
            current_width += char_width

    if current_line:
        lines.append(current_line)

    return lines


def _line_width(text: str, font_name: str, font_size: int) -> float:
    """Measure rendered width for a single line."""
    return pdfmetrics.stringWidth(text, font_name, font_size)


def _enforce_max_width(
    lines: List[str],
    font_name: str,
    font_size: int,
    max_width: float,
) -> List[str]:
    """
    Ensure every returned line is within max_width whenever possible.

    If a line from simpleSplit still overflows (typically long no-space runs),
    split that line with character-level wrapping.
    """
    safe_lines: List[str] = []
    for line in lines:
        if not line:
            safe_lines.append(line)
            continue

        if _line_width(line, font_name, font_size) <= max_width:
            safe_lines.append(line)
            continue

        safe_lines.extend(_wrap_by_character(line, font_name, font_size, max_width))

    return safe_lines


def wrap_text(
    text: str,
    font_name: str,
    font_size: int,
    max_width: float,
    lang_code: Optional[str] = None
) -> List[str]:
    """
    Wrap text to fit within max_width, with support for no-space scripts.

    Strategy:
    - No-space scripts: character-by-character wrapping
    - Other scripts: word-by-word via ReportLab's simpleSplit
    - Safety pass: if any line still overflows, split it by characters

    Args:
        text: Text to wrap
        font_name: ReportLab font name for width calculation
        font_size: Font size in points
        max_width: Maximum line width in points
        lang_code: Optional language hint (e.g., "zh-TW", "ja", "ko").
                   If provided, uses script detection for more reliable results.
                   If not provided, examines text for CJK characters.

    Returns:
        List of wrapped lines that fit within max_width

    Example:
        # With language hint (recommended)
        lines = wrap_text("你好世界", "NotoSansSC", 12, 200, lang_code="zh-CN")

        # Without hint (auto-detection)
        lines = wrap_text("Hello world", "Helvetica", 12, 200)
    """
    if not text:
        return []

    # Determine if character-based wrapping is needed
    use_char_wrap = False
    if lang_code:
        # Use language code for reliable script detection
        script = detect_script(lang_code)
        use_char_wrap = is_no_space_script(script)
    else:
        # Fall back to CJK content detection when language hint isn't available
        use_char_wrap = is_cjk_text(text)

    if use_char_wrap:
        lines = _wrap_by_character(text, font_name, font_size, max_width)
    else:
        lines = simpleSplit(text, font_name, font_size, max_width)

    return _enforce_max_width(lines, font_name, font_size, max_width)
