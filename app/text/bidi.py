"""Right-to-left line layout.

Arabic-script text (Arabic, Farsi, Dari, Pashto, Urdu) is shaped by HarfBuzz
(see shaping.py), which joins every letter of those alphabets and returns an
RTL run's glyphs in visual order. What remains is ordering *runs* within a
line: left-to-right runs (Latin words, digits) keep their own order, but the
runs themselves are laid out right to left.

Hebrew needs no joining, so its lines are reordered with the Unicode bidi
algorithm instead. (HarfBuzz would also apply the Hebrew font's alef-lamed
ligature, which modern Hebrew does not use.)
"""

import re

from bidi.algorithm import get_display

_ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
# A left-to-right run: Latin letters or digits, with joining punctuation.
_LATIN = r"A-Za-z0-9\u00C0-\u024F"
_LTR_RUN = re.compile(rf"[{_LATIN}](?:[{_LATIN}.,:/@%+\-]*[{_LATIN}%])?")


def is_arabic_script(text: str) -> bool:
    return bool(_ARABIC.search(text))


def visual_runs(line: str) -> list[str]:
    """Split a right-to-left line into runs, ordered left to right as drawn."""
    runs: list[str] = []
    position = 0
    for match in _LTR_RUN.finditer(line):
        if match.start() > position:
            runs.append(line[position:match.start()])
        runs.append(match.group())
        position = match.end()
    if position < len(line):
        runs.append(line[position:])
    return runs[::-1]


def to_visual(line: str) -> str:
    """Visual (left-to-right drawing) order for one wrapped Hebrew line."""
    return get_display(line, base_dir="R") if line else line
