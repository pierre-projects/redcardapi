"""Right-to-left text support helpers."""

from ..logging_config import get_logger

logger = get_logger("pdf_renderer")

_rtl_available = None


def check_rtl_support() -> bool:
    """Check whether optional RTL libraries are installed."""
    global _rtl_available

    if _rtl_available is None:
        try:
            import arabic_reshaper  # noqa: F401
            from bidi.algorithm import get_display  # noqa: F401
            _rtl_available = True
            logger.info("RTL support enabled (arabic-reshaper + python-bidi)")
        except ImportError as exc:
            _rtl_available = False
            logger.warning(f"RTL support disabled: {exc}")

    return _rtl_available


def prepare_rtl_text(text: str) -> str:
    """
    Reshape and reorder RTL text for PDF rendering.

    Maintains existing behavior used in the legacy renderer.
    """
    if not text or not check_rtl_support():
        return text

    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception as exc:
        logger.warning(f"RTL text processing failed: {exc}")
        return text

