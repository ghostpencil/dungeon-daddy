"""Tests for Phase 33 — ACTION tab registration and ContextBundle handoff."""
from __future__ import annotations

import queue
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dungeon_daddy.data.models import (
    Dungeon,
    DungeonMeta,
    Level,
    Room,
    SessionState,
)
from dungeon_daddy.memory.repository import MemoryRepository

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


# ---------------------------------------------------------------------------
# Helpers for _RpgSidePanel lifecycle tests
# ---------------------------------------------------------------------------

def _make_rpg_side(active: int = 0):
    from unittest.mock import MagicMock
    from dungeon_daddy.views.play_view import _RpgSidePanel
    char, scene, fallout = MagicMock(), MagicMock(), MagicMock()
    mem = MagicMock()
    action = MagicMock()
    manager = MagicMock()
    panel = _RpgSidePanel(char, scene, fallout, mem, action, None, manager=manager)
    panel._x, panel._y, panel._w, panel._h = 0.0, 0.0, 300.0, 500.0
    panel._tab_rects = []
    panel._active = active
    return panel, manager, action


# ---------------------------------------------------------------------------
# Slice 4 — ACTION tab registered in _RPG_TAB_LABELS
# ---------------------------------------------------------------------------

def test_action_tab_in_rpg_tab_labels():
    from dungeon_daddy.views.play_view import _RPG_TAB_LABELS
    assert "ACTION" in _RPG_TAB_LABELS


# ---------------------------------------------------------------------------
# Helpers for PlayView bundle tests
# ---------------------------------------------------------------------------

def _room() -> Room:
    return Room(id="r1", num=1, name="Hall", x=0, y=0, w=2, h=2, type="hall", note="")


def _level(room: Room) -> Level:
    return Level(
        id=1, name="L1", summary="", ecology="", loop="",
        loops=[], width=20, height=20, entries=[],
        rooms=[room], connections=[],
    )


def _dungeon(level: Level) -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q"),
        levels=[level],
    )


def _make_view(tmp_path: Path, with_rpg: bool = True):
    from dungeon_daddy.views.play_view import PlayView

    room = _room()
    level = _level(room)
    dungeon = _dungeon(level)

    mem_repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
    mem_repo.initialize_schema(MIGRATIONS_DIR)

    view = PlayView.__new__(PlayView)
    view._dungeon = dungeon
    view._state = SessionState(
        dungeon_id="camp-1",
        current_level_idx=0,
        visited_rooms=[],
        current_room_id="r1",
    )
    view.window = MagicMock()
    view._menu_bar = MagicMock()
    view._map = MagicMock()
    view._chat = MagicMock()
    view._renderer = MagicMock()
    view._repo = MagicMock()
    view._repo.load_room_memory.return_value = ""
    view._result_queue = queue.Queue()
    view._llm_busy = False
    view._active_thread = None
    view._dm_history = []
    view._dm_agent = MagicMock()
    view._dm_agent.respond.return_value = "The dungeon rumbles."
    view._mem_repo = mem_repo if with_rpg else None
    view._rpg_service = MagicMock() if with_rpg else None
    view._rpg_debug = MagicMock() if with_rpg else None
    view._rpg_campaign_id = None
    return view, room, level


# ---------------------------------------------------------------------------
# Slice 7 — _RpgSidePanel: set_active(ACTION) calls action.setup_widget
# ---------------------------------------------------------------------------

class TestRpgSidePanelActionLifecycle:
    def test_set_active_action_tab_calls_setup_widget(self):
        from dungeon_daddy.views.play_view import _TAB_ACTION
        panel, manager, action = _make_rpg_side(active=0)
        panel.set_active(_TAB_ACTION)
        action.setup_widget.assert_called_once()

    def test_leaving_action_tab_calls_teardown_widget(self):
        from dungeon_daddy.views.play_view import _TAB_ACTION
        panel, manager, action = _make_rpg_side(active=_TAB_ACTION)
        panel.set_active(0)
        action.teardown_widget.assert_called_once()

    def test_setup_widget_receives_manager_and_dimensions(self):
        from dungeon_daddy.views.play_view import _TAB_ACTION, _RPG_TAB_H
        panel, manager, action = _make_rpg_side(active=0)
        panel.set_active(_TAB_ACTION)
        args = action.setup_widget.call_args
        assert args[0][0] is manager
        assert args[0][3] == 300.0   # w
        assert args[0][4] == 500.0 - _RPG_TAB_H  # content_h


# ---------------------------------------------------------------------------
# Slice 5 — bundle passed when RPG service + mem_repo are available
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Slice 8 — _load_player_actors populates the action panel
# ---------------------------------------------------------------------------

def test_load_player_actors_calls_set_actors(tmp_path: Path):
    from unittest.mock import MagicMock
    from dungeon_daddy.rpg.models import ActorState
    view, _, _ = _make_view(tmp_path, with_rpg=True)
    # Seed one pc and one npc into mem_repo
    view._mem_repo.save_actor("a-pc", "camp-1", "pc", "hero", "Elara")
    view._mem_repo.save_actor("a-npc", "camp-1", "npc", "goblin", "Gob")
    action_panel = MagicMock()
    view._rpg_action = action_panel
    view._load_player_actors()
    action_panel.set_actors.assert_called_once()
    actors = action_panel.set_actors.call_args[0][0]
    assert len(actors) == 1
    assert actors[0].actor_id == "a-pc"


def test_load_player_actors_no_op_without_rpg(tmp_path: Path):
    from unittest.mock import MagicMock
    view, _, _ = _make_view(tmp_path, with_rpg=False)
    action_panel = MagicMock()
    view._rpg_action = action_panel
    view._load_player_actors()
    action_panel.set_actors.assert_not_called()


# ---------------------------------------------------------------------------
# Slice 34-6 — dungeon actor types (faction, dungeon_presence) excluded from panel
# ---------------------------------------------------------------------------

def test_load_player_actors_excludes_faction_and_dungeon_presence(tmp_path: Path):
    """After seeding pc + monster + faction + dungeon_presence, only pc reaches panel."""
    from unittest.mock import MagicMock
    view, _, _ = _make_view(tmp_path, with_rpg=True)
    view._mem_repo.save_actor("a-pc",       "camp-1", "pc",               "hero",    "Elara")
    view._mem_repo.save_actor("a-monster",  "camp-1", "monster",          "warden",  "Bone Warden")
    view._mem_repo.save_actor("a-faction",  "camp-1", "faction",          "cult",    "The Cult")
    view._mem_repo.save_actor("a-presence", "camp-1", "dungeon_presence", "spirit",  "The Spirit")
    action_panel = MagicMock()
    view._rpg_action = action_panel
    view._load_player_actors()
    action_panel.set_actors.assert_called_once()
    actors = action_panel.set_actors.call_args[0][0]
    assert len(actors) == 1
    assert actors[0].actor_id == "a-pc"


# ---------------------------------------------------------------------------
# Slice 9 — _on_resolve_action calls service and stores result
# ---------------------------------------------------------------------------

def test_on_resolve_action_calls_service_and_stores_result(tmp_path: Path):
    from unittest.mock import MagicMock
    from dungeon_daddy.rpg.models import ActionResolution
    view, _, _ = _make_view(tmp_path, with_rpg=True)
    resolution = ActionResolution(
        resolution_id="r1", campaign_id="camp-1", actor_id="a1",
        action_key="fight", dice_rolled=[4, 5, 6], outcome="full", stress_cost=0,
    )
    from unittest.mock import MagicMock as _MM
    view._rpg_service.resolve_action.return_value = (resolution, _MM())
    action_panel = MagicMock()
    action_panel._format_result.return_value = {"outcome": "full", "dice": [4, 5, 6], "stress_cost": 0, "notes": None}
    view._rpg_action = action_panel
    view._on_resolve_action(
        campaign_id="camp-1",
        actor_id="a1",
        intent="Attack the goblin",
        action_key="fight",
        push_yourself=False,
        momentum_spend=0,
        dice_pool=2,
    )
    view._rpg_service.resolve_action.assert_called_once()
    action_panel.store_result.assert_called_once_with(
        {"outcome": "full", "dice": [4, 5, 6], "stress_cost": 0, "notes": None}
    )


def test_on_resolve_action_spawns_dm_narration(tmp_path: Path):
    from unittest.mock import MagicMock, patch
    from dungeon_daddy.rpg.models import ActionResolution
    view, room, level = _make_view(tmp_path, with_rpg=True)
    resolution = ActionResolution(
        resolution_id="r2", campaign_id="camp-1", actor_id="a1",
        action_key="sense", dice_rolled=[6], outcome="full", stress_cost=0,
    )
    view._rpg_service.resolve_action.return_value = (resolution, MagicMock())
    action_panel = MagicMock()
    action_panel._format_result.return_value = {"outcome": "full", "dice": [6], "stress_cost": 0, "notes": None}
    view._rpg_action = action_panel
    with patch.object(view, "_spawn_dm_thread") as mock_spawn:
        view._on_resolve_action(
            campaign_id="camp-1", actor_id="a1", intent="search for traps",
            action_key="sense", push_yourself=False, momentum_spend=0, dice_pool=1,
        )
    mock_spawn.assert_called_once_with(room, level)
    assert any("SENSE" in m.content for m in view._dm_history)


def test_on_resolve_action_dm_message_includes_actor_name(tmp_path: Path):
    from unittest.mock import MagicMock, patch
    from dungeon_daddy.rpg.models import ActionResolution, ActorState
    view, room, level = _make_view(tmp_path, with_rpg=True)
    resolution = ActionResolution(
        resolution_id="r5", campaign_id="camp-1", actor_id="a-talvas",
        action_key="sense", dice_rolled=[6], outcome="full", stress_cost=0,
    )
    view._rpg_service.resolve_action.return_value = (resolution, MagicMock())
    action_panel = MagicMock()
    action_panel._format_result.return_value = {"outcome": "full", "dice": [6], "stress_cost": 0, "notes": None}
    action_panel._actors = [
        ActorState(actor_id="a-talvas", campaign_id="camp-1", actor_type="pc",
                   slug="talvas", display_name="Talvas the Wanderer"),
    ]
    view._rpg_action = action_panel
    with patch.object(view, "_spawn_dm_thread"):
        view._on_resolve_action(
            campaign_id="camp-1", actor_id="a-talvas", intent="look for threats",
            action_key="sense", push_yourself=False, momentum_spend=0, dice_pool=1,
        )
    assert any("Talvas the Wanderer" in m.content for m in view._dm_history)


def test_on_resolve_action_no_room_adds_system_message(tmp_path: Path):
    from unittest.mock import MagicMock
    from dungeon_daddy.rpg.models import ActionResolution
    view, _, _ = _make_view(tmp_path, with_rpg=True)
    view._state.current_room_id = None  # no room selected
    resolution = ActionResolution(
        resolution_id="r3", campaign_id="camp-1", actor_id="a1",
        action_key="fight", dice_rolled=[3], outcome="partial", stress_cost=0,
    )
    view._rpg_service.resolve_action.return_value = (resolution, MagicMock())
    action_panel = MagicMock()
    action_panel._format_result.return_value = {"outcome": "partial", "dice": [3], "stress_cost": 0, "notes": None}
    view._rpg_action = action_panel
    view._on_resolve_action(
        campaign_id="camp-1", actor_id="a1", intent="",
        action_key="fight", push_yourself=False, momentum_spend=0, dice_pool=1,
    )
    view._chat.add_message.assert_called_with("system", "Select a room to get DM narration.")


def test_on_resolve_action_no_op_without_service(tmp_path: Path):
    from unittest.mock import MagicMock
    view, _, _ = _make_view(tmp_path, with_rpg=False)
    action_panel = MagicMock()
    view._rpg_action = action_panel
    view._on_resolve_action(
        campaign_id="camp-1", actor_id="a1", intent="attack",
        action_key="fight", push_yourself=False, momentum_spend=0, dice_pool=1,
    )
    action_panel.store_result.assert_not_called()


# ---------------------------------------------------------------------------
# Slice 5 — bundle passed when RPG service + mem_repo are available (existing)
# ---------------------------------------------------------------------------

def test_dm_agent_receives_context_bundle_when_rpg_available(tmp_path: Path):
    view, room, level = _make_view(tmp_path, with_rpg=True)
    view._spawn_dm_thread(room, level)
    assert view._active_thread is not None
    view._active_thread.join(timeout=5.0)

    call_kwargs = view._dm_agent.respond.call_args.kwargs
    assert "context_bundle" in call_kwargs
    assert call_kwargs["context_bundle"] is not None


# ---------------------------------------------------------------------------
# Slice 6 — context_bundle=None when no RPG service
# ---------------------------------------------------------------------------

def test_dm_agent_receives_no_bundle_when_rpg_unavailable(tmp_path: Path):
    view, room, level = _make_view(tmp_path, with_rpg=False)
    view._spawn_dm_thread(room, level)
    assert view._active_thread is not None
    view._active_thread.join(timeout=5.0)

    call_kwargs = view._dm_agent.respond.call_args.kwargs
    assert call_kwargs.get("context_bundle") is None


# ---------------------------------------------------------------------------
# _load_memory_entries — populates the MEM panel from mem_repo
# ---------------------------------------------------------------------------

def test_load_memory_entries_populates_panel(tmp_path: Path):
    from unittest.mock import MagicMock
    view, _, _ = _make_view(tmp_path, with_rpg=True)
    view._rpg_campaign_id = "camp-1"
    view._mem_repo.save_memory_entry(
        memory_id="m1", campaign_id="camp-1", entry_type="event",
        title="The Factory is Waking Up", summary="Something stirs.",
    )
    memory_panel = MagicMock()
    view._rpg_memory = memory_panel
    view._load_memory_entries()
    memory_panel.set_entries.assert_called_once()
    entries = memory_panel.set_entries.call_args[0][0]
    assert any(e.title == "The Factory is Waking Up" for e in entries)


def test_load_memory_entries_includes_tags(tmp_path: Path):
    from unittest.mock import MagicMock
    view, _, _ = _make_view(tmp_path, with_rpg=True)
    view._rpg_campaign_id = "camp-1"
    view._mem_repo.save_memory_entry(
        memory_id="m2", campaign_id="camp-1", entry_type="npc",
        title="Golem A-7", summary="Watching.",
    )
    view._mem_repo.add_memory_tag("m2", "golem")
    view._mem_repo.add_memory_tag("m2", "factory")
    memory_panel = MagicMock()
    view._rpg_memory = memory_panel
    view._load_memory_entries()
    entries = memory_panel.set_entries.call_args[0][0]
    golem_entry = next(e for e in entries if e.memory_id == "m2")
    assert "golem" in golem_entry.tags
    assert "factory" in golem_entry.tags


def test_load_memory_entries_no_op_without_mem_repo(tmp_path: Path):
    from unittest.mock import MagicMock
    view, _, _ = _make_view(tmp_path, with_rpg=False)
    memory_panel = MagicMock()
    view._rpg_memory = memory_panel
    view._load_memory_entries()
    memory_panel.set_entries.assert_not_called()


# ---------------------------------------------------------------------------
# Phase 35.6 — _apply_world_reaction uses correct track capacity
# ---------------------------------------------------------------------------

def test_apply_world_reaction_persists_weird_track_with_correct_capacity(tmp_path: Path):
    """A ReactionStressLine(track_key='weird') must be saved with weird capacity, not body."""
    from unittest.mock import MagicMock
    from dungeon_daddy.rpg.models import (
        ActionResolution, ActorState, ReactionStressLine, WorldReaction,
    )
    view, _, _ = _make_view(tmp_path, with_rpg=True)

    # Seed actor with body cap=4 and weird cap=6
    actor_id = "a-pc"
    view._mem_repo.save_actor(actor_id, "camp-1", "pc", "hero", "Elara")
    view._mem_repo.save_actor_stress_track(actor_id, "body",  capacity=4, filled=0)
    view._mem_repo.save_actor_stress_track(actor_id, "weird", capacity=6, filled=1)
    view._rpg_campaign_id = "camp-1"

    actor = ActorState(
        actor_id=actor_id, campaign_id="camp-1", actor_type="pc",
        slug="hero", display_name="Elara",
    )
    action_panel = MagicMock()
    action_panel._actors = [actor]
    view._rpg_action = action_panel

    resolution = ActionResolution(
        resolution_id="r1", campaign_id="camp-1", actor_id=actor_id,
        action_key="channel", dice_rolled=[2], outcome="miss",
    )

    # Stub service to return a WorldReaction with weird stress
    stress_line = ReactionStressLine(
        actor_id=actor_id, display_name="Elara",
        track_key="weird", amount=2, new_filled=3,
        triggered_fallout=False, reason="miss consequence — weird",
    )
    fake_reaction = WorldReaction(
        reaction_id="rx1", campaign_id="camp-1",
        source_resolution_id="r1", outcome="miss",
        stress_lines=[stress_line],
    )
    view._rpg_service.react_to_resolution.return_value = (fake_reaction, MagicMock())

    view._apply_world_reaction(resolution)

    tracks_after = {t["track_key"]: t for t in view._mem_repo.get_actor_stress_tracks(actor_id)}
    assert "weird" in tracks_after, "weird track should be persisted"
    assert tracks_after["weird"]["filled"] == 3
    assert tracks_after["weird"]["capacity"] == 6, "must use weird capacity, not body capacity"
