"""Text wrapping helpers for card rendering."""

from typing import List, Optional

from ..text import wrap_text
from .rtl import prepare_rtl_text


def wrap_lines(
    text: str,
    font_name: str,
    font_size: int,
    max_width: float,
    rtl: bool = False,
    lang_code: Optional[str] = None,
) -> List[str]:
    """
    Wrap text to fit within max width with optional RTL preprocessing.
    """
    if rtl:
        text = prepare_rtl_text(text)

    lines: List[str] = []
    for paragraph in (text or "").split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        lines.extend(wrap_text(paragraph, font_name, font_size, max_width, lang_code=lang_code))

    return lines

