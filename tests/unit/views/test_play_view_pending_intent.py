"""Phase 39.3 — Framing UI in chat.

When the player sends plain text (no action chip selected) and the
deterministic classifier finds action suggestions, PlayView should:
  - create a PendingIntent on PlayerActionState
  - add a framing system message to chat
  - NOT call RpgService.resolve_action
  - NOT spawn a DM narration thread

When classifier finds no suggestions, the existing plain narration path runs.
"""
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


def _room() -> Room:
    return Room(id="r1", num=1, name="Hall", x=0, y=0, w=2, h=2, type="hall", note="")


def _level() -> Level:
    return Level(
        id=1, name="L1", summary="", ecology="", loop="",
        loops=[], width=10, height=10, entries=[],
        rooms=[_room()], connections=[],
    )


def _make_view(*, room_id: str | None = "r1") -> PlayView:
    view = PlayView.__new__(PlayView)

    action_state = PlayerActionState()
    action_state.set_actor_roster(["a1"])
    action_state.actor_id = "a1"
    # No action chip selected by default
    view._action_state = action_state

    view._chat = MagicMock()
    view._rpg_service = RpgService()

    panel = PlayerActionPanel()
    panel.set_actors([
        ActorState(
            actor_id="a1", campaign_id="c1", actor_type="pc",
            slug="mara", display_name="Mara",
            actions={"study": 2},
        )
    ])
    view._rpg_action = panel
    view._rpg_campaign_id = "c1"
    view._rpg_debug = None
    view._dm_agent = None
    view._mem_repo = None

    view._result_queue = queue.Queue()
    view._llm_busy = False
    view._active_thread = None
    view._dm_history = []

    view._dungeon = _dungeon([_level()])
    view._state = _state(room_id=room_id)
    return view


# ---------------------------------------------------------------------------
# Slice 1 — Tracer: actionable text → framing message, no resolve
# ---------------------------------------------------------------------------

class TestActionableTextCreatesPendingIntent:
    def test_framing_system_message_added_to_chat(self):
        """Actionable text without a chip shows a framing message, not DM narration."""
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
        system_msgs = [text for role, text in msgs if role == "system"]
        assert any("STUDY" in t or "study" in t.lower() for t in system_msgs)

    def test_resolve_action_not_called(self):
        """RPG service is not called when pending intent framing is shown."""
        view = _make_view()
        captured: list = []
        view._apply_world_reaction = lambda r: captured.append(r)  # type: ignore[method-assign]
        view._on_chat_send("I study the mural to understand its secrets")
        assert captured == []

    def test_dm_thread_not_spawned(self):
        """DM narration thread is not spawned during framing."""
        view = _make_view()
        spawned: list = []
        view._spawn_dm_thread = lambda room, level: spawned.append((room, level))  # type: ignore[method-assign]
        view._on_chat_send("I study the mural to understand its secrets")
        assert spawned == []


# ---------------------------------------------------------------------------
# Slice 2 — PendingIntent stored on action_state
# ---------------------------------------------------------------------------

class TestPendingIntentStoredOnActionState:
    def test_pending_intent_created_with_correct_raw_text(self):
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        pi = view._action_state.pending_intent
        assert pi is not None
        assert pi.raw_text == "I study the mural to understand its secrets"

    def test_pending_intent_actor_id_matches_action_state(self):
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        pi = view._action_state.pending_intent
        assert pi is not None
        assert pi.actor_id == "a1"

    def test_pending_intent_suggested_primary_action_is_study(self):
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        pi = view._action_state.pending_intent
        assert pi is not None
        assert pi.suggested_primary_action == "study"

    def test_pending_intent_status_is_awaiting_confirmation(self):
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        pi = view._action_state.pending_intent
        assert pi is not None
        assert pi.status == "awaiting_confirmation"

    def test_action_state_awaiting_confirmation_set_true(self):
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        assert view._action_state.awaiting_confirmation is True


# ---------------------------------------------------------------------------
# Slice 3 — Non-actionable text → plain narration path
# ---------------------------------------------------------------------------

class TestNonActionableTextUsesPlainNarration:
    def test_no_pending_intent_for_unclassifiable_text(self):
        """Text with no classifier matches creates no pending intent."""
        view = _make_view()
        view._spawn_dm_thread = MagicMock()  # type: ignore[method-assign]
        view._on_chat_send("I wander aimlessly and think about nothing")
        assert view._action_state.pending_intent is None

    def test_dm_thread_spawned_for_unclassifiable_text(self):
        """Text with no classifier matches routes to DM narration."""
        view = _make_view()
        view._spawn_dm_thread = MagicMock()  # type: ignore[method-assign]
        view._on_chat_send("I wander aimlessly and think about nothing")
        view._spawn_dm_thread.assert_called_once()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Slice 4 — reset() clears pending intent
# ---------------------------------------------------------------------------

class TestResetClearsPendingIntent:
    def test_reset_clears_pending_intent(self):
        view = _make_view()
        view._on_chat_send("I study the mural")
        assert view._action_state.pending_intent is not None
        view._action_state.reset()
        assert view._action_state.pending_intent is None

    def test_reset_clears_awaiting_confirmation(self):
        view = _make_view()
        view._on_chat_send("I study the mural")
        assert view._action_state.awaiting_confirmation is True
        view._action_state.reset()
        assert view._action_state.awaiting_confirmation is False


# ---------------------------------------------------------------------------
# Slice 5 — Confirmation path: chip click resolves via _run_chat_action
# ---------------------------------------------------------------------------

def _pending_view() -> PlayView:
    """View pre-loaded with a pending intent and a chip already selected."""
    view = _make_view()
    view._on_chat_send("I study the mural to understand its secrets")
    # Simulate player selecting the suggested chip
    view._action_state.select_action("study")
    return view


class TestConfirmationPathRoutes:
    def test_run_chat_action_called_on_chip_confirm(self):
        """When awaiting_confirmation and chip is selected, _run_chat_action fires."""
        view = _pending_view()
        calls: list = []
        view._run_chat_action = lambda *a, **kw: calls.append((a, kw))  # type: ignore[method-assign]
        view._on_chat_send("")
        assert calls, "_run_chat_action should have been called"

    def test_pending_intent_raw_text_used_as_intent(self):
        """Confirmed chip uses original pending intent text, not the newly typed text."""
        view = _pending_view()
        calls: list = []
        view._run_chat_action = lambda *a, **kw: calls.append((a, kw))  # type: ignore[method-assign]
        view._on_chat_send("some other unrelated text")
        assert calls
        # _run_chat_action(campaign_id, actor_id, action_key, intent)
        intent_arg = calls[0][0][3]
        assert intent_arg == "I study the mural to understand its secrets"

    def test_newly_typed_text_not_used_as_intent_when_awaiting(self):
        """The text sent alongside the chip is ignored when pending intent exists."""
        view = _pending_view()
        calls: list = []
        view._run_chat_action = lambda *a, **kw: calls.append((a, kw))  # type: ignore[method-assign]
        view._on_chat_send("some other unrelated text")
        intent_arg = calls[0][0][3]
        assert intent_arg != "some other unrelated text"


# ---------------------------------------------------------------------------
# Slice 6 — State is cleared after confirmation
# ---------------------------------------------------------------------------

class TestConfirmationClearsState:
    def test_pending_intent_cleared_after_confirm(self):
        view = _pending_view()
        view._run_chat_action = lambda *a, **kw: None  # type: ignore[method-assign]
        view._on_chat_send("")
        assert view._action_state.pending_intent is None

    def test_awaiting_confirmation_false_after_confirm(self):
        view = _pending_view()
        view._run_chat_action = lambda *a, **kw: None  # type: ignore[method-assign]
        view._on_chat_send("")
        assert view._action_state.awaiting_confirmation is False

    def test_action_key_cleared_after_confirm(self):
        view = _pending_view()
        view._run_chat_action = lambda *a, **kw: None  # type: ignore[method-assign]
        view._on_chat_send("")
        assert view._action_state.action_key is None


# ---------------------------------------------------------------------------
# Slice 7 — No-roll path: awaiting_confirmation + no chip → plain narration
# ---------------------------------------------------------------------------

def _no_roll_view() -> PlayView:
    """View with pending intent but no chip selected (player chose no-roll)."""
    view = _make_view()
    view._on_chat_send("I study the mural to understand its secrets")
    # Do NOT select a chip
    return view


class TestNoRollPath:
    def test_spawn_dm_thread_called_on_no_roll(self):
        """When awaiting_confirmation and no chip, plain narration fires."""
        view = _no_roll_view()
        view._spawn_dm_thread = MagicMock()
        view._on_chat_send("")
        view._spawn_dm_thread.assert_called_once()

    def test_raw_text_used_for_narration(self):
        """No-roll uses the original pending intent text for DM history, not the typed text."""
        view = _no_roll_view()
        view._spawn_dm_thread = MagicMock()
        view._on_chat_send("never mind, no roll")
        contents = [m.content for m in view._dm_history]
        assert "I study the mural to understand its secrets" in contents

    def test_world_reaction_not_called_on_no_roll(self):
        """No-roll does not trigger world reaction."""
        view = _no_roll_view()
        view._spawn_dm_thread = MagicMock()
        captured: list = []
        view._apply_world_reaction = lambda r: captured.append(r)  # type: ignore[method-assign]
        view._on_chat_send("")
        assert captured == []

    def test_pending_intent_cleared_on_no_roll(self):
        """No-roll clears the pending intent from action state."""
        view = _no_roll_view()
        view._spawn_dm_thread = MagicMock()
        view._on_chat_send("")
        assert view._action_state.pending_intent is None

    def test_awaiting_confirmation_false_on_no_roll(self):
        """No-roll resets awaiting_confirmation to False."""
        view = _no_roll_view()
        view._spawn_dm_thread = MagicMock()
        view._on_chat_send("")
        assert view._action_state.awaiting_confirmation is False


# ---------------------------------------------------------------------------
# Slice 8 — Action card set when intent is classified (39.S2 → updated 39.S6.3)
# ---------------------------------------------------------------------------

def _make_view_with_pending() -> tuple[PlayView, object]:
    """Create a view with a pending intent and return (view, chip_click_callback)."""
    view = _make_view()
    view._on_chat_send("I study the mural to understand its secrets")
    callback = view._chat.set_chip_click_callback.call_args[0][0]
    return view, callback


class TestPendingChipsSetOnClassification:
    def test_chip_click_callback_registered(self):
        """set_chip_click_callback is called with a callable."""
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        view._chat.set_chip_click_callback.assert_called_once()
        cb = view._chat.set_chip_click_callback.call_args[0][0]
        assert callable(cb)


# ---------------------------------------------------------------------------
# Slice 9 — Action chip click fires _run_chat_action immediately (39.S2)
# ---------------------------------------------------------------------------

class TestActionChipFiresResolution:
    def test_run_chat_action_called_on_action_chip_click(self):
        """Clicking an action chip calls _run_chat_action without a second send."""
        view, callback = _make_view_with_pending()
        calls: list = []
        view._run_chat_action = lambda *a, **kw: calls.append(a)  # type: ignore[method-assign]
        callback("STUDY")
        assert calls, "_run_chat_action should have been called"

    def test_original_intent_text_used_as_intent_on_chip_click(self):
        """Action chip uses pending intent raw_text as the intent argument."""
        view, callback = _make_view_with_pending()
        calls: list = []
        view._run_chat_action = lambda *a, **kw: calls.append(a)  # type: ignore[method-assign]
        callback("STUDY")
        intent_arg = calls[0][3]
        assert intent_arg == "I study the mural to understand its secrets"

    def test_action_state_cleared_after_chip_click(self):
        """Action state is fully reset after chip click resolution."""
        view, callback = _make_view_with_pending()
        view._run_chat_action = lambda *a, **kw: None  # type: ignore[method-assign]
        callback("STUDY")
        assert view._action_state.pending_intent is None
        assert view._action_state.awaiting_confirmation is False


# ---------------------------------------------------------------------------
# Slice 10 — "No Roll" chip triggers DM narration, no RPG resolve (39.S2)
# ---------------------------------------------------------------------------

class TestNoRollChipFiresNarration:
    def test_spawn_dm_thread_called_on_no_roll_chip(self):
        """Clicking 'No Roll' chip spawns the DM narration thread."""
        view, callback = _make_view_with_pending()
        view._spawn_dm_thread = MagicMock()  # type: ignore[method-assign]
        callback("No Roll")
        view._spawn_dm_thread.assert_called_once()  # type: ignore[attr-defined]

    def test_no_roll_chip_uses_pending_intent_raw_text(self):
        """'No Roll' chip places the original intent text into DM history."""
        view, callback = _make_view_with_pending()
        view._spawn_dm_thread = MagicMock()  # type: ignore[method-assign]
        callback("No Roll")
        contents = [m.content for m in view._dm_history]
        assert "I study the mural to understand its secrets" in contents

    def test_no_roll_chip_does_not_call_run_chat_action(self):
        """'No Roll' chip does not trigger RPG resolution."""
        view, callback = _make_view_with_pending()
        view._spawn_dm_thread = MagicMock()  # type: ignore[method-assign]
        calls: list = []
        view._run_chat_action = lambda *a, **kw: calls.append(a)  # type: ignore[method-assign]
        callback("No Roll")
        assert calls == []

    def test_action_state_cleared_after_no_roll_chip(self):
        """Action state is fully reset after 'No Roll' chip click."""
        view, callback = _make_view_with_pending()
        view._spawn_dm_thread = MagicMock()  # type: ignore[method-assign]
        callback("No Roll")
        assert view._action_state.pending_intent is None
        assert view._action_state.awaiting_confirmation is False


# ---------------------------------------------------------------------------
# Slice 12 — _format_intent_framing updated copy (39.S3)
# ---------------------------------------------------------------------------

class TestIntentFramingCopy:
    def test_framing_no_longer_says_open_rpg_panel(self):
        """The framing message no longer redirects to the RPG panel."""
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
        system_msgs = [text for role, text in msgs if role == "system"]
        assert not any("Open RPG panel" in t for t in system_msgs)

    def test_framing_message_says_click_an_action_below(self):
        """The framing message says 'Click an action below'."""
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
        system_msgs = [text for role, text in msgs if role == "system"]
        assert any("Click an action below" in t for t in system_msgs)


# ---------------------------------------------------------------------------
# Slice 13 — Actor mini card wired to chat panel (39.S4)
# ---------------------------------------------------------------------------

class TestActorMiniCardWiredToChat:
    def test_refresh_chat_mini_card_calls_set_actor_mini_card(self):
        """_refresh_chat_mini_card calls set_actor_mini_card on the chat panel."""
        view = _make_view()
        view._refresh_chat_mini_card()
        view._chat.set_actor_mini_card.assert_called_once()

    def test_mini_card_shows_active_actor_name(self):
        """The mini card contains the active actor's display name."""
        view = _make_view()
        view._refresh_chat_mini_card()
        card = view._chat.set_actor_mini_card.call_args[0][0]
        assert card.actor_name == "Mara"

    def test_mini_card_none_when_no_matching_actor(self):
        """set_actor_mini_card(None) when active actor_id has no match."""
        view = _make_view()
        view._action_state.actor_id = "unknown"
        view._refresh_chat_mini_card()
        view._chat.set_actor_mini_card.assert_called_once_with(None)

    def test_mini_card_none_when_actor_id_is_none(self):
        """set_actor_mini_card(None) when no actor is selected."""
        view = _make_view()
        view._action_state.actor_id = None
        view._refresh_chat_mini_card()
        view._chat.set_actor_mini_card.assert_called_once_with(None)


# ---------------------------------------------------------------------------
# Slice 14 — Actor switcher (39.S6.2)
# ---------------------------------------------------------------------------

def _make_multi_actor_view() -> PlayView:
    """View with two actors in roster for switcher tests."""
    view = _make_view()
    view._action_state.set_actor_roster(["a1", "a2"])
    return view


class TestActorSwitcher:
    def test_on_actor_switch_prev_calls_select_prev_actor(self):
        """_on_actor_switch('prev') calls select_prev_actor and refreshes mini card."""
        view = _make_multi_actor_view()
        view._on_actor_switch("prev")
        assert view._action_state.actor_id == "a2"  # wrapped around

    def test_on_actor_switch_next_calls_select_next_actor(self):
        """_on_actor_switch('next') advances to next actor."""
        view = _make_multi_actor_view()
        view._on_actor_switch("next")
        assert view._action_state.actor_id == "a2"

    def test_on_actor_switch_updates_mini_card(self):
        """_on_actor_switch triggers _refresh_chat_mini_card."""
        view = _make_multi_actor_view()
        view._on_actor_switch("next")
        view._chat.set_actor_mini_card.assert_called()

    def test_on_actor_switch_refreshes_action_builder(self):
        """Switching the acting actor re-populates the in-chat Action Builder."""
        view = _make_multi_actor_view()
        view._refresh_vna_panel = MagicMock()
        view._on_actor_switch("next")
        view._refresh_vna_panel.assert_called_once()

    def test_on_actor_switch_awaiting_confirmation_skips_builder_refresh(self):
        """A no-op switch (awaiting confirmation) must not refresh the builder."""
        view = _make_multi_actor_view()
        view._action_state.set_awaiting_confirmation(True)
        view._refresh_vna_panel = MagicMock()
        view._on_actor_switch("next")
        view._refresh_vna_panel.assert_not_called()

    def test_on_actor_switch_disabled_when_awaiting_confirmation(self):
        """_on_actor_switch is a no-op when awaiting_confirmation=True."""
        view = _make_multi_actor_view()
        view._action_state.set_awaiting_confirmation(True)
        original_id = view._action_state.actor_id
        view._chat.reset_mock()
        view._on_actor_switch("next")
        assert view._action_state.actor_id == original_id
        view._chat.set_actor_mini_card.assert_not_called()

    def test_refresh_chat_mini_card_calls_set_has_multiple_actors(self):
        """_refresh_chat_mini_card propagates has_multiple_actors to chat panel."""
        view = _make_multi_actor_view()
        view._refresh_chat_mini_card()
        view._chat.set_has_multiple_actors.assert_called_once_with(True)

    def test_refresh_chat_mini_card_set_has_multiple_false_for_single_actor(self):
        """_refresh_chat_mini_card passes False when only one actor exists."""
        view = _make_view()  # single actor roster
        view._refresh_chat_mini_card()
        view._chat.set_has_multiple_actors.assert_called_once_with(False)


# ---------------------------------------------------------------------------
# Slice 15 — In-chat action card (39.S6.3 + 39.S6.4)
# ---------------------------------------------------------------------------

class TestInChatActionCard:
    def test_add_action_card_called_when_intent_classified(self):
        """add_action_card is called (not set_pending_chips) when pending intent is created."""
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        view._chat.add_action_card.assert_called_once()

    def test_action_card_receives_actor_name(self):
        """add_action_card receives the actor's display name."""
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        args = view._chat.add_action_card.call_args[0]
        assert args[0] == "Mara"

    def test_action_card_receives_intent_text(self):
        """add_action_card receives the raw intent text."""
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        args = view._chat.add_action_card.call_args[0]
        assert "study" in args[1].lower()

    def test_action_card_includes_no_roll(self):
        """add_action_card action_keys list includes 'No Roll'."""
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        args = view._chat.add_action_card.call_args[0]
        assert "No Roll" in args[2]

    def test_set_pending_chips_not_called_on_classification(self):
        """set_pending_chips is NOT called when pending intent is created (S6.4)."""
        view = _make_view()
        view._on_chat_send("I study the mural to understand its secrets")
        view._chat.set_pending_chips.assert_not_called()

    def test_resolve_active_card_called_on_action_chip_click(self):
        """resolve_active_card is called with chosen label after chip click."""
        view, callback = _make_view_with_pending()
        view._run_chat_action = lambda *a, **kw: None  # type: ignore[method-assign]
        view._chat.reset_mock()
        callback("STUDY")
        view._chat.resolve_active_card.assert_called_once_with("STUDY")

    def test_resolve_active_card_called_on_no_roll_chip(self):
        """resolve_active_card is called with 'No Roll' after no-roll chip click."""
        view, callback = _make_view_with_pending()
        view._spawn_dm_thread = MagicMock()  # type: ignore[method-assign]
        view._chat.reset_mock()
        callback("No Roll")
        view._chat.resolve_active_card.assert_called_once_with("No Roll")
