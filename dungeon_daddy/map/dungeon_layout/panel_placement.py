"""Collision-avoiding placement for the Graph Mode detail panel.

Pure geometry — no Arcade dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_MARGIN = 10.0


@dataclass
class ScreenRect:
    x: float  # left edge
    y: float  # bottom edge (Arcade: y=0 is bottom of screen)
    w: float
    h: float


@dataclass
class PanelPlacement:
    x: float  # left edge of placed panel
    y: float  # bottom edge of placed panel (panel grows upward)
    fallback_used: bool = False
    warnings: list[str] = field(default_factory=list)


def _overlaps(panel_x: float, panel_y: float, panel_w: float, panel_h: float, r: ScreenRect) -> bool:
    return (
        panel_x < r.x + r.w and panel_x + panel_w > r.x
        and panel_y < r.y + r.h and panel_y + panel_h > r.y
    )


def _clamp(px: float, py: float, panel_w: float, panel_h: float, vp: ScreenRect) -> tuple[float, float]:
    px = max(vp.x, min(px, vp.x + vp.w - panel_w))
    py = max(vp.y, min(py, vp.y + vp.h - panel_h))
    return px, py


def compute_panel_position(
    panel_w: float,
    panel_h: float,
    viewport: ScreenRect,
    preferred_x: float,
    preferred_y: float,
    selected_rect: ScreenRect | None = None,
    connected_rects: list[ScreenRect] | None = None,
) -> PanelPlacement:
    """Return the best non-overlapping panel position within *viewport*.

    Tries the preferred position first, then four fixed-corner alternates, then
    positions relative to the selected room.  If every candidate overlaps, falls
    back to the (clamped) preferred position and attaches a warning.
    """
    vp = viewport

    def _blocks(px: float, py: float) -> bool:
        if selected_rect and _overlaps(px, py, panel_w, panel_h, selected_rect):
            return True
        for cr in (connected_rects or []):
            if _overlaps(px, py, panel_w, panel_h, cr):
                return True
        return False

    # Corner anchors
    right_x = vp.x + vp.w - panel_w - _MARGIN
    left_x = vp.x + _MARGIN
    bottom_y = vp.y + _MARGIN
    top_y = vp.y + vp.h - panel_h - _MARGIN

    candidates: list[tuple[float, float]] = [
        (preferred_x, preferred_y),   # preferred (typically bottom-right)
        (left_x, bottom_y),           # bottom-left
        (right_x, top_y),             # top-right
        (left_x, top_y),              # top-left
    ]
    if selected_rect is not None:
        sel = selected_rect
        # Below selected room (panel top at room bottom)
        candidates.append((right_x, sel.y - panel_h - _MARGIN))
        # Above selected room (panel bottom at room top)
        candidates.append((right_x, sel.y + sel.h + _MARGIN))

    for i, (cx, cy) in enumerate(candidates):
        cx, cy = _clamp(cx, cy, panel_w, panel_h, vp)
        if not _blocks(cx, cy):
            return PanelPlacement(x=cx, y=cy, fallback_used=i > 0)

    # No clean position found — use preferred, clamped
    cx, cy = _clamp(preferred_x, preferred_y, panel_w, panel_h, vp)
    return PanelPlacement(
        x=cx, y=cy,
        fallback_used=True,
        warnings=["No non-overlapping panel position found; using preferred position"],
    )
