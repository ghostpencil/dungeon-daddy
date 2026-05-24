"""Tests for TilesRenderer — shaded tile style map renderer."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

from dungeon_daddy.data.models import Connection, Level, Room, SessionState
from dungeon_daddy.map.grid_renderer import GridRenderer
from dungeon_daddy.map.tiles_renderer import TilesRenderer, _TILE_SHADE
from dungeon_daddy.ui.theme import ROOM_COLORS, ROOM_UNSEEN_FILL, ROOM_UNSEEN_STROKE, TEAL


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _room(id: str, x: int = 0, y: int = 0) -> Room:
    return Room(id=id, num=1, name=id, x=x, y=y, w=3, h=3, type="hall", note="")


def _level(rooms: list[Room]) -> Level:
    return Level(
        id=1, name="L1", summary="", ecology="", loop="",
        width=20, height=20, entries=[], rooms=rooms, connections=[],
    )


def _state() -> SessionState:
    return SessionState(dungeon_id="test", current_level_idx=0)


# ---------------------------------------------------------------------------
# Behaviors
# ---------------------------------------------------------------------------


def test_tiles_renderer_draw_calls_arcade_per_room():
    renderer = TilesRenderer(cell_px=48)
    level = _level([_room("r1"), _room("r2", x=5)])

    with patch("dungeon_daddy.map.tiles_renderer.arcade") as mock_arcade:
        renderer.draw(level, _state(), 0.0, 0.0)

    assert mock_arcade.draw_rect_filled.call_count >= 2


def test_tiles_renderer_room_center_matches_grid_renderer():
    tiles = TilesRenderer(cell_px=48)
    grid = GridRenderer(cell_px=48)
    room = _room("r1", x=2, y=3)

    assert tiles.room_center(room, 10.0, 20.0, zoom=1.5) == grid.room_center(room, 10.0, 20.0, zoom=1.5)


# ---------------------------------------------------------------------------
# Visited / unvisited color logic
# ---------------------------------------------------------------------------

def test_unvisited_room_uses_unseen_fill():
    renderer = TilesRenderer(cell_px=48)
    level = _level([_room("r1")])

    with patch("dungeon_daddy.map.tiles_renderer.arcade") as mock_arcade:
        renderer.draw(level, _state(), 0.0, 0.0)

    first_fill = mock_arcade.draw_rect_filled.call_args_list[0]
    assert first_fill.args[1] == ROOM_UNSEEN_FILL


def test_unvisited_room_uses_unseen_stroke():
    renderer = TilesRenderer(cell_px=48)
    level = _level([_room("r1")])

    with patch("dungeon_daddy.map.tiles_renderer.arcade") as mock_arcade:
        renderer.draw(level, _state(), 0.0, 0.0)

    outline = mock_arcade.draw_rect_outline.call_args_list[0]
    assert outline.args[1] == ROOM_UNSEEN_STROKE


def test_visited_room_uses_theme_fill():
    renderer = TilesRenderer(cell_px=48)
    level = _level([_room("r1")])
    state = SessionState(dungeon_id="test", current_level_idx=0, visited_rooms=["r1"])

    with patch("dungeon_daddy.map.tiles_renderer.arcade") as mock_arcade:
        renderer.draw(level, state, 0.0, 0.0)

    first_fill = mock_arcade.draw_rect_filled.call_args_list[0]
    assert first_fill.args[1] == ROOM_COLORS["hall"]["fill"]


def test_visited_room_uses_theme_stroke():
    renderer = TilesRenderer(cell_px=48)
    level = _level([_room("r1")])
    state = SessionState(dungeon_id="test", current_level_idx=0, visited_rooms=["r1"])

    with patch("dungeon_daddy.map.tiles_renderer.arcade") as mock_arcade:
        renderer.draw(level, state, 0.0, 0.0)

    outline = mock_arcade.draw_rect_outline.call_args_list[0]
    assert outline.args[1] == ROOM_COLORS["hall"]["stroke"]


def test_current_room_uses_teal_stroke():
    renderer = TilesRenderer(cell_px=48)
    level = _level([_room("r1")])
    state = SessionState(dungeon_id="test", current_level_idx=0, current_room_id="r1")

    with patch("dungeon_daddy.map.tiles_renderer.arcade") as mock_arcade:
        renderer.draw(level, state, 0.0, 0.0)

    outline = mock_arcade.draw_rect_outline.call_args_list[0]
    assert outline.args[1] == TEAL


def test_current_room_uses_theme_fill_not_unseen():
    renderer = TilesRenderer(cell_px=48)
    level = _level([_room("r1")])
    state = SessionState(dungeon_id="test", current_level_idx=0, current_room_id="r1")

    with patch("dungeon_daddy.map.tiles_renderer.arcade") as mock_arcade:
        renderer.draw(level, state, 0.0, 0.0)

    first_fill = mock_arcade.draw_rect_filled.call_args_list[0]
    assert first_fill.args[1] != ROOM_UNSEEN_FILL


def test_tile_shade_always_applied():
    renderer = TilesRenderer(cell_px=48)
    level = _level([_room("r1")])

    with patch("dungeon_daddy.map.tiles_renderer.arcade") as mock_arcade:
        renderer.draw(level, _state(), 0.0, 0.0)

    second_fill = mock_arcade.draw_rect_filled.call_args_list[1]
    assert second_fill.args[1] == _TILE_SHADE
