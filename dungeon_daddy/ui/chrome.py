"""
Chrome drawing helpers — title bar and mode pills.
Called at the start of every on_draw() in both views, before UIManager.draw().
Uses arcade.draw_* primitives directly (not part of the UIManager tree).
"""
from __future__ import annotations

from collections.abc import Callable

import arcade

from dungeon_daddy.ui.theme import (
    BG_1,
    BG_2,
    CHROME_MENUBAR_HEIGHT,
    CHROME_TITLEBAR_HEIGHT,
    EMBER,
    FONT_UI_MED,
    GOLD,
    INK_3,
    LINE,
    PAD_MD,
    TEAL,
    TEXT_MD,
    TEXT_SM,
    VIOLET,
)

# ---------------------------------------------------------------------------
# Three-pill mode switcher
# ---------------------------------------------------------------------------

_PILL_W = 90
_PILL_H = 22
_PILL_GAP = 8
_PILL_MODES = ["library"]
PILLS_CLUSTER_W = len(_PILL_MODES) * _PILL_W + (len(_PILL_MODES) - 1) * _PILL_GAP
_PILL_FILL: dict[str, tuple[int, ...]] = {
    "library":  EMBER,
    "design":   VIOLET,
    "campaign": GOLD,
    "play":     TEAL,
}


def _pill_rect(mode: str, window: object) -> tuple[float, float, float, float]:
    """Return (left, bottom, right, top) of a mode pill in window coordinates."""
    w: int = window.width  # type: ignore[attr-defined]
    h: int = window.height  # type: ignore[attr-defined]
    bar_top = h - CHROME_MENUBAR_HEIGHT
    bar_mid = bar_top - CHROME_TITLEBAR_HEIGHT / 2
    total_w = len(_PILL_MODES) * _PILL_W + (len(_PILL_MODES) - 1) * _PILL_GAP
    right_edge = float(w) - PAD_MD
    idx = _PILL_MODES.index(mode)
    cx = right_edge - total_w + idx * (_PILL_W + _PILL_GAP) + _PILL_W / 2
    return (
        cx - _PILL_W / 2,
        bar_mid - _PILL_H / 2,
        cx + _PILL_W / 2,
        bar_mid + _PILL_H / 2,
    )


def title_bar_mode_at(x: float, y: float, window: object) -> str | None:
    """Return which mode pill was clicked, or None if the click is outside all pills."""
    try:
        h: int = window.height  # type: ignore[attr-defined]
        bar_top = h - CHROME_MENUBAR_HEIGHT
        bar_bottom = bar_top - CHROME_TITLEBAR_HEIGHT
        if not (bar_bottom <= y <= bar_top):
            return None
        for mode in _PILL_MODES:
            left, bot, right, top = _pill_rect(mode, window)
            if left <= x <= right and bot <= y <= top:
                return mode
    except TypeError:
        return None
    return None


# ---------------------------------------------------------------------------
# Title bar  (44 px at the top of the window)
# ---------------------------------------------------------------------------

def draw_title_bar(
    window: object,
    mode: str,
    on_mode: Callable[[str], None] | None = None,
) -> None:
    """
    Draw the title bar with app name and Library home pill.
    mode: active view name — "library" pill is filled when library is active.
    on_mode: unused (click detection is handled by the views via title_bar_mode_at).
    """
    w: int = window.width  # type: ignore[attr-defined]
    h: int = window.height  # type: ignore[attr-defined]
    bar_top = h - CHROME_MENUBAR_HEIGHT
    bar_mid = bar_top - CHROME_TITLEBAR_HEIGHT / 2

    # Background
    arcade.draw_rect_filled(
        arcade.XYWH(w / 2, bar_mid, w, CHROME_TITLEBAR_HEIGHT),
        BG_1,
    )

    # Bottom border
    arcade.draw_line(
        0, bar_top - CHROME_TITLEBAR_HEIGHT,
        w, bar_top - CHROME_TITLEBAR_HEIGHT,
        LINE, 1,
    )

    # App title
    arcade.draw_text(
        "DUNGEON DADDY",
        PAD_MD, bar_mid,
        TEAL,
        font_size=TEXT_MD,
        font_name=FONT_UI_MED,
        anchor_x="left",
        anchor_y="center",
    )

    # Mode pills — active pill filled with accent colour; inactive: BG_2 + LINE border
    for pill_mode in _PILL_MODES:
        left, bot, right, top = _pill_rect(pill_mode, window)
        cx = (left + right) / 2
        cy = (bot + top) / 2
        is_active = pill_mode == mode
        fill = _PILL_FILL[pill_mode] if is_active else BG_2
        label_color = BG_1 if is_active else INK_3
        border = _PILL_FILL[pill_mode] if is_active else LINE
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, _PILL_W, _PILL_H), fill)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, _PILL_W, _PILL_H), border, 1)
        arcade.draw_text(
            pill_mode.upper(), cx, cy, label_color,
            font_size=TEXT_SM, font_name=FONT_UI_MED,
            anchor_x="center", anchor_y="center",
        )
