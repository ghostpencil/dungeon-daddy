"""Tests for the party-location marker in LayoutRenderer (Phase 48 manual-UI fix)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from dungeon_daddy.map.dungeon_layout import LayoutResult
from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
from dungeon_daddy.map.dungeon_layout.models import LayoutBounds, RoomRect
from dungeon_daddy.map.layout_renderer import LayoutRenderer
from dungeon_daddy.ui.theme import GOLD

_FRAME_NAMES = ("default", "current", "hover", "locked", "memory", "danger")


def _room(room_id: str, x: float = 0.0, y: float = 0.0) -> RoomRect:
    return RoomRect(room_id=room_id, x=x, y=y, w=120.0, h=80.0)


def _result(rooms: dict[str, RoomRect]) -> LayoutResult:
    bounds = LayoutBounds(min_x=0.0, min_y=0.0, max_x=500.0, max_y=400.0)
    return LayoutResult(
        rooms=rooms,
        edges=[],
        labels=[],
        bounds=bounds,
        debug_overlay=DebugOverlay(enabled=False, bounds=bounds),
        room_names={},
        room_roles={},
        edge_labels={},
        critical_path=[],
    )


def _make_art() -> MagicMock:
    art = MagicMock()
    art.frames = {name: MagicMock() for name in _FRAME_NAMES}
    return art


def _gold_outline_calls(mock_arcade: MagicMock) -> list:
    return [c for c in mock_arcade.draw_rect_outline.call_args_list if GOLD in c.args]


# ---------------------------------------------------------------------------
# Cycle 1 — a GOLD party marker is drawn for the party's room only
# ---------------------------------------------------------------------------

def test_party_marker_drawn_for_party_room() -> None:
    rooms = {"r1": _room("r1"), "r2": _room("r2", 200.0, 0.0)}
    renderer = LayoutRenderer()
    renderer._art = _make_art()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(_result(rooms), origin_x=0.0, origin_y=0.0, zoom=1.0, party_room_id="r1")

    assert len(_gold_outline_calls(mock_arcade)) == 1


# ---------------------------------------------------------------------------
# Cycle 2 — no party marker when no party room is supplied
# ---------------------------------------------------------------------------

def test_no_party_marker_when_party_room_none() -> None:
    rooms = {"r1": _room("r1")}
    renderer = LayoutRenderer()
    renderer._art = _make_art()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(_result(rooms), origin_x=0.0, origin_y=0.0, zoom=1.0, party_room_id=None)

    assert _gold_outline_calls(mock_arcade) == []
