"""Tests for Phase 48 Slice 10 — exit panel wiring in PlayView."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import RoomExit, RoomObject
from dungeon_daddy.ui.panels.exit_list_panel import ExitListPanel

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
    view._exit_panel = ExitListPanel()
    view._exit_panel.set_move_callback(view._on_exit_move)
    view._chat = MagicMock()
    view._map = MagicMock()
    view._rpg_scene = MagicMock()
    view._rpg_action = MagicMock(_actors=[])
    view._spawn_dm_thread = MagicMock()
    view._compact_history = MagicMock()
    view._save_session = MagicMock()
    view._dm_history = []
    return view


# ---------------------------------------------------------------------------
# _refresh_exits — populates the panel from build_room_context
# ---------------------------------------------------------------------------

def test_refresh_exits_populates_visible_exit(tmp_path):
    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, label="North Door", status="open")

    view._refresh_exits()

    labels = [e["label"] for e in view._exit_panel._visible_exits]
    assert "North Door" in labels


def test_refresh_exits_lists_locked_exit_with_reason(tmp_path):
    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, status="locked", requires_item_slug="iron-key")

    view._refresh_exits()

    assert view._exit_panel._locked_exits[0]["missing_condition"] == "iron-key"


def _save_trap(repo: MemoryRepository, state: str) -> None:
    repo.save_room_object(RoomObject(
        object_id="o-trap", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="dart-trap", display_name="Dart Trap", archetype="trap",
        description="A pressure plate.", current_state=state,
    ))


def test_refresh_exits_surfaces_recklessly_chip_for_armed_trap(tmp_path):
    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, status="open")
    _save_trap(view._mem_repo, state="armed")

    view._refresh_exits()

    hows = [c.how for c in view._exit_panel._how_chips]
    assert "recklessly" in hows


def test_refresh_exits_no_recklessly_chip_when_trap_disarmed(tmp_path):
    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, status="open")
    _save_trap(view._mem_repo, state="disarmed")

    view._refresh_exits()

    hows = [c.how for c in view._exit_panel._how_chips]
    assert "recklessly" not in hows


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


def test_clicking_exit_in_panel_triggers_move(tmp_path):
    """End-to-end through the panel: click an exit row -> engine move."""
    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, status="open")
    view._refresh_exits()
    view._exit_panel.setup(0.0, 0.0, 240.0, 360.0)

    layout = view._exit_panel._layout()
    _eid, _label, _status, (ex, ey, ew, eh) = layout["exits"][0]
    view._exit_panel.handle_click(ex + ew / 2, ey + eh / 2)

    assert view._state.current_room_id == "r2"
