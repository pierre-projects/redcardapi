"""Script detection and font selection for PDF rendering."""

from .font_manager import FontManager, get_font_manager, init_font_manager
from .script_detector import Script, detect_script

__all__ = ["FontManager", "Script", "detect_script", "get_font_manager", "init_font_manager"]
