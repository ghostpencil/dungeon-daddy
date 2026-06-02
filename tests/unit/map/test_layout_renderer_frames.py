"""Tests for room frame texture drawing in LayoutRenderer (VP-3 / VP-4)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from dungeon_daddy.map.dungeon_layout import LayoutResult
from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState
from dungeon_daddy.map.dungeon_layout.models import LayoutBounds, RoomRect, RoutedEdge
from dungeon_daddy.map.layout_renderer import LayoutRenderer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FRAME_NAMES = ("default", "current", "hover", "locked", "memory", "danger")


def _room(room_id: str, x: float = 0.0, y: float = 0.0) -> RoomRect:
    return RoomRect(room_id=room_id, x=x, y=y, w=120.0, h=80.0)


def _result(rooms: dict[str, RoomRect] | None = None) -> LayoutResult:
    bounds = LayoutBounds(min_x=0.0, min_y=0.0, max_x=500.0, max_y=400.0)
    return LayoutResult(
        rooms=rooms or {},
        edges=[],
        labels=[],
        bounds=bounds,
        debug_overlay=DebugOverlay(enabled=False, bounds=bounds),
        room_names={},
        room_roles={},
        edge_labels={},
        critical_path=[],
    )


def _make_art(tex: object) -> MagicMock:
    art = MagicMock()
    art.frames = {name: tex for name in _FRAME_NAMES}
    return art


def _make_art_keyed() -> tuple[MagicMock, dict[str, MagicMock]]:
    """Returns (art_mock, {frame_name: unique_texture_mock})."""
    textures: dict[str, MagicMock] = {name: MagicMock(name=f"tex_{name}") for name in _FRAME_NAMES}
    art = MagicMock()
    art.frames = textures
    return art, textures


# ---------------------------------------------------------------------------
# Cycle 1 — frame drawn once per room when default texture available
# ---------------------------------------------------------------------------

def test_frame_drawn_per_room() -> None:
    rooms = {"r1": _room("r1"), "r2": _room("r2", 200.0, 0.0)}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()
    fake_tex = MagicMock()
    renderer._art = _make_art(fake_tex)

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0)

    frame_calls = [c for c in mock_arcade.draw_texture_rect.call_args_list if c.args[0] is fake_tex]
    assert len(frame_calls) == 2


# ---------------------------------------------------------------------------
# Cycle 2 — no crash when default frame texture is None
# ---------------------------------------------------------------------------

def test_no_crash_when_default_frame_is_none() -> None:
    rooms = {"r1": _room("r1")}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()
    renderer._art = _make_art(None)

    with patch("dungeon_daddy.map.layout_renderer.arcade"):
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0)  # must not raise


# ---------------------------------------------------------------------------
# Cycle 3 — frame rect dimensions are 136*zoom × 96*zoom
# ---------------------------------------------------------------------------

def test_frame_rect_dimensions_scale_with_zoom() -> None:
    rooms = {"r1": _room("r1")}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()
    fake_tex = MagicMock()
    renderer._art = _make_art(fake_tex)

    zoom = 1.5
    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=zoom)

    xywh_args = [c.args for c in mock_arcade.XYWH.call_args_list]
    frame_matches = [args for args in xywh_args if len(args) >= 4 and abs(args[2] - 136 * zoom) < 0.1]
    assert frame_matches, "No XYWH call with width 136*zoom"
    assert abs(frame_matches[0][3] - 96 * zoom) < 0.1


# ---------------------------------------------------------------------------
# Cycle 4 — frame_current used when selected_room_id param matches the room
# ---------------------------------------------------------------------------

def test_frame_current_for_selected_room_id_param() -> None:
    rooms = {"r1": _room("r1")}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()
    art, textures = _make_art_keyed()
    renderer._art = art

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0, selected_room_id="r1")

    used_textures = [c.args[0] for c in mock_arcade.draw_texture_rect.call_args_list]
    assert textures["current"] in used_textures
    assert textures["default"] not in used_textures


# ---------------------------------------------------------------------------
# Cycle 5 — frame_current used when view_state.selected_room_id matches
# ---------------------------------------------------------------------------

def test_frame_current_for_view_state_selected() -> None:
    rooms = {"r1": _room("r1")}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()
    art, textures = _make_art_keyed()
    renderer._art = art
    view_state = GraphViewState(selected_room_id="r1")

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0, view_state=view_state)

    used_textures = [c.args[0] for c in mock_arcade.draw_texture_rect.call_args_list]
    assert textures["current"] in used_textures
    assert textures["default"] not in used_textures


# ---------------------------------------------------------------------------
# Cycle 6 — frame_hover used when view_state.hovered_room_id matches (not selected)
# ---------------------------------------------------------------------------

def test_frame_hover_for_hovered_room() -> None:
    rooms = {"r1": _room("r1")}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()
    art, textures = _make_art_keyed()
    renderer._art = art
    view_state = GraphViewState(hovered_room_id="r1")

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0, view_state=view_state)

    used_textures = [c.args[0] for c in mock_arcade.draw_texture_rect.call_args_list]
    assert textures["hover"] in used_textures
    assert textures["default"] not in used_textures


# ---------------------------------------------------------------------------
# Cycle 7 — frame_current wins over frame_hover when room is both selected and hovered
# ---------------------------------------------------------------------------

def test_frame_current_beats_hover_when_both() -> None:
    rooms = {"r1": _room("r1")}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()
    art, textures = _make_art_keyed()
    renderer._art = art
    view_state = GraphViewState(selected_room_id="r1", hovered_room_id="r1")

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0, view_state=view_state)

    used_textures = [c.args[0] for c in mock_arcade.draw_texture_rect.call_args_list]
    assert textures["current"] in used_textures
    assert textures["hover"] not in used_textures
