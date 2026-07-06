"""Tests for party-location focus on move + load (Phase 48 manual-UI fix)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level, Room, SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import RoomExit

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy" / "data" / "migrations"
)


def _dungeon() -> Dungeon:
    rooms = [
        Room(id="r1", num=1, name="Entry Hall", x=0, y=0, w=4, h=4, type="hall", note="a"),
        Room(id="r2", num=2, name="North Vault", x=6, y=0, w=4, h=4, type="vault", note="b"),
    ]
    level = Level(
        id=1, name="Level 1", summary="", ecology="", loop="",
        width=50, height=50, entries=[], rooms=rooms, connections=[], loops=[],
    )
    meta = DungeonMeta(title="T", theme="", setting="", party="", quest="")
    return Dungeon(meta=meta, levels=[level])


def _make_view(tmp_path: Path, current_room_id: str = "r1"):
    from dungeon_daddy.views.play_view import PlayView

    mem_repo = MemoryRepository(tmp_path / "test.duckdb")
    mem_repo.initialize_schema(MIGRATIONS_DIR)
    mem_repo.save_campaign("camp-1", "test-campaign", "Test Campaign")

    view = PlayView.__new__(PlayView)
    view._mem_repo = mem_repo
    view._rpg_campaign_id = "camp-1"
    view._state = SessionState(
        dungeon_id="d1", current_level_idx=0,
        current_room_id=current_room_id, visited_rooms=[current_room_id],
    )
    view._dungeon = _dungeon()
    view._map = MagicMock()
    view._chat = MagicMock()
    view._rpg_scene = MagicMock()
    view._rpg_action = MagicMock()
    view._narration.spawn_dm_thread = MagicMock()
    view._narration.compact_history = MagicMock()
    view._save_session = MagicMock()
    view._dm_history = []
    return view


def _save_exit(repo: MemoryRepository) -> None:
    repo.save_room_exit(RoomExit(
        exit_id="e1", campaign_id="camp-1",
        from_room_id="r1", to_room_id="r2", level_id="level-1",
        label="North Door", exit_type="door", status="open",
    ))


# ---------------------------------------------------------------------------
# Moving via an exit moves the map selection cursor to the new room
# ---------------------------------------------------------------------------

def test_on_exit_move_selects_destination_room_on_map(tmp_path):
    view = _make_view(tmp_path)
    _save_exit(view._mem_repo)

    view._on_exit_move("e1", "cautiously")

    assert view._state.current_room_id == "r2"
    view._map.set_selected_room.assert_called_once_with("r2")


# ---------------------------------------------------------------------------
# _focus_party_room — reflect the saved party room in map + side panels
# ---------------------------------------------------------------------------

def test_focus_party_room_sets_map_selection_and_panels(tmp_path):
    view = _make_view(tmp_path, current_room_id="r2")

    view._focus_party_room()

    view._map.set_selected_room.assert_called_once_with("r2")
    view._chat.set_current_room.assert_called_once()
    assert view._chat.set_current_room.call_args.args[0] == "North Vault"
    view._rpg_scene.set_scene.assert_called_once()


def test_focus_party_room_noop_when_no_current_room(tmp_path):
    view = _make_view(tmp_path, current_room_id="r1")
    view._state.current_room_id = None

    view._focus_party_room()

    view._map.set_selected_room.assert_not_called()
    view._chat.set_current_room.assert_not_called()
