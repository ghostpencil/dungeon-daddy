"""Tests for GridRenderer — patch arcade.draw_* so no display is needed."""
from __future__ import annotations

import pytest
from unittest.mock import patch

import arcade

from dungeon_daddy.data.models import Connection, Entry, Level, Room, SessionState
from dungeon_daddy.ui.theme import BG_2, ROOM_COLORS, TEAL, ROOM_UNSEEN_FILL


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _room(id: str, x: int, y: int, w: int = 1, h: int = 1, type: str = "hall") -> Room:
    return Room(id=id, num=1, name=id, x=x, y=y, w=w, h=h, type=type, note="")


def _conn(from_id: str, to_id: str) -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": "normal"})


def _level(rooms: list[Room], connections: list[Connection] | None = None) -> Level:
    return Level(
        id=1, name="T", summary="", ecology="", loop="",
        width=20, height=20, entries=[], rooms=rooms,
        connections=connections or [],
    )


def _state(**kwargs) -> SessionState:
    defaults: dict = dict(dungeon_id="test", current_level_idx=0, visited_rooms=[])
    defaults.update(kwargs)
    return SessionState(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_draws_room_rect() -> None:
    """draw() calls draw_rect_filled with pixel coords derived from room grid pos."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    room = _room("r1", x=1, y=2, w=2, h=1, type="hall")
    level = _level([room])
    state = _state(visited_rooms=["r1"])
    renderer = GridRenderer(cell_px=48)

    with patch("arcade.draw_rect_filled") as mock_fill, \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line"), \
         patch("arcade.draw_text"):
        renderer.draw(level, state, origin_x=0.0, origin_y=0.0)

    assert mock_fill.called
    rect, color = mock_fill.call_args[0]
    # center_x = (1 + 2/2) * 48 = 96, center_y = (2 + 1/2) * 48 = 120
    assert rect.x == pytest.approx(96.0)
    assert rect.y == pytest.approx(120.0)
    assert rect.width == pytest.approx(96.0)
    assert rect.height == pytest.approx(48.0)
    assert color == ROOM_COLORS["hall"]["fill"]


def test_draws_connection_line() -> None:
    """draw() calls draw_line between room boundary edges (edge-port routing)."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    r1 = _room("r1", x=0, y=0, w=1, h=1)
    r2 = _room("r2", x=2, y=0, w=1, h=1)
    level = _level([r1, r2], connections=[_conn("r1", "r2")])
    state = _state(visited_rooms=["r1", "r2"])
    renderer = GridRenderer(cell_px=48)

    with patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line") as mock_line, \
         patch("arcade.draw_text"):
        renderer.draw(level, state, origin_x=0.0, origin_y=0.0)

    assert mock_line.called
    x1, y1, x2, y2 = mock_line.call_args[0][:4]
    # r1 center (24,24), hw=24 → right edge toward r2: x=48, y=24
    # r2 center (120,24), hw=24 → left edge toward r1: x=96, y=24
    assert x1 == pytest.approx(48.0)
    assert y1 == pytest.approx(24.0)
    assert x2 == pytest.approx(96.0)
    assert y2 == pytest.approx(24.0)


def test_highlights_current_room() -> None:
    """Current room's outline uses TEAL, not the default room stroke."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    room = _room("r1", x=0, y=0, type="hall")
    level = _level([room])
    state = _state(current_room_id="r1")
    renderer = GridRenderer(cell_px=48)

    with patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_rect_outline") as mock_outline, \
         patch("arcade.draw_line"), \
         patch("arcade.draw_text"):
        renderer.draw(level, state, origin_x=0.0, origin_y=0.0)

    assert mock_outline.called
    _rect, stroke, *_ = mock_outline.call_args[0]
    assert stroke == TEAL


def test_rooms_use_type_fill() -> None:
    """Rooms always render with their type-specific fill color."""
    from dungeon_daddy.map.grid_renderer import GridRenderer
    from dungeon_daddy.ui.theme import ROOM_COLORS

    room = _room("r1", x=0, y=0, type="shrine")
    level = _level([room])
    state = _state(visited_rooms=[])  # not visited, not current
    renderer = GridRenderer(cell_px=48)

    with patch("arcade.draw_rect_filled") as mock_fill, \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line"), \
         patch("arcade.draw_text"):
        renderer.draw(level, state, origin_x=0.0, origin_y=0.0)

    _rect, color = mock_fill.call_args[0]
    assert color == ROOM_COLORS["shrine"]["fill"]


def test_draws_room_label_centered() -> None:
    """draw() calls draw_text with the room name centered in the room."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    room = Room(id="r1", num=1, name="Throne Room", x=1, y=2, w=2, h=2, type="hall", note="")
    level = _level([room])
    state = _state(visited_rooms=["r1"])
    renderer = GridRenderer(cell_px=48)

    with patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line"), \
         patch("arcade.draw_text") as mock_text:
        renderer.draw(level, state, origin_x=0.0, origin_y=0.0)

    assert mock_text.called
    args, kwargs = mock_text.call_args
    # text, x, y
    assert args[0] == "Throne Room (r1)"
    # center_x = (1 + 2/2) * 48 = 96, center_y = (2 + 2/2) * 48 = 144
    assert args[1] == pytest.approx(96.0)
    assert args[2] == pytest.approx(144.0)
    assert kwargs.get("anchor_x") == "center"
    assert kwargs.get("anchor_y") == "center"


def test_zoom_scales_room_center() -> None:
    """room_center() multiplies cell_px by zoom."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    room = _room("r1", x=1, y=2, w=2, h=2)
    renderer = GridRenderer(cell_px=48)

    cx1, cy1 = renderer.room_center(room, origin_x=0.0, origin_y=0.0, zoom=1.0)
    cx2, cy2 = renderer.room_center(room, origin_x=0.0, origin_y=0.0, zoom=2.0)

    assert cx2 == pytest.approx(cx1 * 2)
    assert cy2 == pytest.approx(cy1 * 2)


def test_zoom_scales_drawn_room_rect() -> None:
    """draw() at zoom=2.0 doubles room pixel width and height."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    room = _room("r1", x=0, y=0, w=2, h=3, type="hall")
    level = _level([room])
    state = _state(visited_rooms=["r1"])
    renderer = GridRenderer(cell_px=48)

    rects_at_zoom = {}
    for z in (1.0, 2.0):
        with patch("arcade.draw_rect_filled") as mock_fill, \
             patch("arcade.draw_rect_outline"), \
             patch("arcade.draw_line"), \
             patch("arcade.draw_text"):
            renderer.draw(level, state, origin_x=0.0, origin_y=0.0, zoom=z)
        rects_at_zoom[z] = mock_fill.call_args[0][0]

    assert rects_at_zoom[2.0].width == pytest.approx(rects_at_zoom[1.0].width * 2)
    assert rects_at_zoom[2.0].height == pytest.approx(rects_at_zoom[1.0].height * 2)


def test_draws_label_for_unseen_room() -> None:
    """Label is drawn for unseen rooms too (GM always sees all room names)."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    room = Room(id="r1", num=1, name="Secret Vault", x=0, y=0, w=1, h=1, type="vault", note="")
    level = _level([room])
    state = _state(visited_rooms=[])
    renderer = GridRenderer(cell_px=48)

    with patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line"), \
         patch("arcade.draw_text") as mock_text:
        renderer.draw(level, state, origin_x=0.0, origin_y=0.0)

    drawn_texts = [call.args[0] for call in mock_text.call_args_list]
    assert "Secret Vault (r1)" in drawn_texts


def test_draws_connection_type_label_at_midpoint() -> None:
    """draw() renders the connection type at the midpoint of the connection line."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    r1 = _room("r1", x=0, y=0, w=1, h=1)
    r2 = _room("r2", x=2, y=0, w=1, h=1)
    conn = Connection(**{"from": "r1", "to": "r2", "type": "normal"})
    level = _level([r1, r2], connections=[conn])
    state = _state(visited_rooms=["r1", "r2"])
    renderer = GridRenderer(cell_px=48)

    with patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line"), \
         patch("arcade.draw_text") as mock_text:
        renderer.draw(level, state, origin_x=0.0, origin_y=0.0)

    drawn = {call.args[0]: call.args[1:3] for call in mock_text.call_args_list}
    # r1 center: (0.5*48, 0.5*48) = (24, 24)
    # r2 center: (2.5*48, 0.5*48) = (120, 24)
    # midpoint: (72, 24)
    assert "normal" in drawn
    assert drawn["normal"][0] == pytest.approx(72.0)
    assert drawn["normal"][1] == pytest.approx(24.0)


def test_truncates_long_connection_type_label() -> None:
    """Connection type longer than 12 chars is truncated to 9 chars + '...'."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    r1 = _room("r1", x=0, y=0, w=1, h=1)
    r2 = _room("r2", x=2, y=0, w=1, h=1)
    # "secret_passage" = 14 chars → "secret_pa..." (9 + 3 = 12)
    conn = Connection(**{"from": "r1", "to": "r2", "type": "secret_passage"})
    level = _level([r1, r2], connections=[conn])
    state = _state(visited_rooms=["r1", "r2"])
    renderer = GridRenderer(cell_px=48)

    with patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line"), \
         patch("arcade.draw_text") as mock_text:
        renderer.draw(level, state, origin_x=0.0, origin_y=0.0)

    drawn_texts = [call.args[0] for call in mock_text.call_args_list]
    assert "secret_pa..." in drawn_texts
    assert "secret_passage" not in drawn_texts


def test_draws_connection_line_diagonal_rooms_uses_port_midpoints() -> None:
    """Diagonally-placed rooms use N/S/E/W port midpoints, not corners."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    # r1 at (0,0,2,2), r2 at (4,4,2,2) — purely diagonal, |dx|==|dy|
    r1 = _room("r1", x=0, y=0, w=2, h=2)
    r2 = _room("r2", x=4, y=4, w=2, h=2)
    level = _level([r1, r2], connections=[_conn("r1", "r2")])
    state = _state(visited_rooms=["r1", "r2"])
    renderer = GridRenderer(cell_px=48)

    with patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line") as mock_line, \
         patch("arcade.draw_text"):
        renderer.draw(level, state, origin_x=0.0, origin_y=0.0)

    x1, y1, x2, y2 = mock_line.call_args[0][:4]
    # |dx|==|dy| → horizontal wins → east/west ports
    # r1 east port: right edge = 2*48=96, center_y = 1*48=48
    # r2 west port: left edge  = 4*48=192, center_y = 5*48=240
    assert x1 == pytest.approx(96.0)
    assert y1 == pytest.approx(48.0)
    assert x2 == pytest.approx(192.0)
    assert y2 == pytest.approx(240.0)


def test_draws_orthogonal_route_when_straight_path_blocked() -> None:
    """When straight path is blocked, draw() draws 2 line segments via route_orthogonal."""
    from dungeon_daddy.map.grid_renderer import GridRenderer
    from dungeon_daddy.ui.theme import LINE

    # A east port (2,1) → C west port (6,5); blocker B at rect(2,2,4,6) blocks V-first
    # route_orthogonal returns H-first: (2,1)→(6,1)→(6,5)
    r_a = _room("A", x=0, y=0, w=2, h=2)
    r_c = _room("C", x=6, y=4, w=2, h=2)
    r_b = _room("B", x=2, y=2, w=2, h=4)
    level = _level([r_a, r_b, r_c], connections=[_conn("A", "C")])
    state = _state(visited_rooms=["A", "B", "C"])
    renderer = GridRenderer(cell_px=48)

    with patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line") as mock_line, \
         patch("arcade.draw_text"):
        renderer.draw(level, state, origin_x=0.0, origin_y=0.0)

    calls = mock_line.call_args_list
    assert len(calls) == 2
    # Segment 1: from_port (2,1) → corner (6,1) in screen pixels
    x1, y1, x2, y2 = calls[0].args[:4]
    assert x1 == pytest.approx(2 * 48)   # 96
    assert y1 == pytest.approx(1 * 48)   # 48
    assert x2 == pytest.approx(6 * 48)   # 288
    assert y2 == pytest.approx(1 * 48)   # 48
    # Segment 2: corner (6,1) → to_port (6,5) in screen pixels
    x1, y1, x2, y2 = calls[1].args[:4]
    assert x1 == pytest.approx(6 * 48)   # 288
    assert y1 == pytest.approx(1 * 48)   # 48
    assert x2 == pytest.approx(6 * 48)   # 288
    assert y2 == pytest.approx(5 * 48)   # 240


def test_hit_test_connection_returns_connection_on_line() -> None:
    """hit_test_connection returns the Connection when point is on the line midpoint."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    r1 = _room("r1", x=0, y=0, w=1, h=1)
    r2 = _room("r2", x=2, y=0, w=1, h=1)
    conn = _conn("r1", "r2")
    level = _level([r1, r2], connections=[conn])
    state = _state(visited_rooms=["r1", "r2"])
    renderer = GridRenderer(cell_px=48)

    # r1 center: (24, 24), r2 center: (120, 24), midpoint: (72, 24)
    result = renderer.hit_test_connection(level, state, x=72.0, y=24.0, origin_x=0.0, origin_y=0.0)

    assert result is conn


def test_hit_test_connection_returns_none_when_far() -> None:
    """hit_test_connection returns None when point is more than 8px from all lines."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    r1 = _room("r1", x=0, y=0, w=1, h=1)
    r2 = _room("r2", x=2, y=0, w=1, h=1)
    level = _level([r1, r2], connections=[_conn("r1", "r2")])
    state = _state(visited_rooms=["r1", "r2"])
    renderer = GridRenderer(cell_px=48)

    # line is at y=24; point 50px above = y=74 → distance 50px > 8px
    result = renderer.hit_test_connection(level, state, x=72.0, y=74.0, origin_x=0.0, origin_y=0.0)

    assert result is None


def test_hit_test_connection_returns_connection_within_threshold() -> None:
    """hit_test_connection returns Connection when point is within 8px of the line."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    r1 = _room("r1", x=0, y=0, w=1, h=1)
    r2 = _room("r2", x=2, y=0, w=1, h=1)
    conn = _conn("r1", "r2")
    level = _level([r1, r2], connections=[conn])
    state = _state(visited_rooms=["r1", "r2"])
    renderer = GridRenderer(cell_px=48)

    # line is at y=24; point 6px above = y=30 → distance 6px < 8px
    result = renderer.hit_test_connection(level, state, x=72.0, y=30.0, origin_x=0.0, origin_y=0.0)

    assert result is conn


def test_hit_test_connection_bent_waypoint_path() -> None:
    """hit_test_connection returns Connection for a point on a bent (waypoint) path,
    not just on the straight center-to-center line."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    r1 = _room("r1", x=0, y=0, w=2, h=2)
    r2 = _room("r2", x=0, y=6, w=2, h=2)
    conn = Connection(**{"from": "r1", "to": "r2", "type": "normal", "waypoints": [{"x": 4, "y": 3}]})
    level = _level([r1, r2], connections=[conn])
    state = _state()
    renderer = GridRenderer(cell_px=48)

    # Path in grid: [(1,2), (4,3), (1,6)] → screen: [(48,96), (192,144), (48,288)]
    # Click at midpoint of first segment (120, 120) — this is NOT on the straight center line
    # (centers are both at x=48), so the old code would return None
    result = renderer.hit_test_connection(level, state, x=120.0, y=120.0, origin_x=0.0, origin_y=0.0)

    assert result is conn


def test_draw_uses_manual_waypoints_when_present() -> None:
    """draw() uses the waypoints path verbatim when conn.waypoints is set."""
    from dungeon_daddy.map.grid_renderer import GridRenderer

    # r1 east port (2,1), r2 west port (8,5) — straight path is clear (no blocker)
    # With waypoints the renderer must draw 3 segments instead of 1
    r1 = _room("r1", x=0, y=0, w=2, h=2)
    r2 = _room("r2", x=8, y=4, w=2, h=2)
    conn = Connection(**{
        "from": "r1", "to": "r2", "type": "door",
        "waypoints": [{"x": 4.0, "y": 1.0}, {"x": 4.0, "y": 5.0}],
    })
    level = _level([r1, r2], connections=[conn])
    state = _state(visited_rooms=["r1", "r2"])
    renderer = GridRenderer(cell_px=48)

    with patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line") as mock_line, \
         patch("arcade.draw_text"):
        renderer.draw(level, state, origin_x=0.0, origin_y=0.0)

    calls = mock_line.call_args_list
    assert len(calls) == 3
    # seg 0: from_port (2,1) → waypoint (4,1) in screen pixels
    assert calls[0].args[0] == pytest.approx(2 * 48)
    assert calls[0].args[1] == pytest.approx(1 * 48)
    assert calls[0].args[2] == pytest.approx(4 * 48)
    assert calls[0].args[3] == pytest.approx(1 * 48)
    # seg 2: waypoint (4,5) → to_port (8,5) in screen pixels
    assert calls[2].args[0] == pytest.approx(4 * 48)
    assert calls[2].args[1] == pytest.approx(5 * 48)
    assert calls[2].args[2] == pytest.approx(8 * 48)
    assert calls[2].args[3] == pytest.approx(5 * 48)


# ---------------------------------------------------------------------------
# debug_routing flag
# ---------------------------------------------------------------------------

