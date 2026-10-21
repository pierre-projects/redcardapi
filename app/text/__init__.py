"""Text preparation for PDF rendering: shaping, bidi and line wrapping."""

from .shaping import shape, text_width
from .wrap import wrap_text

__all__ = ["shape", "text_width", "wrap_text"]
