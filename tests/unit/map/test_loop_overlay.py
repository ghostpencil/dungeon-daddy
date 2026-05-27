"""Tests for LoopOverlay — patch arcade.draw_* so no display is needed."""
from __future__ import annotations

from unittest.mock import patch

from dungeon_daddy.data.models import Level, Loop, Room, SessionState
from dungeon_daddy.map.grid_renderer import GridRenderer
from dungeon_daddy.ui.theme import PATH_A_COLOR, PATH_B_COLOR

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _room(id: str, x: int, y: int, w: int = 1, h: int = 1) -> Room:
    return Room(id=id, num=1, name=id, x=x, y=y, w=w, h=h, type="hall", note="")


def _loop(id: str, path_a: list[str], path_b: list[str]) -> Loop:
    return Loop(
        id=id, pattern="test", note="",
        entry=path_a[0] if path_a else "",
        goal=path_a[-1] if path_a else "",
        path_a=path_a,
        path_b=path_b,
    )


def _level(rooms: list[Room], loops: list[Loop] | None = None) -> Level:
    return Level(
        id=1, name="T", summary="", ecology="", loop="",
        width=20, height=20, entries=[], rooms=rooms,
        connections=[], loops=loops or [],
    )


def _state(**kwargs) -> SessionState:
    defaults: dict = dict(dungeon_id="test", current_level_idx=0, visited_rooms=[])
    defaults.update(kwargs)
    return SessionState(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_draws_path_a_in_teal() -> None:
    """draw() draws lines between consecutive path_a rooms using PATH_A_COLOR."""
    from dungeon_daddy.map.loop_overlay import LoopOverlay

    r1 = _room("r1", x=0, y=0)
    r2 = _room("r2", x=2, y=0)
    loop = _loop("lp1", path_a=["r1", "r2"], path_b=[])
    level = _level([r1, r2], loops=[loop])
    state = _state(active_loop_id="lp1")
    renderer = GridRenderer(cell_px=48)
    overlay = LoopOverlay()

    with patch("arcade.draw_line") as mock_line:
        overlay.draw(level, state, renderer, origin_x=0.0, origin_y=0.0)

    assert mock_line.called
    _x1, _y1, _x2, _y2, color, *_ = mock_line.call_args[0]
    assert color == PATH_A_COLOR


def test_draws_path_b_in_violet() -> None:
    """draw() draws lines between consecutive path_b rooms using PATH_B_COLOR."""
    from dungeon_daddy.map.loop_overlay import LoopOverlay

    r1 = _room("r1", x=0, y=0)
    r2 = _room("r2", x=2, y=0)
    loop = _loop("lp1", path_a=[], path_b=["r1", "r2"])
    level = _level([r1, r2], loops=[loop])
    state = _state(active_loop_id="lp1")
    renderer = GridRenderer(cell_px=48)
    overlay = LoopOverlay()

    with patch("arcade.draw_line") as mock_line:
        overlay.draw(level, state, renderer, origin_x=0.0, origin_y=0.0)

    assert mock_line.called
    _x1, _y1, _x2, _y2, color, *_ = mock_line.call_args[0]
    assert color == PATH_B_COLOR


def test_zoom_scales_path_line_positions() -> None:
    """draw() at zoom=2.0 doubles the screen coordinates of path lines."""
    import pytest

    from dungeon_daddy.map.loop_overlay import LoopOverlay

    r1 = _room("r1", x=0, y=0)
    r2 = _room("r2", x=2, y=0)
    loop = _loop("lp1", path_a=["r1", "r2"], path_b=[])
    level = _level([r1, r2], loops=[loop])
    state = _state(active_loop_id="lp1")
    renderer = GridRenderer(cell_px=48)
    overlay = LoopOverlay()

    coords: dict[float, tuple] = {}
    for z in (1.0, 2.0):
        with patch("arcade.draw_line") as mock_line:
            overlay.draw(level, state, renderer, origin_x=0.0, origin_y=0.0, zoom=z)
        coords[z] = mock_line.call_args[0][:4]

    x1_1, y1_1, x2_1, y2_1 = coords[1.0]
    x1_2, y1_2, x2_2, y2_2 = coords[2.0]
    assert x1_2 == pytest.approx(x1_1 * 2)
    assert x2_2 == pytest.approx(x2_1 * 2)


def test_no_draw_when_no_active_loop() -> None:
    """draw() makes no arcade calls when state.active_loop_id is None."""
    from dungeon_daddy.map.loop_overlay import LoopOverlay

    r1 = _room("r1", x=0, y=0)
    r2 = _room("r2", x=2, y=0)
    loop = _loop("lp1", path_a=["r1", "r2"], path_b=[])
    level = _level([r1, r2], loops=[loop])
    state = _state(active_loop_id=None)
    renderer = GridRenderer(cell_px=48)
    overlay = LoopOverlay()

    with patch("arcade.draw_line") as mock_line:
        overlay.draw(level, state, renderer, origin_x=0.0, origin_y=0.0)

    mock_line.assert_not_called()
