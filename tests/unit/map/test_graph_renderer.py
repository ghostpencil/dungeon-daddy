"""Tests for GraphRenderer — abstract node graph style map renderer."""
from __future__ import annotations

from unittest.mock import patch

import math
import pytest

from dungeon_daddy.data.models import Connection, Level, Room, SessionState
from dungeon_daddy.map.grid_renderer import GridRenderer
from dungeon_daddy.map.graph_renderer import GraphRenderer, _NODE_RADIUS_CELLS
from dungeon_daddy.ui.theme import INK_1, INK_2


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _room(id: str, x: int = 0, y: int = 0) -> Room:
    return Room(id=id, num=1, name=id, x=x, y=y, w=3, h=3, type="hall", note="")


def _level(rooms: list[Room], connections: list[Connection] | None = None) -> Level:
    return Level(
        id=1, name="L1", summary="", ecology="", loop="",
        width=20, height=20, entries=[], rooms=rooms,
        connections=connections or [],
    )


def _conn(from_id: str, to_id: str) -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": "passage"})


def _state() -> SessionState:
    return SessionState(dungeon_id="test", current_level_idx=0)


# ---------------------------------------------------------------------------
# Behaviors
# ---------------------------------------------------------------------------


def test_graph_renderer_draw_calls_circle_per_room():
    renderer = GraphRenderer(cell_px=48)
    level = _level([_room("r1"), _room("r2", x=5)])

    with patch("dungeon_daddy.map.graph_renderer.arcade") as mock_arcade:
        renderer.draw(level, _state(), 0.0, 0.0)

    assert mock_arcade.draw_circle_filled.call_count >= 2


def test_graph_renderer_room_center_matches_grid_renderer():
    graph = GraphRenderer(cell_px=48)
    grid = GridRenderer(cell_px=48)
    room = _room("r1", x=1, y=4)

    assert graph.room_center(room, 5.0, 10.0, zoom=2.0) == grid.room_center(room, 5.0, 10.0, zoom=2.0)


# ---------------------------------------------------------------------------
# Connection lines drawn between circle edges, not room centers
# ---------------------------------------------------------------------------

def test_connection_line_starts_at_from_circle_edge():
    """draw_line x0 must be offset from from-room center by exactly one radius."""
    cell_px = 48
    renderer = GraphRenderer(cell_px=cell_px)
    r1 = _room("r1", x=0, y=0)
    r2 = _room("r2", x=5, y=0)
    level = _level([r1, r2], [_conn("r1", "r2")])

    with patch("dungeon_daddy.map.graph_renderer.arcade") as mock_arcade:
        renderer.draw(level, _state(), 0.0, 0.0)

    radius = _NODE_RADIUS_CELLS * cell_px
    fcx, fcy = renderer.room_center(r1, 0.0, 0.0)
    tcx, tcy = renderer.room_center(r2, 0.0, 0.0)
    dx, dy = tcx - fcx, tcy - fcy
    dist = math.hypot(dx, dy)
    expected_x0 = fcx + (dx / dist) * radius
    expected_y0 = fcy + (dy / dist) * radius

    line_call = mock_arcade.draw_line.call_args_list[0]
    assert line_call.args[0] == pytest.approx(expected_x0)
    assert line_call.args[1] == pytest.approx(expected_y0)


def test_connection_line_ends_at_to_circle_edge():
    """draw_line x1 must be offset from to-room center by exactly one radius (inward)."""
    cell_px = 48
    renderer = GraphRenderer(cell_px=cell_px)
    r1 = _room("r1", x=0, y=0)
    r2 = _room("r2", x=5, y=0)
    level = _level([r1, r2], [_conn("r1", "r2")])

    with patch("dungeon_daddy.map.graph_renderer.arcade") as mock_arcade:
        renderer.draw(level, _state(), 0.0, 0.0)

    radius = _NODE_RADIUS_CELLS * cell_px
    fcx, fcy = renderer.room_center(r1, 0.0, 0.0)
    tcx, tcy = renderer.room_center(r2, 0.0, 0.0)
    dx, dy = tcx - fcx, tcy - fcy
    dist = math.hypot(dx, dy)
    expected_x1 = tcx - (dx / dist) * radius
    expected_y1 = tcy - (dy / dist) * radius

    line_call = mock_arcade.draw_line.call_args_list[0]
    assert line_call.args[2] == pytest.approx(expected_x1)
    assert line_call.args[3] == pytest.approx(expected_y1)


def test_connection_line_does_not_start_at_room_center():
    """Confirm the line start is not the raw room center (guards against regression)."""
    cell_px = 48
    renderer = GraphRenderer(cell_px=cell_px)
    r1 = _room("r1", x=0, y=0)
    r2 = _room("r2", x=5, y=0)
    level = _level([r1, r2], [_conn("r1", "r2")])

    with patch("dungeon_daddy.map.graph_renderer.arcade") as mock_arcade:
        renderer.draw(level, _state(), 0.0, 0.0)

    fcx, fcy = renderer.room_center(r1, 0.0, 0.0)
    line_call = mock_arcade.draw_line.call_args_list[0]
    assert line_call.args[0] != pytest.approx(fcx)


# ---------------------------------------------------------------------------
# Room labels
# ---------------------------------------------------------------------------

def test_room_label_contains_name_and_id():
    renderer = GraphRenderer(cell_px=48)
    room = _room("r1")
    level = _level([room])

    with patch("dungeon_daddy.map.graph_renderer.arcade") as mock_arcade:
        renderer.draw(level, _state(), 0.0, 0.0)

    text_call = mock_arcade.draw_text.call_args_list[0]
    assert text_call.args[0] == f"{room.name} ({room.id})"


def test_room_label_color_is_ink2_for_non_current():
    renderer = GraphRenderer(cell_px=48)
    level = _level([_room("r1")])

    with patch("dungeon_daddy.map.graph_renderer.arcade") as mock_arcade:
        renderer.draw(level, _state(), 0.0, 0.0)

    text_call = mock_arcade.draw_text.call_args_list[0]
    assert text_call.args[3] == INK_2


def test_room_label_color_is_ink1_for_current_room():
    renderer = GraphRenderer(cell_px=48)
    level = _level([_room("r1")])
    state = SessionState(dungeon_id="test", current_level_idx=0, current_room_id="r1")

    with patch("dungeon_daddy.map.graph_renderer.arcade") as mock_arcade:
        renderer.draw(level, state, 0.0, 0.0)

    text_call = mock_arcade.draw_text.call_args_list[0]
    assert text_call.args[3] == INK_1
