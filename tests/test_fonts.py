from app.fonts import Script
from scripts.validate_translations import missing_glyphs
from tests.known_issues import KNOWN_CORRUPT


def test_every_script_has_a_font(fonts):
    assert [s.name for s in Script if not fonts.is_script_supported(s)] == []


def test_every_card_character_has_a_glyph(store, fonts):
    """Catches a language mapped to the wrong script/font, or a missing font."""
    problems = [p for p in missing_glyphs(store) if p.split(":")[0] not in KNOWN_CORRUPT]
    assert problems == []
