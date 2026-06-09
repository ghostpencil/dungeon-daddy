"""Unit tests for stress_routing.choose_stress_track() — Phase 35.6."""
from __future__ import annotations

import pytest

from dungeon_daddy.rpg.stress_routing import choose_stress_track
from dungeon_daddy.rpg.models import ClockState


# ---------------------------------------------------------------------------
# Action-key mapping (no clocks, no intent)
# ---------------------------------------------------------------------------

def test_fight_defaults_to_body():
    assert choose_stress_track(action_key="fight") == "body"


def test_move_defaults_to_body():
    assert choose_stress_track(action_key="move") == "body"


def test_endure_defaults_to_body():
    assert choose_stress_track(action_key="endure") == "body"


def test_tinker_defaults_to_body():
    assert choose_stress_track(action_key="tinker") == "body"


def test_sense_defaults_to_composure():
    assert choose_stress_track(action_key="sense") == "composure"


def test_study_defaults_to_composure():
    assert choose_stress_track(action_key="study") == "composure"


def test_focus_defaults_to_composure():
    assert choose_stress_track(action_key="focus") == "composure"


def test_sway_defaults_to_bonds():
    assert choose_stress_track(action_key="sway") == "bonds"


def test_channel_defaults_to_weird():
    assert choose_stress_track(action_key="channel") == "weird"


def test_unknown_action_falls_back_to_body():
    assert choose_stress_track(action_key="zap") == "body"


# ---------------------------------------------------------------------------
# Explicit override
# ---------------------------------------------------------------------------

def test_explicit_track_wins_over_everything():
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Dungeon Stirs",
        segments=6, filled=1, category="danger",
    )
    assert choose_stress_track(
        action_key="fight", matched_clocks=[clock], explicit_track="weird"
    ) == "weird"


# ---------------------------------------------------------------------------
# Clock category routing (slice 4)
# ---------------------------------------------------------------------------

def _clock_with_category(category: str, clock_level: str = "dungeon") -> ClockState:
    return ClockState(
        clock_id="ck1", campaign_id="c1", label="Test Clock",
        segments=6, filled=1, category=category, clock_level=clock_level,  # type: ignore[arg-type]
    )


def test_dungeon_intimacy_clock_routes_to_weird():
    clock = _clock_with_category("dungeon_intimacy")
    assert choose_stress_track(action_key="sense", matched_clocks=[clock]) == "weird"


def test_relationship_clock_routes_to_bonds():
    clock = _clock_with_category("relationship", "character")
    assert choose_stress_track(action_key="fight", matched_clocks=[clock]) == "bonds"


def test_ritual_clock_routes_to_weird():
    clock = _clock_with_category("ritual")
    assert choose_stress_track(action_key="study", matched_clocks=[clock]) == "weird"


def test_danger_clock_routes_to_body():
    clock = _clock_with_category("danger", "room")
    assert choose_stress_track(action_key="channel", matched_clocks=[clock]) == "body"


def test_horror_clock_routes_to_composure():
    clock = _clock_with_category("horror")
    assert choose_stress_track(action_key="fight", matched_clocks=[clock]) == "composure"


def test_category_takes_priority_over_clock_level():
    # clock_level=dungeon would route "weird", but category="danger" routes "body"
    clock = _clock_with_category("danger", "dungeon")
    assert choose_stress_track(action_key="fight", matched_clocks=[clock]) == "body"


# ---------------------------------------------------------------------------
# Clock level routing when category absent (slice 4)
# ---------------------------------------------------------------------------

def _clock_with_level(level: str) -> ClockState:
    return ClockState(
        clock_id="ck1", campaign_id="c1", label="Test Clock",
        segments=6, filled=1, clock_level=level,  # type: ignore[arg-type]
    )


def test_dungeon_level_clock_routes_to_weird():
    clock = _clock_with_level("dungeon")
    assert choose_stress_track(action_key="fight", matched_clocks=[clock]) == "weird"


def test_character_level_clock_routes_to_bonds():
    clock = _clock_with_level("character")
    assert choose_stress_track(action_key="fight", matched_clocks=[clock]) == "bonds"


def test_quest_level_clock_routes_to_composure():
    clock = _clock_with_level("quest")
    assert choose_stress_track(action_key="fight", matched_clocks=[clock]) == "composure"


def test_room_level_clock_routes_to_body():
    clock = _clock_with_level("room")
    assert choose_stress_track(action_key="channel", matched_clocks=[clock]) == "body"


# ---------------------------------------------------------------------------
# Intent keyword routing (slice 5)
# ---------------------------------------------------------------------------

def test_intent_dungeon_routes_to_weird_when_no_clock():
    assert choose_stress_track(
        action_key="sense", intent="I reach out to the dungeon and listen"
    ) == "weird"


def test_intent_trust_routes_to_bonds():
    assert choose_stress_track(
        action_key="fight", intent="I appeal to his trust"
    ) == "bonds"


def test_intent_betray_routes_to_bonds():
    assert choose_stress_track(
        action_key="move", intent="I betray the signal"
    ) == "bonds"


def test_intent_fear_routes_to_composure():
    assert choose_stress_track(
        action_key="endure", intent="I resist the fear"
    ) == "composure"


def test_intent_weird_beats_bonds_when_both_match():
    # "dungeon" (weird) + "trust" (bonds) — weird wins
    assert choose_stress_track(
        action_key="sense", intent="I trust the dungeon's whisper"
    ) == "weird"


def test_no_intent_no_clocks_uses_action_key():
    assert choose_stress_track(action_key="sense", intent=None) == "composure"


# ---------------------------------------------------------------------------
# 37.1.3 — Intent overrides action-key default (no clocks)
# ---------------------------------------------------------------------------

def test_study_intent_ritual_dungeon_voice_routes_to_weird():
    # "study" defaults to composure; intent keywords override to weird
    assert choose_stress_track(
        action_key="study", intent="I begin a ritual in the dungeon and hear a voice"
    ) == "weird"


def test_move_intent_protect_ally_promise_routes_to_bonds():
    # "move" defaults to body; intent keywords override to bonds
    assert choose_stress_track(
        action_key="move", intent="I protect my ally and keep my promise"
    ) == "bonds"


def test_tinker_intent_fear_nightmare_truth_routes_to_composure():
    # "tinker" defaults to body; intent keywords override to composure
    assert choose_stress_track(
        action_key="tinker", intent="I face a fear born of nightmare and truth"
    ) == "composure"


def test_clock_category_danger_beats_intent_ritual():
    # clock category "danger" → body; intent "ritual" would give weird — category wins
    clock = _clock_with_category("danger")
    assert choose_stress_track(
        action_key="study", intent="I perform a ritual", matched_clocks=[clock]
    ) == "body"
