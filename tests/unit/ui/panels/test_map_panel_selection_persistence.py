"""Tests for selected-room persistence across level switches (bug fix)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_panel():
    from dungeon_daddy.ui.panels.map_panel import MapPanel
    renderer = MagicMock()
    renderer.cell_px = 48
    panel = MapPanel(
        on_level_change=lambda _: None,
        renderer=renderer,
        overlay=MagicMock(),
    )
    panel._stepper = MagicMock()
    panel._x, panel._y, panel._w, panel._h = 440.0, 0.0, 800.0, 600.0
    return panel


def _make_level(level_id: int = 1, room_id: str = "r1"):
    from dungeon_daddy.data.models import Level, Room
    room = Room(id=room_id, num=1, name="Test Room", x=0, y=0, w=4, h=4, type="hall", note="")
    return Level(
        id=level_id, name=f"Level {level_id}", summary="", ecology="", loop="",
        width=50, height=50, entries=[], rooms=[room], connections=[],
        loops=[],
    )


def _make_state(level_idx: int = 0):
    from dungeon_daddy.data.models import SessionState
    return SessionState(dungeon_id="test", current_level_idx=level_idx, active_loop_id=None)


def _fake_layout():
    result = MagicMock()
    result.bounds = MagicMock(width=100.0, height=100.0, min_x=0.0, max_x=100.0, min_y=0.0, max_y=100.0)
    return result


# ---------------------------------------------------------------------------
# Cycle 1 — selection is restored when returning to a previously visited level
# ---------------------------------------------------------------------------

def test_selection_preserved_when_returning_to_level() -> None:
    panel = _make_panel()

    with patch("dungeon_daddy.ui.panels.map_panel.run_layout_pipeline", return_value=_fake_layout()):
        panel.load(_make_level(1, "r1"), _make_state(level_idx=0))
        panel._view_state.selected_room_id = "r1"

        panel.load(_make_level(2, "r2"), _make_state(level_idx=1))
        assert panel._view_state.selected_room_id is None

        panel.load(_make_level(1, "r1"), _make_state(level_idx=0))
        assert panel._view_state.selected_room_id == "r1"


# ---------------------------------------------------------------------------
# Cycle 2 — first visit to a level starts with no selection
# ---------------------------------------------------------------------------

def test_first_visit_to_level_has_no_selection() -> None:
    panel = _make_panel()

    with patch("dungeon_daddy.ui.panels.map_panel.run_layout_pipeline", return_value=_fake_layout()):
        panel.load(_make_level(1, "r1"), _make_state(level_idx=0))
        assert panel._view_state.selected_room_id is None
