"""Tests for panel_placement — collision-avoiding detail panel positioning."""
from dungeon_daddy.map.dungeon_layout.panel_placement import (
    ScreenRect,
    compute_panel_position,
)


def _no_overlap(px: float, py: float, pw: float, ph: float, r: ScreenRect) -> bool:
    """Return True if panel rect does NOT overlap r."""
    return not (
        px < r.x + r.w and px + pw > r.x
        and py < r.y + r.h and py + ph > r.y
    )


# ---------------------------------------------------------------------------
# Cycle 1 — No selection: returns preferred position unchanged
# ---------------------------------------------------------------------------

def test_no_selection_returns_preferred():
    result = compute_panel_position(
        panel_w=300, panel_h=100,
        viewport=ScreenRect(0, 0, 800, 600),
        preferred_x=480, preferred_y=20,
    )
    assert result.x == 480
    assert result.y == 20
    assert not result.fallback_used
    assert result.warnings == []


# ---------------------------------------------------------------------------
# Cycle 2 — No overlap: returns preferred position unchanged
# ---------------------------------------------------------------------------

def test_no_overlap_returns_preferred():
    # Panel at x=[480,780] y=[20,120]; selected room at x=[0,100] y=[400,500]
    result = compute_panel_position(
        panel_w=300, panel_h=100,
        viewport=ScreenRect(0, 0, 800, 600),
        preferred_x=480, preferred_y=20,
        selected_rect=ScreenRect(0, 400, 100, 100),
    )
    assert result.x == 480
    assert result.y == 20
    assert not result.fallback_used


# ---------------------------------------------------------------------------
# Cycle 3 — Overlap with selected: panel moves to non-overlapping position
# ---------------------------------------------------------------------------

def test_overlap_with_selected_moves_panel():
    # Panel preferred at x=[480,780] y=[20,120]
    # Selected room at x=[500,700] y=[10,130] — overlaps panel
    selected = ScreenRect(500, 10, 200, 120)
    result = compute_panel_position(
        panel_w=300, panel_h=100,
        viewport=ScreenRect(0, 0, 800, 600),
        preferred_x=480, preferred_y=20,
        selected_rect=selected,
    )
    assert _no_overlap(result.x, result.y, 300, 100, selected)
    assert result.fallback_used


# ---------------------------------------------------------------------------
# Cycle 4 — Panel always inside viewport bounds
# ---------------------------------------------------------------------------

def test_preferred_outside_viewport_is_clamped():
    # preferred_x=600 → panel right edge would be 900, beyond viewport width 800
    result = compute_panel_position(
        panel_w=300, panel_h=100,
        viewport=ScreenRect(0, 0, 800, 600),
        preferred_x=600, preferred_y=20,
    )
    assert result.x >= 0
    assert result.x + 300 <= 800
    assert result.y >= 0
    assert result.y + 100 <= 600


def test_panel_stays_inside_offset_viewport():
    # Viewport starts at (100, 50) — panel must stay within it
    result = compute_panel_position(
        panel_w=300, panel_h=100,
        viewport=ScreenRect(100, 50, 800, 600),
        preferred_x=800, preferred_y=60,
    )
    assert result.x >= 100
    assert result.x + 300 <= 900
    assert result.y >= 50
    assert result.y + 100 <= 650


# ---------------------------------------------------------------------------
# Cycle 5 — Overlap with connected rooms also triggers fallback
# ---------------------------------------------------------------------------

def test_overlap_with_connected_room_moves_panel():
    # Selected room is far away; connected room overlaps panel
    selected = ScreenRect(0, 400, 50, 50)
    connected = ScreenRect(500, 10, 200, 120)  # overlaps preferred panel position
    result = compute_panel_position(
        panel_w=300, panel_h=100,
        viewport=ScreenRect(0, 0, 800, 600),
        preferred_x=480, preferred_y=20,
        selected_rect=selected,
        connected_rects=[connected],
    )
    assert _no_overlap(result.x, result.y, 300, 100, connected)
    assert result.fallback_used


# ---------------------------------------------------------------------------
# Cycle 6 — No clean position: returns preferred with warning
# ---------------------------------------------------------------------------

def test_no_clean_position_returns_warning():
    # Giant room fills entire viewport — every candidate will overlap
    huge_room = ScreenRect(0, 0, 800, 600)
    result = compute_panel_position(
        panel_w=300, panel_h=100,
        viewport=ScreenRect(0, 0, 800, 600),
        preferred_x=10, preferred_y=10,
        selected_rect=huge_room,
    )
    assert result.fallback_used
    assert len(result.warnings) > 0
