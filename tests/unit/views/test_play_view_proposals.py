"""Tests for Phase 36 Slice 9 — proposal pipeline wired into _on_resolve_action."""
from __future__ import annotations

import queue
from pathlib import Path
from unittest.mock import MagicMock, patch

from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level, Room, SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import ActionResolution, ActorState

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


# ---------------------------------------------------------------------------
# Shared helpers
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


class _MockProvider:
    def __init__(self, response: str):
        self._response = response

    def complete(self, messages, system="", max_tokens=512):
        return self._response

    @property
    def model_id(self):
        return "mock"


def _make_view(tmp_path: Path):
    """Build a PlayView via __new__ with real mem_repo and mock rpg_service."""
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
    view._mem_repo = mem_repo
    view._rpg_service = MagicMock()
    view._rpg_campaign_id = "camp-1"
    return view


def _resolution() -> ActionResolution:
    return ActionResolution(
        resolution_id="r1",
        campaign_id="camp-1",
        actor_id="a-pc",
        action_key="skirmish",
        dice_rolled=[4, 5, 6],
        outcome="full",
        stress_cost=0,
        intent="disarm the guard",
    )


def _setup_action_panel(view, resolution: ActionResolution) -> MagicMock:
    actor = ActorState(
        actor_id="a-pc", campaign_id="camp-1",
        actor_type="pc", slug="hero", display_name="Elara",
    )
    panel = MagicMock()
    panel._actors = [actor]
    panel._format_result.return_value = {
        "outcome": "full", "dice": [4, 5, 6], "stress_cost": 0, "notes": None,
    }
    view._rpg_action = panel
    view._rpg_service.resolve_action.return_value = (resolution, MagicMock())
    return panel


# ---------------------------------------------------------------------------
# Behavior: _on_resolve_action sets _rpg_debug._last_validation after a
# valid proposal from the DM agent
# ---------------------------------------------------------------------------

def test_on_resolve_action_sets_proposal_result_after_valid_proposal(tmp_path: Path):
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.ui.panels.debug_controls import DebugControls

    view = _make_view(tmp_path)
    resolution = _resolution()
    _setup_action_panel(view, resolution)

    raw_json = '{"narration_hint": "Guards react.", "proposed_changes": []}'
    view._dm_agent = DungeonMasterAgent(provider=_MockProvider(raw_json))
    view._rpg_debug = DebugControls(view._rpg_service)

    with patch.object(view, "_apply_world_reaction"):
        view._on_resolve_action(
            campaign_id="camp-1", actor_id="a-pc", intent="disarm the guard",
            action_key="skirmish", push_yourself=False, momentum_spend=0, dice_pool=2,
        )

    assert view._rpg_debug._last_validation is not None


# ---------------------------------------------------------------------------
# Behavior: _on_resolve_action sets _rpg_debug._last_validation even when
# the LLM returns malformed JSON (parse_proposal returns None)
# ---------------------------------------------------------------------------

def test_on_resolve_action_sets_proposal_result_when_parse_fails(tmp_path: Path):
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.ui.panels.debug_controls import DebugControls

    view = _make_view(tmp_path)
    resolution = _resolution()
    _setup_action_panel(view, resolution)

    view._dm_agent = DungeonMasterAgent(provider=_MockProvider("not valid json {{{"))
    view._rpg_debug = DebugControls(view._rpg_service)

    with patch.object(view, "_apply_world_reaction"):
        view._on_resolve_action(
            campaign_id="camp-1", actor_id="a-pc", intent="disarm the guard",
            action_key="skirmish", push_yourself=False, momentum_spend=0, dice_pool=2,
        )

    assert view._rpg_debug._last_validation is not None
