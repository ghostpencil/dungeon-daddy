"""Tests for fog-of-war room-name hiding in LayoutRenderer (Phase 48 Slice 10)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from dungeon_daddy.map.dungeon_layout import LayoutResult
from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
from dungeon_daddy.map.dungeon_layout.models import LayoutBounds, RoomRect
from dungeon_daddy.map.layout_renderer import LayoutRenderer
from dungeon_daddy.ui.fog_of_war import HIDDEN_LABEL

_FRAME_NAMES = ("default", "current", "hover", "locked", "memory", "danger")


def _room(room_id: str, x: float = 0.0, y: float = 0.0) -> RoomRect:
    return RoomRect(room_id=room_id, x=x, y=y, w=120.0, h=80.0)


def _result(rooms: dict[str, RoomRect], room_names: dict[str, str]) -> LayoutResult:
    bounds = LayoutBounds(min_x=0.0, min_y=0.0, max_x=500.0, max_y=400.0)
    return LayoutResult(
        rooms=rooms,
        edges=[],
        labels=[],
        bounds=bounds,
        debug_overlay=DebugOverlay(enabled=False, bounds=bounds),
        room_names=room_names,
        room_roles={},
        edge_labels={},
        critical_path=[],
    )


def _make_art() -> MagicMock:
    art = MagicMock()
    art.frames = {name: MagicMock() for name in _FRAME_NAMES}
    return art


def _label_texts(mock_arcade: MagicMock) -> list[str]:
    return [c.args[0] for c in mock_arcade.draw_text.call_args_list if c.args]


# Cycle 1 — an unvisited room's label is hidden behind '?'
def test_unvisited_room_label_hidden() -> None:
    rooms = {"r1": _room("r1"), "r2": _room("r2", 200.0, 0.0)}
    renderer = LayoutRenderer()
    renderer._art = _make_art()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(
            _result(rooms, {"r1": "Alpha", "r2": "Beta"}),
            origin_x=0.0, origin_y=0.0, zoom=1.0,
            visited_rooms=["r1"], party_room_id="r1",
        )

    texts = _label_texts(mock_arcade)
    assert any("Alpha" in t for t in texts)
    assert all("Beta" not in t for t in texts)
    assert HIDDEN_LABEL in texts


# Cycle 2 — the party's current room is always revealed even if unvisited
def test_party_room_revealed_even_if_unvisited() -> None:
    rooms = {"r1": _room("r1")}
    renderer = LayoutRenderer()
    renderer._art = _make_art()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(
            _result(rooms, {"r1": "Alpha"}),
            origin_x=0.0, origin_y=0.0, zoom=1.0,
            visited_rooms=[], party_room_id="r1",
        )

    texts = _label_texts(mock_arcade)
    assert any("Alpha" in t for t in texts)


# Cycle 3 — with no visited_rooms passed (default), nothing is fogged
def test_no_fog_when_visited_rooms_not_supplied() -> None:
    rooms = {"r1": _room("r1")}
    renderer = LayoutRenderer()
    renderer._art = _make_art()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(
            _result(rooms, {"r1": "Alpha"}),
            origin_x=0.0, origin_y=0.0, zoom=1.0,
        )

    texts = _label_texts(mock_arcade)
    assert any("Alpha" in t for t in texts)
    assert HIDDEN_LABEL not in texts
