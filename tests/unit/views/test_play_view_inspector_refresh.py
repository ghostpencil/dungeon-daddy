"""Phase 38.5 — Right panel inspector refresh after chat-side action."""
from __future__ import annotations

import queue
from pathlib import Path
from unittest.mock import MagicMock

from dungeon_daddy.data.models import Level, Room
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import ActorState, FalloutRecord
from dungeon_daddy.rpg.service import RpgService

_MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy" / "data" / "migrations"
)
from dungeon_daddy.ui.panels.character_sheet_panel import CharacterSheetPanel
from dungeon_daddy.ui.panels.fallout_panel import FalloutPanel
from dungeon_daddy.ui.panels.player_action_panel import PlayerActionPanel
from dungeon_daddy.ui.player_action_state import PlayerActionState
from dungeon_daddy.views.play_view import PlayView
from tests.unit.views._factories import _dungeon, _state


def _room_obj(room_id: str = "r1") -> Room:
    return Room(id=room_id, num=1, name="Hall", x=0, y=0, w=2, h=2, type="hall", note="")


def _level_with_room(room_id: str = "r1") -> Level:
    return Level(
        id=1, name="L1", summary="", ecology="", loop="",
        loops=[], width=10, height=10, entries=[],
        rooms=[_room_obj(room_id)], connections=[],
    )


def _make_view(
    action_key: str | None = None,
    actor_id: str = "a1",
    room_id: str | None = "r1",
    has_rpg_service: bool = True,
) -> PlayView:
    view = PlayView.__new__(PlayView)

    action_state = PlayerActionState()
    action_state.set_actor_roster(["a1"])
    action_state.actor_id = actor_id
    if action_key is not None:
        action_state.select_action(action_key)
    view._action_state = action_state

    view._chat = MagicMock()
    view._rpg_service = RpgService() if has_rpg_service else None

    panel = PlayerActionPanel()
    panel.set_actors([
        ActorState(
            actor_id="a1", campaign_id="c1", actor_type="pc",
            slug="mara", display_name="Mara",
            actions={"study": 2, "fight": 1},
        )
    ])
    view._rpg_action = panel
    view._session.set_actors(panel._actors)
    view._rpg_campaign_id = "c1"
    view._rpg_debug = None
    view._dm_agent = None
    view._mem_repo = None

    view._rpg_char = CharacterSheetPanel()
    view._rpg_fallout = FalloutPanel()

    view._result_queue = queue.Queue()
    view._llm_busy = False
    view._active_thread = None
    view._dm_history = []

    level = _level_with_room("r1")
    view._dungeon = _dungeon([level])
    view._state = _state(room_id=room_id)

    return view


# ---------------------------------------------------------------------------
# Slice 1 — Char panel populated after chat-side action
# ---------------------------------------------------------------------------

class TestCharPanelPopulatedAfterChatAction:
    def test_char_panel_actor_is_none_before_action(self):
        """CharacterSheetPanel starts with no actor."""
        view = _make_view(action_key="study", room_id="r1")
        assert view._rpg_char._actor is None

    def test_char_panel_actor_set_after_chat_action(self):
        """After a chat-side action resolves, _rpg_char._actor is populated."""
        view = _make_view(action_key="study", room_id="r1")
        view._on_chat_send("I study the mural")
        assert view._rpg_char._actor is not None

    def test_char_panel_shows_actor_who_acted(self):
        """_rpg_char._actor.actor_id matches the actor who took the action."""
        view = _make_view(action_key="study", actor_id="a1", room_id="r1")
        view._on_chat_send("I study the mural")
        assert view._rpg_char._actor is not None
        assert view._rpg_char._actor.actor_id == "a1"


# ---------------------------------------------------------------------------
# Slice 3 — Fallout panel populated from mem_repo after chat-side action
# ---------------------------------------------------------------------------

class TestFalloutPanelPopulatedAfterChatAction:
    def test_fallout_entries_loaded_when_repo_has_record(self, tmp_path: Path):
        """_rpg_fallout._entries contains the actor's fallout record after action."""
        mem_repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        mem_repo.initialize_schema(_MIGRATIONS_DIR)
        mem_repo.save_fallout_record(FalloutRecord(
            fallout_id="f1",
            campaign_id="c1",
            actor_id="a1",
            track_key="body",
            severity="minor",
            title="Sprained Wrist",
            summary="Twisted it badly.",
            status="active",
        ))

        view = _make_view(action_key="study", room_id="r1")
        view._mem_repo = mem_repo

        view._on_chat_send("I study the mural")

        assert len(view._rpg_fallout._entries) == 1
        assert view._rpg_fallout._entries[0].fallout_id == "f1"


# ---------------------------------------------------------------------------
# Slice 4 — Right-panel action path also refreshes CHAR tab (regression)
# ---------------------------------------------------------------------------

class TestCharPanelPopulatedAfterRightPanelAction:
    def test_char_panel_set_after_on_resolve_action(self):
        """_rpg_char._actor is set after _on_resolve_action (right-panel path)."""
        view = _make_view(room_id="r1")
        assert view._rpg_char._actor is None
        view._on_resolve_action(
            campaign_id="c1",
            actor_id="a1",
            intent="I study the mural",
            action_key="study",
            push_yourself=False,
            momentum_spend=0,
            dice_pool=2,
        )
        assert view._rpg_char._actor is not None
        assert view._rpg_char._actor.actor_id == "a1"
