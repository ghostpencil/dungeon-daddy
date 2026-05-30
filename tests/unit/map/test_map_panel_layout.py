"""Tests for MapPanel layout pipeline wiring.

No arcade display needed — setup() is never called.
"""
from __future__ import annotations

import arcade

from dungeon_daddy.data.models import Connection, Level, Room, SessionState
from dungeon_daddy.ui.panels.map_panel import MapPanel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _panel() -> MapPanel:
    return MapPanel(on_level_change=lambda _: None)


def _panel_sized(w: float = 900.0, h: float = 700.0) -> MapPanel:
    p = MapPanel(on_level_change=lambda _: None)
    p._x, p._y, p._w, p._h = 0.0, 0.0, w, h
    return p


def _room(room_id: str) -> Room:
    return Room(id=room_id, num=0, name=room_id, x=0, y=0, w=10, h=10, type="room", note="")


def _conn(from_id: str, to_id: str) -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": "door"})


def _level(room_ids: list[str], connections: list[Connection] | None = None) -> Level:
    rooms = [_room(rid) for rid in room_ids]
    return Level(
        id=1, name="Test", summary="", ecology="", loop="",
        width=100, height=100, entries=[],
        rooms=rooms, connections=connections or [],
    )


def _state() -> SessionState:
    return SessionState(dungeon_id="test", current_level_idx=0)


# ---------------------------------------------------------------------------
# Cycle 1 — load() caches LayoutResult
# ---------------------------------------------------------------------------

def test_load_caches_layout_result() -> None:
    p = _panel()
    level = _level(["a", "b"], [_conn("a", "b")])
    p.load(level, _state())
    assert p._layout_result is not None
    assert set(p._layout_result.rooms.keys()) == {"a", "b"}


def test_load_new_level_replaces_cached_layout() -> None:
    p = _panel()
    p.load(_level(["a", "b"], [_conn("a", "b")]), _state())
    first = p._layout_result

    p.load(_level(["x", "y", "z"], [_conn("x", "y"), _conn("y", "z")]), _state())
    assert p._layout_result is not first
    assert set(p._layout_result.rooms.keys()) == {"x", "y", "z"}  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Cycle 2 — debug overlay disabled by default after load
# ---------------------------------------------------------------------------

def test_debug_overlay_disabled_after_load() -> None:
    p = _panel()
    p.load(_level(["a", "b"], [_conn("a", "b")]), _state())
    assert p._layout_result is not None
    assert p._layout_result.debug_overlay.enabled is False


# ---------------------------------------------------------------------------
# Cycle 3 — D key toggles debug overlay on
# ---------------------------------------------------------------------------

def test_d_key_enables_debug_overlay() -> None:
    p = _panel()
    p.load(_level(["a", "b"], [_conn("a", "b")]), _state())
    assert p._layout_result is not None
    p.handle_key_press(arcade.key.D)
    assert p._layout_result.debug_overlay.enabled is True


def test_d_key_toggles_debug_overlay_off() -> None:
    p = _panel()
    p.load(_level(["a", "b"], [_conn("a", "b")]), _state())
    assert p._layout_result is not None
    p.handle_key_press(arcade.key.D)
    p.handle_key_press(arcade.key.D)
    assert p._layout_result.debug_overlay.enabled is False


def test_d_key_does_nothing_without_layout() -> None:
    p = _panel()
    # no load() — _layout_result is None; must not raise
    p.handle_key_press(arcade.key.D)


# ---------------------------------------------------------------------------
# Cycle 4 — camera fit centres the layout in the viewport
# ---------------------------------------------------------------------------

def test_fit_layout_camera_sets_non_zero_pan() -> None:
    p = _panel_sized(w=900.0, h=700.0)
    level = _level(["a", "b", "c"], [_conn("a", "b"), _conn("b", "c")])
    p.load(level, _state())

    # Reset pan/zoom so we can see the effect of fit
    p._pan_offset_x = 0.0
    p._pan_offset_y = 0.0
    p._zoom_level = 1.0

    p._fit_layout_camera()

    # Camera fit should have moved the pan or changed zoom
    assert p.pan_offset != (0.0, 0.0) or p.zoom_level != 1.0


def test_fit_layout_camera_zoom_within_bounds() -> None:
    from dungeon_daddy.ui.panels.map_panel import _ZOOM_MIN, _ZOOM_MAX
    p = _panel_sized(w=900.0, h=700.0)
    level = _level(["a", "b"], [_conn("a", "b")])
    p.load(level, _state())
    p._fit_layout_camera()
    assert _ZOOM_MIN <= p.zoom_level <= _ZOOM_MAX


def test_load_on_graph_tab_applies_camera_fit() -> None:
    p = _panel_sized(w=900.0, h=700.0)
    p._active_variant = "Graph"
    level = _level(["a", "b", "c"], [_conn("a", "b"), _conn("b", "c")])
    p.load(level, _state())
    # Camera fit should have been applied — zoom or pan differs from defaults
    assert p.pan_offset != (0.0, 0.0) or p.zoom_level != 1.0
