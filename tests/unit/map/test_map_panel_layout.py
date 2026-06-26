"""Tests for MapPanel layout pipeline wiring.

No arcade display needed — setup() is never called.
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import arcade

from dungeon_daddy.data.models import Connection, Level, Room, SessionState
from dungeon_daddy.map.dungeon_layout import LayoutResult
from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
from dungeon_daddy.map.dungeon_layout.models import LayoutBounds, RoomRect, RoutedEdge
from dungeon_daddy.ui.panels.map_panel import MapPanel
from dungeon_daddy.ui.theme import PAD_MD

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
    from dungeon_daddy.ui.panels.map_panel import _ZOOM_MAX, _ZOOM_MIN
    p = _panel_sized(w=900.0, h=700.0)
    level = _level(["a", "b"], [_conn("a", "b")])
    p.load(level, _state())
    p._fit_layout_camera()
    assert _ZOOM_MIN <= p.zoom_level <= _ZOOM_MAX


def test_load_on_graph_tab_applies_camera_fit() -> None:
    p = _panel_sized(w=900.0, h=700.0)
    p._active_variant = "Map"
    level = _level(["a", "b", "c"], [_conn("a", "b"), _conn("b", "c")])
    p.load(level, _state())
    # Camera fit should have been applied — zoom or pan differs from defaults
    assert p.pan_offset != (0.0, 0.0) or p.zoom_level != 1.0


# ---------------------------------------------------------------------------
# Helpers for selection tests
# ---------------------------------------------------------------------------

def _graph_panel_with_room(room_id: str = "a") -> tuple[MapPanel, RoomRect]:
    """Panel in Graph/select mode, zoom=1, pan=0, with one room at origin."""
    p = _panel_sized(900.0, 700.0)
    p._active_variant = "Map"
    p._active_tool = "select"
    p._pan_offset_x = 0.0
    p._pan_offset_y = 0.0
    p._zoom_level = 1.0
    room = RoomRect(room_id=room_id, x=0.0, y=0.0, w=120.0, h=80.0)
    bounds = LayoutBounds(min_x=0.0, min_y=0.0, max_x=200.0, max_y=200.0)
    p._layout_result = LayoutResult(
        rooms={room_id: room}, edges=[], labels=[], bounds=bounds,
        debug_overlay=DebugOverlay(enabled=False, bounds=bounds),
    )
    return p, room


def _screen_center(p: MapPanel, room: RoomRect) -> tuple[float, float]:
    cx = p._x + PAD_MD + room.x + room.w / 2
    cy = p._y + PAD_MD + room.y + room.h / 2
    return cx, cy


# ---------------------------------------------------------------------------
# Cycle 5 — click inside room selects it
# ---------------------------------------------------------------------------

def test_click_inside_room_selects_it() -> None:
    p, room = _graph_panel_with_room("a")
    cx, cy = _screen_center(p, room)
    p.handle_mouse_press(cx, cy, arcade.MOUSE_BUTTON_LEFT)
    assert p._selected_room_id == "a"


# ---------------------------------------------------------------------------
# Cycle 6 — click same room again clears selection
# ---------------------------------------------------------------------------

def test_click_same_room_again_clears_selection() -> None:
    p, room = _graph_panel_with_room("a")
    p._selected_room_id = "a"
    cx, cy = _screen_center(p, room)
    p.handle_mouse_press(cx, cy, arcade.MOUSE_BUTTON_LEFT)
    assert p._selected_room_id is None


# ---------------------------------------------------------------------------
# Cycle 7 — click outside all rooms leaves selection unchanged
# ---------------------------------------------------------------------------

def test_click_outside_rooms_does_not_change_selection() -> None:
    p, _ = _graph_panel_with_room("a")
    p._selected_room_id = "a"
    # click far outside the 120×80 room (which ends at screen PAD_MD+120)
    p.handle_mouse_press(p._x + PAD_MD + 500.0, p._y + PAD_MD + 500.0, arcade.MOUSE_BUTTON_LEFT)
    assert p._selected_room_id == "a"


# ---------------------------------------------------------------------------
# Cycle 8 — load() resets _selected_room_id
# ---------------------------------------------------------------------------

def test_load_resets_selected_room() -> None:
    p = _panel()
    p._selected_room_id = "old"  # type: ignore[assignment]
    p.load(_level(["a"]), _state())
    assert p._selected_room_id is None


# ---------------------------------------------------------------------------
# Helpers shared by Cycles 9 and 10
# ---------------------------------------------------------------------------

def _graph_panel_with_callback(
    on_room_select: object = None,
    on_connection_select: object = None,
) -> tuple[MapPanel, RoomRect]:
    """Panel in Graph/select mode with a single room and optional callbacks."""
    p = MapPanel(
        on_level_change=lambda _: None,
        on_room_select=on_room_select,  # type: ignore[arg-type]
        on_connection_select=on_connection_select,  # type: ignore[arg-type]
    )
    p._x, p._y, p._w, p._h = 0.0, 0.0, 900.0, 700.0
    p._active_variant = "Map"
    p._active_tool = "select"
    p._pan_offset_x = 0.0
    p._pan_offset_y = 0.0
    p._zoom_level = 1.0
    room = RoomRect(room_id="1-A", x=0.0, y=0.0, w=120.0, h=80.0)
    bounds = LayoutBounds(min_x=0.0, min_y=0.0, max_x=400.0, max_y=200.0)
    edge = RoutedEdge(
        connection_id="1-A→1-B",
        points=[(120.0, 40.0), (200.0, 40.0)],
        source_port="right", target_port="left", score=0.0,
    )
    p._layout_result = LayoutResult(
        rooms={"1-A": room}, edges=[edge], labels=[], bounds=bounds,
        debug_overlay=DebugOverlay(enabled=False, bounds=bounds),
    )
    return p, room


# ---------------------------------------------------------------------------
# Cycle 9 — room click fires on_room_select callback
# ---------------------------------------------------------------------------

def test_room_click_fires_on_room_select_callback() -> None:
    fired: list[str] = []
    p, room = _graph_panel_with_callback(on_room_select=lambda rid: fired.append(rid))
    cx = p._x + PAD_MD + room.x + room.w / 2
    cy = p._y + PAD_MD + room.y + room.h / 2
    p.handle_mouse_press(cx, cy, arcade.MOUSE_BUTTON_LEFT)
    assert fired == ["1-A"]


def test_no_callback_room_click_does_not_raise() -> None:
    p, room = _graph_panel_with_callback()  # no callback set
    cx = p._x + PAD_MD + room.x + room.w / 2
    cy = p._y + PAD_MD + room.y + room.h / 2
    p.handle_mouse_press(cx, cy, arcade.MOUSE_BUTTON_LEFT)  # must not raise


# ---------------------------------------------------------------------------
# Cycle 10 — edge click fires on_connection_select callback
# ---------------------------------------------------------------------------

def test_edge_click_fires_on_connection_select_callback() -> None:
    fired: list[tuple[str, str]] = []
    p, _ = _graph_panel_with_callback(
        on_connection_select=lambda fr, to: fired.append((fr, to))
    )
    # edge runs from (120,40)→(200,40) in layout space; click midpoint (160,40)
    ex = p._x + PAD_MD + 160.0
    ey = p._y + PAD_MD + 40.0
    p.handle_mouse_press(ex, ey, arcade.MOUSE_BUTTON_LEFT)
    assert fired == [("1-A", "1-B")]


def test_miss_outside_room_and_edge_does_not_fire_callbacks() -> None:
    room_fired: list[str] = []
    conn_fired: list[tuple[str, str]] = []
    p, _ = _graph_panel_with_callback(
        on_room_select=lambda rid: room_fired.append(rid),
        on_connection_select=lambda fr, to: conn_fired.append((fr, to)),
    )
    # click well away from room and edge
    p.handle_mouse_press(p._x + PAD_MD + 600.0, p._y + PAD_MD + 400.0, arcade.MOUSE_BUTTON_LEFT)
    assert room_fired == []
    assert conn_fired == []


# ---------------------------------------------------------------------------
# Cycle 11 — R key recenters Graph Mode camera
# ---------------------------------------------------------------------------

def _graph_panel_with_layout() -> MapPanel:
    """Panel in Graph mode with a layout result and non-default pan/zoom."""
    p = _panel_sized(w=900.0, h=700.0)
    p._active_variant = "Map"
    level = _level(["a", "b", "c"], [_conn("a", "b"), _conn("b", "c")])
    p.load(level, _state())
    # Shift pan so we can observe recenter effect
    p._pan_offset_x = 9999.0
    p._pan_offset_y = 9999.0
    p._zoom_level = 0.5
    return p


def test_r_key_recenters_graph_camera() -> None:
    p = _graph_panel_with_layout()
    p.handle_key_press(arcade.key.R)
    # After recenter, pan should no longer be the sentinel values
    assert p._pan_offset_x != 9999.0
    assert p._pan_offset_y != 9999.0


def test_r_key_without_layout_does_not_raise() -> None:
    p = _panel_sized(w=900.0, h=700.0)
    p._active_variant = "Map"
    p._layout_result = None
    p.handle_key_press(arcade.key.R)  # must not raise


# ---------------------------------------------------------------------------
# Cycle 12 — Escape key clears Graph Mode selection
# ---------------------------------------------------------------------------

def test_escape_clears_selected_room_in_graph_mode() -> None:
    p = _panel_sized(w=900.0, h=700.0)
    p._active_variant = "Map"
    p._selected_room_id = "R1"
    p.handle_key_press(arcade.key.ESCAPE)
    assert p._selected_room_id is None


def test_escape_with_no_selection_does_not_raise() -> None:
    p = _panel_sized(w=900.0, h=700.0)
    p._active_variant = "Map"
    p._selected_room_id = None
    p.handle_key_press(arcade.key.ESCAPE)  # must not raise
    assert p._selected_room_id is None


# ---------------------------------------------------------------------------
# Cycle 13 — handle_mouse_motion over room sets hover state
# ---------------------------------------------------------------------------

def test_mouse_motion_over_room_sets_hover() -> None:
    p, room = _graph_panel_with_room("a")
    cx, cy = _screen_center(p, room)
    p.handle_mouse_motion(cx, cy)
    assert p._view_state.hovered_room_id == "a"


# ---------------------------------------------------------------------------
# Cycle 14 — handle_mouse_motion off room clears hover state
# ---------------------------------------------------------------------------

def test_mouse_motion_off_room_clears_hover() -> None:
    p, _ = _graph_panel_with_room("a")
    p._view_state.hover_room("a")
    p.handle_mouse_motion(p._x + PAD_MD + 500.0, p._y + PAD_MD + 500.0)
    assert p._view_state.hovered_room_id is None


# ---------------------------------------------------------------------------
# Cycle 16 — handle_mouse_motion near connection sets connection hover
# ---------------------------------------------------------------------------

def test_mouse_motion_near_connection_sets_connection_hover() -> None:
    p, _ = _graph_panel_with_callback()
    # edge "1-A→1-B" runs from layout (120,40) to (200,40); click midpoint (160,40)
    ex = p._x + PAD_MD + 160.0
    ey = p._y + PAD_MD + 40.0
    p.handle_mouse_motion(ex, ey)
    assert p._view_state.hovered_connection_id == "1-A→1-B"


# ---------------------------------------------------------------------------
# Cycle 17 — load() resets view_state (hover and selection cleared)
# ---------------------------------------------------------------------------

def test_load_resets_view_state() -> None:
    p = _panel()
    p._view_state.select_room("R1")
    p._view_state.hover_room("R2")
    p.load(_level(["a"]), _state())
    assert p._view_state.selected_room_id is None
    assert p._view_state.hovered_room_id is None


# ---------------------------------------------------------------------------
# Phase 50.6 Slice 7 — "Things Here" overlay forwarding
# ---------------------------------------------------------------------------

def _draw_with_mock_renderer(p: MapPanel):
    """Run MapPanel.draw() with the renderer + GPU bits stubbed; return the mock."""
    p._layout_renderer = MagicMock()
    p._stepper = MagicMock()
    p._art = types.SimpleNamespace(background=None)
    p._active_variant = "Grid"  # skip the Map-background texture branch
    p._x, p._y, p._w, p._h = 0.0, 0.0, 900.0, 700.0
    p._draw_level_overlay = lambda *a, **k: None  # type: ignore[method-assign]
    with patch("dungeon_daddy.ui.panels.map_panel.arcade"), \
            patch("dungeon_daddy.ui.panels.map_panel.draw_kicker"), \
            patch("dungeon_daddy.ui.panels.map_panel.draw_chip"):
        p.draw()
    return p._layout_renderer.draw


def test_draw_forwards_things_here_in_play_mode() -> None:
    from dungeon_daddy.rpg.action_options import RoomThing, RoomThings, ThingsSection
    p = _panel()
    p.load(_level(["a", "b"], [_conn("a", "b")]), _state())
    things = RoomThings(
        room_id="a",
        sections=[ThingsSection("EXITS", [RoomThing("b", "Hall", "→", "open", "teal")])],
    )
    p.set_things_here(things)

    draw = _draw_with_mock_renderer(p)
    _, kwargs = draw.call_args
    assert kwargs["mode"] == "play"
    assert kwargs["room_things"] is things


def test_draw_stays_graph_mode_without_things_here() -> None:
    p = _panel()
    p.load(_level(["a", "b"], [_conn("a", "b")]), _state())

    draw = _draw_with_mock_renderer(p)
    _, kwargs = draw.call_args
    assert kwargs["mode"] == "graph"
    assert kwargs["room_things"] is None


# ---------------------------------------------------------------------------
# Phase 50.6 Slice 8 — overlay noun-row click feeds the action builder
# ---------------------------------------------------------------------------

def _play_panel_with_noun_rect(
    on_noun_click=None, on_room_select=None, rect=None,
):
    from dungeon_daddy.map.dungeon_layout.panel_placement import ScreenRect
    from dungeon_daddy.rpg.action_options import RoomThing, RoomThings, ThingsSection
    p = MapPanel(
        on_level_change=lambda _: None,
        on_noun_click=on_noun_click,  # type: ignore[arg-type]
        on_room_select=on_room_select,  # type: ignore[arg-type]
    )
    p._x, p._y, p._w, p._h = 0.0, 0.0, 900.0, 700.0
    p._active_variant = "Map"
    p._active_tool = "select"
    p._pan_offset_x = p._pan_offset_y = 0.0
    p._zoom_level = 1.0
    p._things_here = RoomThings(
        room_id="a",
        sections=[ThingsSection("EXITS", [RoomThing("e1", "Hall", "→", "open", "teal")])],
    )
    p._layout_renderer._thing_rects = {
        "e1": rect or ScreenRect(x=100.0, y=100.0, w=200.0, h=20.0)
    }
    return p


def test_overlay_noun_click_fires_on_noun_click() -> None:
    fired: list[str] = []
    p = _play_panel_with_noun_rect(on_noun_click=lambda nid: fired.append(nid))
    consumed = p.handle_mouse_press(150.0, 110.0, arcade.MOUSE_BUTTON_LEFT)
    assert fired == ["e1"]
    assert consumed is True


def test_overlay_noun_click_outside_rows_does_not_fire() -> None:
    fired: list[str] = []
    p = _play_panel_with_noun_rect(on_noun_click=lambda nid: fired.append(nid))
    p.handle_mouse_press(400.0, 400.0, arcade.MOUSE_BUTTON_LEFT)
    assert fired == []


def test_overlay_noun_click_takes_priority_over_room_select() -> None:
    from dungeon_daddy.map.dungeon_layout.panel_placement import ScreenRect
    from dungeon_daddy.map.dungeon_layout.models import LayoutBounds, RoomRect
    from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
    nouns: list[str] = []
    rooms: list[str] = []
    # The noun row overlaps the room rect at screen (PAD_MD..PAD_MD+120, ...).
    p = _play_panel_with_noun_rect(
        on_noun_click=lambda nid: nouns.append(nid),
        on_room_select=lambda rid: rooms.append(rid),
        rect=ScreenRect(x=PAD_MD, y=PAD_MD, w=120.0, h=80.0),
    )
    room = RoomRect(room_id="a", x=0.0, y=0.0, w=120.0, h=80.0)
    bounds = LayoutBounds(min_x=0.0, min_y=0.0, max_x=200.0, max_y=200.0)
    p._layout_result = LayoutResult(
        rooms={"a": room}, edges=[], labels=[], bounds=bounds,
        debug_overlay=DebugOverlay(enabled=False, bounds=bounds),
    )
    p.handle_mouse_press(PAD_MD + 60.0, PAD_MD + 40.0, arcade.MOUSE_BUTTON_LEFT)
    assert nouns == ["e1"]
    assert rooms == []


# ---------------------------------------------------------------------------
# Phase 50.6 — loop strip chips gated to test-drive / design (not normal play)
# ---------------------------------------------------------------------------

def _level_with_loop() -> Level:
    from dungeon_daddy.data.models import Loop
    lvl = _level(["a", "b"], [_conn("a", "b")])
    lvl.loops = [Loop(id="lp1", pattern="lock_key", note="", entry="a", goal="b",
                      path_a=["a"], path_b=["b"])]
    return lvl


def test_loop_strip_shown_by_default() -> None:
    p = _panel_sized()
    p.load(_level_with_loop(), _state())
    assert "lp1" in p._loop_strip_rects


def test_loop_strip_hidden_when_loops_invisible() -> None:
    p = _panel_sized()
    p.set_loops_visible(False)
    p.load(_level_with_loop(), _state())
    assert p._loop_strip_rects == {}


def test_set_loops_visible_rebuilds_on_loaded_level() -> None:
    p = _panel_sized()
    p.load(_level_with_loop(), _state())
    p.set_loops_visible(False)
    assert p._loop_strip_rects == {}
    p.set_loops_visible(True)
    assert "lp1" in p._loop_strip_rects


def test_draw_forwards_selection() -> None:
    from dungeon_daddy.rpg.action_options import RoomThing, RoomThings, ThingsSection
    p = _panel()
    p.load(_level(["a", "b"], [_conn("a", "b")]), _state())
    things = RoomThings(
        room_id="a",
        sections=[ThingsSection("EXITS", [RoomThing("b", "Hall", "→", "open", "teal")])],
    )
    p.set_things_here(things, selected_noun_id="b")

    draw = _draw_with_mock_renderer(p)
    _, kwargs = draw.call_args
    assert kwargs["selected_noun_id"] == "b"
