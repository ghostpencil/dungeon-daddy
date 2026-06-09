from __future__ import annotations


def _state():
    from dungeon_daddy.ui.player_action_state import PlayerActionState
    return PlayerActionState()


# ---------------------------------------------------------------------------
# Slice 1 — default state
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_actor_id_is_none(self):
        assert _state().actor_id is None

    def test_action_key_is_none(self):
        assert _state().action_key is None

    def test_intent_is_empty_string(self):
        assert _state().intent == ""

    def test_awaiting_confirmation_is_false(self):
        assert _state().awaiting_confirmation is False

    def test_resolution_summary_is_none(self):
        assert _state().resolution_summary is None


# ---------------------------------------------------------------------------
# Slice 2 — select_actor
# ---------------------------------------------------------------------------

class TestSelectActor:
    def test_sets_actor_id(self):
        s = _state()
        s.select_actor("hero-1")
        assert s.actor_id == "hero-1"

    def test_clears_actor_id(self):
        s = _state()
        s.select_actor("hero-1")
        s.select_actor(None)
        assert s.actor_id is None


# ---------------------------------------------------------------------------
# Slice 3 — select_action valid key
# ---------------------------------------------------------------------------

class TestSelectAction:
    def test_sets_valid_action_key(self):
        s = _state()
        s.select_action("study")
        assert s.action_key == "study"

    def test_accepts_all_nine_keys(self):
        from dungeon_daddy.ui.player_action_state import ACTION_KEYS
        s = _state()
        for key in ACTION_KEYS:
            s.select_action(key)
            assert s.action_key == key

    def test_clears_action_key_with_none(self):
        s = _state()
        s.select_action("fight")
        s.select_action(None)
        assert s.action_key is None

    def test_invalid_key_raises_value_error(self):
        import pytest
        s = _state()
        with pytest.raises(ValueError, match="fireball"):
            s.select_action("fireball")


# ---------------------------------------------------------------------------
# Slice 4 — set_intent
# ---------------------------------------------------------------------------

class TestSetIntent:
    def test_updates_intent_text(self):
        s = _state()
        s.set_intent("I study the mural")
        assert s.intent == "I study the mural"

    def test_overwrites_previous_intent(self):
        s = _state()
        s.set_intent("first")
        s.set_intent("second")
        assert s.intent == "second"


# ---------------------------------------------------------------------------
# Slice 5 — awaiting_confirmation
# ---------------------------------------------------------------------------

class TestAwaitingConfirmation:
    def test_set_true(self):
        s = _state()
        s.set_awaiting_confirmation(True)
        assert s.awaiting_confirmation is True

    def test_set_false(self):
        s = _state()
        s.set_awaiting_confirmation(True)
        s.set_awaiting_confirmation(False)
        assert s.awaiting_confirmation is False


# ---------------------------------------------------------------------------
# Slice 6 — resolution_summary
# ---------------------------------------------------------------------------

class TestResolutionSummary:
    def test_sets_summary(self):
        s = _state()
        s.set_resolution_summary("Partial success — Weird +1")
        assert s.resolution_summary == "Partial success — Weird +1"

    def test_clears_summary(self):
        s = _state()
        s.set_resolution_summary("something")
        s.set_resolution_summary(None)
        assert s.resolution_summary is None


# ---------------------------------------------------------------------------
# Slice 7 — reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_action_intent_confirmation_summary(self):
        s = _state()
        s.select_actor("hero-1")
        s.select_action("fight")
        s.set_intent("charge the door")
        s.set_awaiting_confirmation(True)
        s.set_resolution_summary("Full success")
        s.reset()
        assert s.action_key is None
        assert s.intent == ""
        assert s.awaiting_confirmation is False
        assert s.resolution_summary is None

    def test_reset_preserves_actor_id(self):
        s = _state()
        s.select_actor("hero-1")
        s.reset()
        assert s.actor_id == "hero-1"


# ---------------------------------------------------------------------------
# Slice 8 — actor roster
# ---------------------------------------------------------------------------

class TestActorRoster:
    def test_empty_roster_gives_no_actor(self):
        s = _state()
        s.set_actor_roster([])
        assert s.actor_id is None

    def test_empty_roster_has_multiple_actors_false(self):
        s = _state()
        s.set_actor_roster([])
        assert s.has_multiple_actors is False

    def test_single_actor_roster_selects_that_actor(self):
        s = _state()
        s.set_actor_roster(["hero-1"])
        assert s.actor_id == "hero-1"

    def test_single_actor_roster_has_multiple_actors_false(self):
        s = _state()
        s.set_actor_roster(["hero-1"])
        assert s.has_multiple_actors is False

    def test_multi_actor_roster_selects_first(self):
        s = _state()
        s.set_actor_roster(["hero-1", "hero-2", "hero-3"])
        assert s.actor_id == "hero-1"

    def test_multi_actor_roster_has_multiple_actors_true(self):
        s = _state()
        s.set_actor_roster(["hero-1", "hero-2"])
        assert s.has_multiple_actors is True


# ---------------------------------------------------------------------------
# Slice 9 — select_next_actor
# ---------------------------------------------------------------------------

class TestSelectNextActor:
    def test_single_actor_next_is_noop(self):
        s = _state()
        s.set_actor_roster(["hero-1"])
        s.select_next_actor()
        assert s.actor_id == "hero-1"

    def test_advances_to_second_actor(self):
        s = _state()
        s.set_actor_roster(["hero-1", "hero-2"])
        s.select_next_actor()
        assert s.actor_id == "hero-2"

    def test_wraps_from_last_to_first(self):
        s = _state()
        s.set_actor_roster(["hero-1", "hero-2", "hero-3"])
        s.select_next_actor()
        s.select_next_actor()
        s.select_next_actor()
        assert s.actor_id == "hero-1"

    def test_empty_roster_next_is_noop(self):
        s = _state()
        s.set_actor_roster([])
        s.select_next_actor()
        assert s.actor_id is None


# ---------------------------------------------------------------------------
# Slice 10 — select_prev_actor
# ---------------------------------------------------------------------------

class TestSelectPrevActor:
    def test_single_actor_prev_is_noop(self):
        s = _state()
        s.set_actor_roster(["hero-1"])
        s.select_prev_actor()
        assert s.actor_id == "hero-1"

    def test_wraps_from_first_to_last(self):
        s = _state()
        s.set_actor_roster(["hero-1", "hero-2", "hero-3"])
        s.select_prev_actor()
        assert s.actor_id == "hero-3"

    def test_goes_back_from_second_to_first(self):
        s = _state()
        s.set_actor_roster(["hero-1", "hero-2"])
        s.select_next_actor()
        s.select_prev_actor()
        assert s.actor_id == "hero-1"

    def test_empty_roster_prev_is_noop(self):
        s = _state()
        s.set_actor_roster([])
        s.select_prev_actor()
        assert s.actor_id is None
