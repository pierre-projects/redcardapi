"""Registers the Noto fonts with ReportLab and picks one per language."""

import logging
import threading
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from ..exceptions import FontNotAvailableError
from .font_config import FONT_FAMILIES, SCRIPT_FONT
from .script_detector import Script, detect_script

logger = logging.getLogger(__name__)


class FontManager:
    def __init__(self, fonts_dir: Path):
        self.fonts_dir = Path(fonts_dir)
        self._registered: dict[str, bool] = {}

    def register_all(self) -> None:
        for family, files in FONT_FAMILIES.items():
            self._register(family, files.regular_file)
            self._register(f"{family}-Bold", files.bold_file)

        missing = [s.name for s in Script if not self.is_script_supported(s)]
        logger.info("Fonts registered: %d/%d scripts supported", len(Script) - len(missing), len(Script))
        if missing:
            logger.warning("No font for scripts: %s", ", ".join(missing))

    def _register(self, font_name: str, filename: str) -> None:
        path = self.fonts_dir / filename
        if not path.exists():
            logger.warning("Font file missing: %s", path)
            self._registered[font_name] = False
            return
        try:
            pdfmetrics.registerFont(TTFont(font_name, str(path)))
            self._registered[font_name] = True
        except Exception:
            logger.exception("Could not register font %s from %s", font_name, path)
            self._registered[font_name] = False

    def is_script_supported(self, script: Script) -> bool:
        family = SCRIPT_FONT.get(script)
        return bool(family and self._registered.get(family) and self._registered.get(f"{family}-Bold"))

    def pick(self, lang_code: str | None = None, bold: bool = False) -> str:
        """ReportLab font name for a language; raises if its script has no font."""
        script = detect_script(lang_code or "en")
        if not self.is_script_supported(script):
            raise FontNotAvailableError(script.name, lang_code or "en")
        family = SCRIPT_FONT[script]
        return f"{family}-Bold" if bold else family


_manager: FontManager | None = None
_lock = threading.Lock()


def init_font_manager(fonts_dir: Path) -> FontManager:
    """Register fonts once per process (safe to call from several threads)."""
    global _manager
    with _lock:
        if _manager is None:
            manager = FontManager(fonts_dir)
            manager.register_all()
            _manager = manager
    return _manager


def get_font_manager() -> FontManager:
    if _manager is None:
        from ..config import settings
        return init_font_manager(settings.fonts_dir)
    return _manager
