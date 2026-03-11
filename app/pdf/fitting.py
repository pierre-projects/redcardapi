"""Shared text fitting helpers for PDF card renderers."""

from dataclasses import dataclass
from typing import Callable, Iterable, Tuple

from .constants import (
    MIN_FONT_SCALE_FACTOR,
    MAX_FONT_SCALE_FACTOR,
    MIN_ABSOLUTE_FONT_SIZE,
    MAX_ABSOLUTE_FONT_SIZE,
    FIT_BINARY_SEARCH_STEPS,
)


@dataclass
class FitResult:
    """Result of a font-scale fitting pass."""

    scale: float
    fits: bool
    base_height: float
    fitted_height: float
    min_scale: float
    max_scale: float


def _compute_scale_bounds(
    base_scale: float,
    base_font_sizes: Iterable[int],
) -> Tuple[float, float]:
    """Clamp scale range using relative scale factors and absolute font-size caps."""
    min_scale = base_scale * MIN_FONT_SCALE_FACTOR
    max_scale = base_scale * MAX_FONT_SCALE_FACTOR

    for base_size in base_font_sizes:
        if base_size <= 0:
            continue
        min_scale = max(min_scale, MIN_ABSOLUTE_FONT_SIZE / base_size)
        max_scale = min(max_scale, MAX_ABSOLUTE_FONT_SIZE / base_size)

    if max_scale < min_scale:
        max_scale = min_scale

    return min_scale, max_scale


def find_best_fit_scale(
    *,
    base_scale: float,
    available_height: float,
    base_font_sizes: Iterable[int],
    measure_height: Callable[[float], float],
) -> FitResult:
    """
    Select the largest scale that fits available height.

    Strategy:
    - Clamp search range by relative limits + absolute font-size caps.
    - If base scale fits, search upward.
    - If base scale does not fit, search downward.
    """
    min_scale, max_scale = _compute_scale_bounds(base_scale, base_font_sizes)
    base_scale = max(min_scale, min(max_scale, base_scale))

    base_height = measure_height(base_scale)

    # Base scale fits: grow to the largest fitting value.
    if base_height <= available_height:
        low = base_scale
        high = max_scale
        best_scale = base_scale
        best_height = base_height

        for _ in range(FIT_BINARY_SEARCH_STEPS):
            if high - low <= 1e-4:
                break
            mid = (low + high) / 2.0
            mid_height = measure_height(mid)
            if mid_height <= available_height:
                low = mid
                best_scale = mid
                best_height = mid_height
            else:
                high = mid

        return FitResult(
            scale=best_scale,
            fits=True,
            base_height=base_height,
            fitted_height=best_height,
            min_scale=min_scale,
            max_scale=max_scale,
        )

    # Base does not fit: shrink to the largest fitting value.
    min_height = measure_height(min_scale)
    if min_height > available_height:
        return FitResult(
            scale=min_scale,
            fits=False,
            base_height=base_height,
            fitted_height=min_height,
            min_scale=min_scale,
            max_scale=max_scale,
        )

    low = min_scale
    high = base_scale
    best_scale = min_scale
    best_height = min_height

    for _ in range(FIT_BINARY_SEARCH_STEPS):
        if high - low <= 1e-4:
            break
        mid = (low + high) / 2.0
        mid_height = measure_height(mid)
        if mid_height <= available_height:
            low = mid
            best_scale = mid
            best_height = mid_height
        else:
            high = mid

    return FitResult(
        scale=best_scale,
        fits=True,
        base_height=base_height,
        fitted_height=best_height,
        min_scale=min_scale,
        max_scale=max_scale,
    )
