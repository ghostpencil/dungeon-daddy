"""Phase 38.4 — Chat-side RPG action: send with chip → ActionRequest → resolution pipeline."""
from __future__ import annotations

import queue
from unittest.mock import MagicMock

from dungeon_daddy.data.models import Level, Room
from dungeon_daddy.rpg.models import ActorState
from dungeon_daddy.rpg.service import RpgService
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

    # Chat-side action state
    action_state = PlayerActionState()
    action_state.set_actor_roster(["a1"])
    action_state.actor_id = actor_id
    if action_key is not None:
        action_state.select_action(action_key)
    view._action_state = action_state

    # Chat panel (mocked — requires Arcade)
    view._chat = MagicMock()

    # RPG service (real)
    view._rpg_service = RpgService() if has_rpg_service else None

    # Actor panel (real)
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

    # DM thread infrastructure
    view._result_queue = queue.Queue()
    view._llm_busy = False
    view._active_thread = None
    view._dm_history = []

    # Dungeon and session state (dungeon always present; room may be absent)
    level = _level_with_room("r1")
    view._dungeon = _dungeon([level])
    view._state = _state(room_id=room_id)

    return view


# ---------------------------------------------------------------------------
# Slice 1 — Tracer bullet: action chip resolved → system bubble added
# ---------------------------------------------------------------------------

class TestChatSendWithActionKeyResolvesAction:
    def test_system_bubble_added_after_resolution(self):
        """Sending chat with action chip set adds a system bubble mentioning the action."""
        view = _make_view(action_key="study", room_id="r1")
        view._on_chat_send("I study the mural")
        msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
        assert any(role == "system" and "STUDY" in text for role, text in msgs)


# ---------------------------------------------------------------------------
# Slice 2 — No action key → plain narration path (no resolution)
# ---------------------------------------------------------------------------

class TestChatSendNoActionKey:
    def test_no_resolution_when_no_chip_selected(self):
        """Plain chat (no chip) does not trigger action resolution."""
        view = _make_view(action_key=None, room_id="r1")
        captured: list = []

        def _spy(resolution):
            captured.append(resolution)

        # The action logic lives on the orchestrator (Phase 51.7 Slice 4) —
        # spy at that seam; the view method is now a thin delegator.
        view._actions.apply_world_reaction = _spy  # type: ignore[method-assign]
        view._on_chat_send("I look around the room")
        assert len(captured) == 0


# ---------------------------------------------------------------------------
# Slice 3 — Chat text becomes ActionRequest.intent
# ---------------------------------------------------------------------------

class TestChatTextBecomesIntent:
    def test_chat_text_passes_as_intent_to_resolution(self):
        """Chat text becomes the intent field in ActionResolution."""
        view = _make_view(action_key="study", room_id="r1")
        captured: list = []

        def _spy(resolution):
            captured.append(resolution)

        view._actions.apply_world_reaction = _spy  # type: ignore[method-assign]
        view._on_chat_send("I study the mural to resist its pull.")
        assert len(captured) == 1
        assert captured[0].intent == "I study the mural to resist its pull."


# ---------------------------------------------------------------------------
# Slice 4 — Actor id from action state used in resolution
# ---------------------------------------------------------------------------

class TestActorIdFromActionState:
    def test_resolution_uses_actor_id_from_action_state(self):
        """Resolution uses the actor_id set in PlayerActionState."""
        view = _make_view(action_key="fight", actor_id="a1", room_id="r1")
        captured: list = []

        def _spy(resolution):
            captured.append(resolution)

        view._actions.apply_world_reaction = _spy  # type: ignore[method-assign]
        view._on_chat_send("I attack the warden.")
        assert len(captured) == 1
        assert captured[0].actor_id == "a1"


# ---------------------------------------------------------------------------
# Slice 5 — Mechanical result bubble format
# ---------------------------------------------------------------------------

class TestMechanicalResultBubble:
    def test_result_bubble_contains_actor_name_and_action_key(self):
        """Mechanical bubble mentions actor display name and action key."""
        view = _make_view(action_key="study", room_id="r1")
        view._on_chat_send("I study the mural.")
        msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
        system_msgs = [text for role, text in msgs if role == "system"]
        assert any("Mara" in t and "STUDY" in t for t in system_msgs)

    def test_bubble_uses_human_readable_outcome_tier(self):
        """Mechanical bubble shows 'Partial Success' etc., not the raw 'partial' key."""
        view = _make_view(action_key="study", room_id="r1")
        view._on_chat_send("I study the mural.")
        msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
        system_msgs = [text for role, text in msgs if role == "system"]
        assert any(
            any(tier in t for tier in ("Partial Success", "Full Success", "Critical Success", "Miss"))
            for t in system_msgs
        )

    def test_bubble_includes_best_die_in_brackets(self):
        """Mechanical bubble includes best die value in square brackets."""
        view = _make_view(action_key="study", room_id="r1")
        view._on_chat_send("I study the mural.")
        msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
        system_msgs = [text for role, text in msgs if role == "system"]
        import re
        assert any(re.search(r"\[\d+\]", t) for t in system_msgs)


# ---------------------------------------------------------------------------
# Slice 6 — Action state reset after resolution
# ---------------------------------------------------------------------------

class TestActionStateResetAfterResolution:
    def test_action_key_cleared_after_resolution(self):
        """action_key is None after resolution completes."""
        view = _make_view(action_key="study", room_id="r1")
        view._on_chat_send("I study the mural.")
        assert view._action_state.action_key is None

    def test_intent_cleared_after_resolution(self):
        """intent is empty string after resolution completes."""
        view = _make_view(action_key="study", room_id="r1")
        view._action_state.set_intent("pending text")
        view._on_chat_send("I study the mural.")
        assert view._action_state.intent == ""


# ---------------------------------------------------------------------------
# Slice 7 — No room selected with chip → system message, no resolution
# ---------------------------------------------------------------------------

class TestNoRoomWithChip:
    def test_system_message_when_no_room_selected(self):
        """System message appears when chip is set but no room is selected."""
        view = _make_view(action_key="study", room_id=None)
        captured: list = []

        def _spy(resolution):
            captured.append(resolution)

        view._actions.apply_world_reaction = _spy  # type: ignore[method-assign]
        view._on_chat_send("I study the mural.")
        assert len(captured) == 0
        msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
        assert any(role == "system" for role, _ in msgs)


# ---------------------------------------------------------------------------
# Slice 8 — No RPG service with chip → graceful fallback
# ---------------------------------------------------------------------------

class TestNoRpgServiceWithChip:
    def test_graceful_when_rpg_service_absent(self):
        """No crash when RPG service is absent; player message still added."""
        view = _make_view(action_key="study", has_rpg_service=False, room_id="r1")
        view._on_chat_send("I study the mural.")  # must not raise
        msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
        assert len(msgs) >= 1  # at minimum the "gm" message was added
