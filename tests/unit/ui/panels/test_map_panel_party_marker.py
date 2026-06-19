"""Tests for party-room wiring in MapPanel (Phase 48 manual-UI fix)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from dungeon_daddy.data.models import Level, Room, SessionState
from dungeon_daddy.ui.panels.map_panel import MapPanel


def _make_panel() -> MapPanel:
    panel = MapPanel(on_level_change=lambda _: None)
    panel._stepper = MagicMock()
    panel._x, panel._y, panel._w, panel._h = 440.0, 0.0, 800.0, 600.0
    return panel


def _make_level() -> Level:
    room = Room(id="r1", num=1, name="Hall", x=0, y=0, w=4, h=4, type="hall", note="")
    return Level(
        id=1, name="Level 1", summary="", ecology="", loop="",
        width=50, height=50, entries=[], rooms=[room], connections=[], loops=[],
    )


# ---------------------------------------------------------------------------
# set_selected_room — public API for moving the selection cursor
# ---------------------------------------------------------------------------

def test_set_selected_room_updates_view_state() -> None:
    panel = _make_panel()
    panel.set_selected_room("r5")
    assert panel._view_state.selected_room_id == "r5"


# ---------------------------------------------------------------------------
# draw — passes the party's current_room_id through to the renderer
# ---------------------------------------------------------------------------

def test_draw_passes_party_room_id_to_renderer() -> None:
    panel = _make_panel()
    panel._layout_renderer = MagicMock()
    panel._art = MagicMock()
    panel._level = _make_level()
    panel._state = SessionState(dungeon_id="d1", current_level_idx=0, current_room_id="r1")
    panel._layout_result = MagicMock()

    with patch("dungeon_daddy.ui.panels.map_panel.arcade"), \
            patch("dungeon_daddy.ui.panels.map_panel.draw_kicker"), \
            patch("dungeon_daddy.ui.panels.map_panel.draw_chip"):
        panel.draw()

    assert panel._layout_renderer.draw.call_args.kwargs["party_room_id"] == "r1"


def test_draw_passes_visited_rooms_to_renderer() -> None:
    panel = _make_panel()
    panel._layout_renderer = MagicMock()
    panel._art = MagicMock()
    panel._level = _make_level()
    panel._state = SessionState(
        dungeon_id="d1", current_level_idx=0, current_room_id="r1",
        visited_rooms=["r1", "r2"],
    )
    panel._layout_result = MagicMock()

    with patch("dungeon_daddy.ui.panels.map_panel.arcade"), \
            patch("dungeon_daddy.ui.panels.map_panel.draw_kicker"), \
            patch("dungeon_daddy.ui.panels.map_panel.draw_chip"):
        panel.draw()

    assert panel._layout_renderer.draw.call_args.kwargs["visited_rooms"] == ["r1", "r2"]
