"""Tests for MapPanel loop toggle strip (F-27)."""
from __future__ import annotations

from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_panel(on_activate_loop=None):
    from dungeon_daddy.ui.panels.map_panel import MapPanel
    renderer = MagicMock()
    renderer.cell_px = 48
    panel = MapPanel(
        on_level_change=lambda d: None,
        renderer=renderer,
        overlay=MagicMock(),
        on_activate_loop=on_activate_loop,
    )
    panel._x, panel._y, panel._w, panel._h = 440.0, 0.0, 800.0, 600.0
    return panel


def _make_loop(loop_id="loop1", pattern="lock_key", loop_type="main"):
    from dungeon_daddy.data.models import Loop
    return Loop(
        id=loop_id, pattern=pattern, note="", entry="r1", goal="r2",
        path_a=["r1", "r2"], path_b=["r1", "r3", "r2"], type=loop_type,
    )


def _make_level(loops=None):
    from dungeon_daddy.data.models import Level, Room
    room = Room(id="r1", num=1, name="Room 1", x=0, y=0, w=4, h=4, type="hall", note="")
    return Level(
        id=1, name="Test Level", summary="", ecology="", loop="",
        width=50, height=50, entries=[], rooms=[room], connections=[],
        loops=loops or [],
    )


def _make_state(active_loop_id=None):
    from dungeon_daddy.data.models import SessionState
    return SessionState(dungeon_id="test", current_level_idx=0, active_loop_id=active_loop_id)


# ---------------------------------------------------------------------------
# Test 1 — strip hidden when no loops
# ---------------------------------------------------------------------------

def test_strip_hidden_when_no_loops() -> None:
    panel = _make_panel()
    panel.load(_make_level(loops=[]), _make_state())
    assert panel._loop_strip_rects == {}


# ---------------------------------------------------------------------------
# Test 2 — one pill per loop
# ---------------------------------------------------------------------------

def test_strip_shows_one_pill_per_loop() -> None:
    panel = _make_panel()
    loops = [_make_loop("L1"), _make_loop("L2")]
    panel.load(_make_level(loops=loops), _make_state())
    assert len(panel._loop_strip_rects) == 2
    assert "L1" in panel._loop_strip_rects
    assert "L2" in panel._loop_strip_rects


# ---------------------------------------------------------------------------
# Test 3 — clicking inactive pill fires callback with loop id
# ---------------------------------------------------------------------------

def test_clicking_pill_calls_on_activate_loop_with_id() -> None:
    callback = MagicMock()
    panel = _make_panel(on_activate_loop=callback)
    panel._loop_strip_rects = {"loop1": (10.0, 10.0, 120.0, 34.0)}
    panel._active_loop_id = None
    panel.handle_mouse_press(60.0, 20.0, 1)  # 1 = left button, inside rect
    callback.assert_called_once_with("loop1")


# ---------------------------------------------------------------------------
# Test 4 — clicking the active pill fires callback with None
# ---------------------------------------------------------------------------

def test_clicking_active_pill_calls_on_activate_loop_with_none() -> None:
    callback = MagicMock()
    panel = _make_panel(on_activate_loop=callback)
    panel._loop_strip_rects = {"loop1": (10.0, 10.0, 120.0, 34.0)}
    panel._active_loop_id = "loop1"
    panel.handle_mouse_press(60.0, 20.0, 1)
    callback.assert_called_once_with(None)


# ---------------------------------------------------------------------------
# Test 5 — activating second loop replaces first
# ---------------------------------------------------------------------------

def test_activating_second_loop_replaces_first() -> None:
    callback = MagicMock()
    panel = _make_panel(on_activate_loop=callback)
    panel._loop_strip_rects = {
        "loop1": (10.0, 10.0, 120.0, 34.0),
        "loop2": (130.0, 10.0, 240.0, 34.0),
    }
    panel._active_loop_id = "loop1"
    panel.handle_mouse_press(185.0, 20.0, 1)  # click loop2
    callback.assert_called_once_with("loop2")
    assert panel._active_loop_id == "loop2"
