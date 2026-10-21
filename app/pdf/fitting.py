"""Find the largest text scale whose content fits a card."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from reportlab.lib.units import inch

from .constants import (
    BASE_BODY_SIZE,
    BASE_LEADING,
    BASE_TITLE_SIZE,
    FIT_BINARY_SEARCH_STEPS,
    MAX_ABSOLUTE_FONT_SIZE,
    MAX_FONT_SCALE_FACTOR,
    MIN_ABSOLUTE_FONT_SIZE,
    MIN_FONT_SCALE_FACTOR,
)


@dataclass(frozen=True)
class Typography:
    """Font sizes and spacing for one scale factor."""
    scale: float
    title_size: int
    body_size: int
    leading: int
    bullet_indent: float
    pad: float


def _clamp_size(size: float) -> int:
    return max(MIN_ABSOLUTE_FONT_SIZE, min(MAX_ABSOLUTE_FONT_SIZE, int(size)))


def typography(scale: float, line_height: float = 1.0) -> Typography:
    """Sizes for a scale; line_height > 1 for scripts with tall stacked glyphs."""
    return Typography(
        scale=scale,
        title_size=_clamp_size(BASE_TITLE_SIZE * scale),
        body_size=_clamp_size(BASE_BODY_SIZE * scale),
        leading=max(8, int(BASE_LEADING * scale * line_height)),
        bullet_indent=8 * scale,
        pad=0.12 * inch * scale + 0.06 * inch,
    )


@dataclass(frozen=True)
class FitResult:
    scale: float
    fits: bool


def _scale_bounds(base_scale: float, base_font_sizes: Iterable[int]) -> tuple[float, float]:
    """Relative limits around the layout's scale, tightened by absolute font-size caps."""
    low = base_scale * MIN_FONT_SCALE_FACTOR
    high = base_scale * MAX_FONT_SCALE_FACTOR
    for size in base_font_sizes:
        low = max(low, MIN_ABSOLUTE_FONT_SIZE / size)
        high = min(high, MAX_ABSOLUTE_FONT_SIZE / size)
    return low, max(low, high)


def find_best_fit_scale(*, base_scale: float, available_height: float,
                        base_font_sizes: Iterable[int],
                        measure_height: Callable[[float], float]) -> FitResult:
    """Binary-search the largest scale whose measured height fits.

    Searches upward from the layout's scale when it fits, downward otherwise.
    If even the smallest scale overflows, returns it with fits=False and the
    text is clipped at the card edge.
    """
    low_bound, high_bound = _scale_bounds(base_scale, base_font_sizes)
    base_scale = max(low_bound, min(high_bound, base_scale))

    if measure_height(base_scale) <= available_height:
        low, high = base_scale, high_bound
    elif measure_height(low_bound) <= available_height:
        low, high = low_bound, base_scale
    else:
        return FitResult(scale=low_bound, fits=False)

    for _ in range(FIT_BINARY_SEARCH_STEPS):
        if high - low <= 1e-4:
            break
        mid = (low + high) / 2
        if measure_height(mid) <= available_height:
            low = mid
        else:
            high = mid
    return FitResult(scale=low, fits=True)
