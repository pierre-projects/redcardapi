"""Line wrapping that respects spaces, grapheme clusters and RTL order."""

import unicodedata

from ..fonts import Script
from . import bidi
from .shaping import text_width

_CHARACTER_BREAK_SCRIPTS = frozenset({Script.CJK_SIMPLIFIED, Script.CJK_TRADITIONAL, Script.JAPANESE})

# Characters after which a line must not break: they join the next letter
# into the same cluster (viramas, Khmer coeng, joiners).
_JOINS_NEXT = frozenset("\u094D\u09CD\u0A4D\u0BCD\u0E3A\u0EBA\u1039\u17D2\u200D")
_JOINS_PREVIOUS = frozenset("\u200C\u200D")
# CJK punctuation that must not begin a line (kinsoku): keep with the previous character.
_NO_LINE_START = frozenset("，。、；：！？）」』》〉】.,;:!?)")


def _is_cluster_start(text: str, i: int) -> bool:
    """True if a line may break before text[i] without splitting a letter."""
    if i == 0:
        return True
    ch = text[i]
    if unicodedata.category(ch).startswith("M") or ch in _JOINS_PREVIOUS:
        return False
    return text[i - 1] not in _JOINS_NEXT


def _clusters(text: str) -> list[str]:
    clusters: list[str] = []
    for i, ch in enumerate(text):
        if clusters and not _is_cluster_start(text, i):
            clusters[-1] += ch
        else:
            clusters.append(ch)
    return clusters


def _fill(units: list[str], font: str, size: float, max_width: float) -> list[str]:
    """Greedily pack units (words with trailing space, or clusters) into lines."""
    lines: list[str] = []
    line = ""
    for unit in units:
        candidate = line + unit
        if line and text_width(candidate.rstrip(), font, size) > max_width:
            lines.append(line.rstrip())
            line = unit.lstrip()
        else:
            line = candidate
        # A single unit wider than the line: break it between clusters.
        while text_width(line.rstrip(), font, size) > max_width and len(_clusters(line)) > 1:
            parts = _clusters(line)
            head = ""
            for index, cluster in enumerate(parts):
                if head and text_width(head + cluster, font, size) > max_width:
                    lines.append(head)
                    line = "".join(parts[index:])
                    break
                head += cluster
            else:
                break
    if line.strip():
        lines.append(line.rstrip())
    return lines


def _words(text: str) -> list[str]:
    """Split on spaces, keeping each space attached to the preceding word."""
    words: list[str] = []
    for part in text.split(" "):
        if words:
            words[-1] += " "
        if part:
            words.append(part)
    return words


def wrap_text(text: str, font: str, size: float, max_width: float,
              script: Script = Script.LATIN, rtl: bool = False) -> list[str]:
    """Wrap one paragraph into lines.

    Lines stay in logical order, except Hebrew lines, which come back in visual
    order; Arabic-script lines are ordered when drawn (see pdf.draw).
    """
    text = " ".join((text or "").split())
    if not text:
        return []

    # CJK may break between any two characters. Other scripts break at spaces
    # (Thai, Lao, Khmer and Myanmar data separates phrases with them) and
    # fall back to cluster boundaries for runs too long for one line.
    if script in _CHARACTER_BREAK_SCRIPTS:
        units: list[str] = []
        for cluster in _clusters(text):
            if units and cluster[0] in _NO_LINE_START:
                units[-1] += cluster
            else:
                units.append(cluster)
    else:
        units = _words(text)

    lines = _fill(units, font, size, max_width)
    if rtl and script != Script.ARABIC:
        return [bidi.to_visual(line) for line in lines]
    return lines
