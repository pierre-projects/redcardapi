from app.fonts import Script
from scripts.known_issues import KNOWN_CORRUPT
from scripts.validate_translations import missing_glyphs


def test_every_script_has_a_font(fonts):
    assert [s.name for s in Script if not fonts.is_script_supported(s)] == []


def test_every_card_character_has_a_glyph(store, fonts):
    """Catches a language mapped to the wrong script/font, or a missing font."""
    problems = {code: p for code, p in missing_glyphs(store).items() if code not in KNOWN_CORRUPT}
    assert problems == {}
