"""Tests for Phase 48 Slice 10 — party-move engine command in PlayView.

(The right-panel EXITS/Move tab was retired in Phase 50.6 — moving is now driven
by the "Things Here" overlay + in-chat builder. The ``_on_exit_move`` engine
command they call is exercised here.)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import RoomExit

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy" / "data" / "migrations"
)


def _save_exit(repo: MemoryRepository, **kw) -> RoomExit:
    defaults = dict(
        exit_id="e1", campaign_id="camp-1",
        from_room_id="r1", to_room_id="r2", level_id="level-1",
        label="North Door", exit_type="door", status="open",
    )
    defaults.update(kw)
    ex = RoomExit(**defaults)
    repo.save_room_exit(ex)
    return ex


def _make_view(tmp_path: Path):
    from dungeon_daddy.views.play_view import PlayView

    mem_repo = MemoryRepository(tmp_path / "test.duckdb")
    mem_repo.initialize_schema(MIGRATIONS_DIR)
    mem_repo.save_campaign("camp-1", "test-campaign", "Test Campaign")

    view = PlayView.__new__(PlayView)
    view._mem_repo = mem_repo
    view._rpg_campaign_id = "camp-1"
    view._state = SessionState(
        dungeon_id="d1", current_level_idx=0,
        current_room_id="r1", visited_rooms=["r1"],
    )
    view._dungeon = None
    view._chat = MagicMock()
    view._map = MagicMock()
    view._rpg_scene = MagicMock()
    view._rpg_action = MagicMock()
    view._narration.spawn_dm_thread = MagicMock()
    view._narration.compact_history = MagicMock()
    view._save_session = MagicMock()
    view._dm_history = []
    return view


# ---------------------------------------------------------------------------
# _on_exit_move — runs the engine command and updates session state
# ---------------------------------------------------------------------------

def test_on_exit_move_updates_current_room(tmp_path):
    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, status="open")

    view._on_exit_move("e1", "cautiously")

    assert view._state.current_room_id == "r2"
    assert "r2" in view._state.visited_rooms


def test_on_exit_move_rejected_keeps_room_and_warns(tmp_path):
    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, status="locked", requires_item_slug="iron-key")

    view._on_exit_move("e1", "cautiously")

    assert view._state.current_room_id == "r1"
    view._chat.add_message.assert_called_once()
    assert view._chat.add_message.call_args.args[0] == "system"
