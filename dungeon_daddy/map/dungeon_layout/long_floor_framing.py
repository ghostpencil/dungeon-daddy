"""Detection and framing helpers for long linear floor layouts.

Pure geometry — no Arcade dependency.
"""
from __future__ import annotations

from dungeon_daddy.map.dungeon_layout.models import LayoutBounds

_LONG_LINEAR_ASPECT_THRESHOLD = 2.0
_MIN_READABLE_ZOOM = 0.5


def is_long_linear_floor(bounds: LayoutBounds) -> bool:
    """Return True when the layout is much wider than it is tall."""
    if bounds.height == 0:
        return False
    return (bounds.width / bounds.height) > _LONG_LINEAR_ASPECT_THRESHOLD


def compute_long_floor_framing_feedback(
    bounds: LayoutBounds,
    fit_zoom: float | None = None,
) -> dict:
    """Return a framing feedback dict for the given layout bounds."""
    if not is_long_linear_floor(bounds):
        return {"is_long_linear_floor": False}

    warnings: list[str] = []
    labels_readable = True
    if fit_zoom is not None and fit_zoom < _MIN_READABLE_ZOOM:
        labels_readable = False
        warnings.append(
            f"Fit zoom {fit_zoom:.2f} is below readable threshold {_MIN_READABLE_ZOOM}; "
            "labels may be too small"
        )

    return {
        "is_long_linear_floor": True,
        "labels_readable_after_fit": labels_readable,
        "warnings": warnings,
    }
