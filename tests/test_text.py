import unicodedata

import pytest

from app.fonts import Script
from app.text import text_width, wrap_text
from app.text.shaping import needs_shaping


@pytest.fixture(autouse=True)
def _fonts(fonts):
    return fonts


def test_latin_wraps_at_spaces_within_width():
    text = "I do not wish to speak with you or answer your questions."
    lines = wrap_text(text, "NotoSans", 10, 120)
    assert len(lines) > 1
    assert " ".join(lines) == text
    assert all(text_width(line, "NotoSans", 10) <= 120 for line in lines)


def test_shaped_width_differs_for_conjuncts():
    word = "क्षत्रिय"
    assert needs_shaping(word)
    from reportlab.pdfbase import pdfmetrics
    assert text_width(word, "NotoSans", 20) < pdfmetrics.stringWidth(word, "NotoSans", 20)


def test_never_breaks_inside_a_cluster():
    # Long Khmer run with no spaces: must break, but never before a mark or after a coeng.
    text = "សិទ្ធិ" * 30
    lines = wrap_text(text, "NotoSansKhmer", 10, 80, Script.KHMER)
    assert len(lines) > 1
    for line in lines:
        assert not unicodedata.category(line[0]).startswith("M")
        assert line[-1] != "្"


def test_cjk_lines_do_not_start_with_closing_punctuation():
    text = "如果移民调查员敲门，不要开门。" * 6
    lines = wrap_text(text, "NotoSansSC", 10, 60, Script.CJK_SIMPLIFIED)
    assert len(lines) > 1
    assert all(line[0] not in "，。" for line in lines)


def test_rtl_lines_keep_sentence_order():
    # The first line holds the beginning of the sentence (bidi used to run on
    # the whole paragraph, putting its end on the first line).
    words = ["أول", "ثاني", "ثالث", "رابع", "خامس", "سادس", "سابع", "ثامن"]
    lines = wrap_text(" ".join(words), "NotoSansArabic", 12, 70, Script.ARABIC, rtl=True)
    assert len(lines) > 1
    assert lines[0].startswith(words[0])
    assert lines[-1].endswith(words[-1])


def test_pashto_letters_are_joined():
    # Pashto-specific letters must take joining forms; unshaped they print
    # isolated (the reshaper used before did not know them).
    from reportlab.pdfbase import pdfmetrics

    from app.text.shaping import shape
    word = "پوښتنی"
    shaped = shape(word, "NotoSansArabic", 20)
    assert str(shaped) != word  # contextual glyphs, not the isolated letters
    assert text_width(word, "NotoSansArabic", 20) < pdfmetrics.stringWidth(word, "NotoSansArabic", 20)


def test_rtl_runs_keep_latin_and_digits_left_to_right():
    from app.text.bidi import visual_runs
    # Runs keep their logical text; only their order is reversed.
    assert visual_runs("اتصل بالرقم 911 الآن") == [" الآن", "911", "اتصل بالرقم "]
    assert visual_runs("لا شيء") == ["لا شيء"]


def test_hebrew_lines_come_back_in_visual_order():
    lines = wrap_text("אל תפתח את הדלת", "NotoSansHebrew", 12, 500, Script.HEBREW, rtl=True)
    assert lines == ["תלדה תא חתפת לא"]
