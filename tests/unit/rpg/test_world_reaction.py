"""Unit tests for compute_world_reaction() — Phase 35 step 35-2."""
from __future__ import annotations

from dungeon_daddy.rpg.models import (
    ActionResolution,
    ActorState,
    ClockState,
    StressTrack,
)
from dungeon_daddy.rpg.world_reaction import compute_world_reaction


def _resolution(outcome: str, actor_id: str = "a1") -> ActionResolution:
    return ActionResolution(
        resolution_id="res1",
        campaign_id="c1",
        actor_id=actor_id,
        action_key="fight",
        dice_rolled=[3],
        outcome=outcome,  # type: ignore[arg-type]
    )


def _clock(clock_id: str = "ck1", filled: int = 1, segments: int = 6) -> ClockState:
    return ClockState(
        clock_id=clock_id,
        campaign_id="c1",
        label="Heat Rising",
        segments=segments,
        filled=filled,
    )


def _pc(actor_id: str = "a1", body_filled: int = 0) -> tuple[ActorState, dict[str, StressTrack]]:
    actor = ActorState(
        actor_id=actor_id,
        campaign_id="c1",
        actor_type="pc",
        slug="hero",
        display_name="Hero",
    )
    tracks = {"body": StressTrack(track_key="body", capacity=4, filled=body_filled)}
    return actor, tracks


# ---------------------------------------------------------------------------
# Miss — clocks +2, PC takes 2 body stress
# ---------------------------------------------------------------------------

def test_miss_advances_active_clock_by_two():
    resolution = _resolution("miss")
    actor, tracks = _pc()
    result = compute_world_reaction(resolution, [_clock()], [(actor, tracks)])
    assert len(result.clock_lines) == 1
    assert result.clock_lines[0].ticks == 2
    assert result.clock_lines[0].new_filled == 3


def test_miss_applies_two_body_stress_to_pc():
    resolution = _resolution("miss")
    actor, tracks = _pc()
    result = compute_world_reaction(resolution, [_clock()], [(actor, tracks)])
    assert len(result.stress_lines) == 1
    assert result.stress_lines[0].amount == 2
    assert result.stress_lines[0].track_key == "body"
    assert result.stress_lines[0].new_filled == 2


# ---------------------------------------------------------------------------
# Partial — clocks +1, PC takes 1 body stress
# ---------------------------------------------------------------------------

def test_partial_advances_active_clock_by_one():
    resolution = _resolution("partial")
    actor, tracks = _pc()
    result = compute_world_reaction(resolution, [_clock()], [(actor, tracks)])
    assert result.clock_lines[0].ticks == 1
    assert result.clock_lines[0].new_filled == 2


def test_partial_applies_one_body_stress_to_pc():
    resolution = _resolution("partial")
    actor, tracks = _pc()
    result = compute_world_reaction(resolution, [_clock()], [(actor, tracks)])
    assert result.stress_lines[0].amount == 1
    assert result.stress_lines[0].new_filled == 1


# ---------------------------------------------------------------------------
# Full — no clock advance, no stress
# ---------------------------------------------------------------------------

def test_full_does_not_advance_clocks():
    resolution = _resolution("full")
    actor, tracks = _pc()
    result = compute_world_reaction(resolution, [_clock()], [(actor, tracks)])
    assert result.clock_lines == []


def test_full_does_not_apply_stress():
    resolution = _resolution("full")
    actor, tracks = _pc()
    result = compute_world_reaction(resolution, [_clock()], [(actor, tracks)])
    assert result.stress_lines == []


# ---------------------------------------------------------------------------
# Critical — clocks retreat -1 (floor 0), no stress
# ---------------------------------------------------------------------------

def test_critical_retreats_clock_by_one():
    resolution = _resolution("critical")
    actor, tracks = _pc()
    clock = _clock(filled=3)
    result = compute_world_reaction(resolution, [clock], [(actor, tracks)])
    assert result.clock_lines[0].ticks == -1
    assert result.clock_lines[0].new_filled == 2


def test_critical_does_not_retreat_below_zero():
    resolution = _resolution("critical")
    actor, tracks = _pc()
    clock = _clock(filled=0)
    result = compute_world_reaction(resolution, [clock], [(actor, tracks)])
    assert result.clock_lines[0].new_filled == 0


def test_critical_does_not_apply_stress():
    resolution = _resolution("critical")
    actor, tracks = _pc()
    result = compute_world_reaction(resolution, [_clock()], [(actor, tracks)])
    assert result.stress_lines == []


# ---------------------------------------------------------------------------
# Completed clocks are skipped
# ---------------------------------------------------------------------------

def test_completed_clock_is_skipped():
    resolution = _resolution("miss")
    actor, tracks = _pc()
    done_clock = ClockState(
        clock_id="ck_done", campaign_id="c1", label="Done", segments=4, filled=4,
        status="completed",
    )
    result = compute_world_reaction(resolution, [done_clock], [(actor, tracks)])
    assert result.clock_lines == []


# ---------------------------------------------------------------------------
# Summary lines are generated
# ---------------------------------------------------------------------------

def test_miss_produces_summary_lines():
    resolution = _resolution("miss")
    actor, tracks = _pc()
    result = compute_world_reaction(resolution, [_clock()], [(actor, tracks)])
    assert len(result.summary_lines) >= 1
    combined = " ".join(result.summary_lines).lower()
    assert "heat" in combined or "clock" in combined or "stress" in combined


# ---------------------------------------------------------------------------
# Stress overflow clamps at capacity and flags fallout
# ---------------------------------------------------------------------------

def test_miss_stress_overflow_flags_fallout():
    resolution = _resolution("miss")
    actor, tracks = _pc(body_filled=3)
    result = compute_world_reaction(resolution, [], [(actor, tracks)])
    assert result.stress_lines[0].triggered_fallout is True
    assert result.stress_lines[0].new_filled == 4


# ---------------------------------------------------------------------------
# Only the acting actor takes stress — not the whole party
# ---------------------------------------------------------------------------

def test_miss_stress_only_applied_to_acting_actor():
    resolution = _resolution("miss", actor_id="a1")
    acting, acting_tracks = _pc(actor_id="a1")
    bystander, bystander_tracks = _pc(actor_id="a2")
    result = compute_world_reaction(
        resolution, [], [(acting, acting_tracks), (bystander, bystander_tracks)]
    )
    assert len(result.stress_lines) == 1
    assert result.stress_lines[0].actor_id == "a1"


def test_partial_stress_only_applied_to_acting_actor():
    resolution = _resolution("partial", actor_id="a2")
    actor1, tracks1 = _pc(actor_id="a1")
    actor2, tracks2 = _pc(actor_id="a2")
    result = compute_world_reaction(
        resolution, [], [(actor1, tracks1), (actor2, tracks2)]
    )
    assert len(result.stress_lines) == 1
    assert result.stress_lines[0].actor_id == "a2"


# ---------------------------------------------------------------------------
# Phase 35.5 — Clock scoping: room filter
# ---------------------------------------------------------------------------

def test_scoped_clock_advances_in_matching_room():
    resolution = _resolution("miss")
    actor, tracks = _pc()
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Trap Primed",
        segments=6, filled=1, scope_room_id="room_a",
    )
    result = compute_world_reaction(
        resolution, [clock], [(actor, tracks)], current_room_id="room_a"
    )
    assert len(result.clock_lines) == 1
    assert result.clock_lines[0].ticks == 2


def test_scoped_clock_skipped_in_wrong_room():
    resolution = _resolution("miss")
    actor, tracks = _pc()
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Trap Primed",
        segments=6, filled=1, scope_room_id="room_a",
    )
    result = compute_world_reaction(
        resolution, [clock], [(actor, tracks)], current_room_id="room_b"
    )
    assert result.clock_lines == []


def test_global_clock_advances_regardless_of_room():
    resolution = _resolution("miss")
    actor, tracks = _pc()
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Heat Rising",
        segments=6, filled=1,
    )
    result = compute_world_reaction(
        resolution, [clock], [(actor, tracks)], current_room_id="some_room"
    )
    assert len(result.clock_lines) == 1


# ---------------------------------------------------------------------------
# Phase 35.5 — Clock scoping: action tags
# ---------------------------------------------------------------------------

def test_action_tagged_clock_advances_on_matching_action():
    resolution = ActionResolution(
        resolution_id="res1", campaign_id="c1", actor_id="a1",
        action_key="sense", dice_rolled=[3], outcome="miss",
    )
    actor, tracks = _pc()
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Alert Clock",
        segments=6, filled=1, action_tags=["sense", "study"],
    )
    result = compute_world_reaction(resolution, [clock], [(actor, tracks)])
    assert len(result.clock_lines) == 1


def test_action_tagged_clock_skipped_on_non_matching_action():
    resolution = _resolution("miss")  # action_key="fight"
    actor, tracks = _pc()
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Alert Clock",
        segments=6, filled=1, action_tags=["sense", "study"],
    )
    result = compute_world_reaction(resolution, [clock], [(actor, tracks)])
    assert result.clock_lines == []


def test_untagged_clock_advances_on_any_action():
    resolution = _resolution("miss")  # action_key="fight"
    actor, tracks = _pc()
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Heat Rising",
        segments=6, filled=1, action_tags=[],
    )
    result = compute_world_reaction(resolution, [clock], [(actor, tracks)])
    assert len(result.clock_lines) == 1


def test_composed_scope_and_tags_both_must_match():
    actor, tracks = _pc()
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Boiler Trap",
        segments=6, filled=1,
        scope_room_id="room_boiler", action_tags=["fight", "move"],
    )
    # both match — should advance
    res_match = ActionResolution(
        resolution_id="r1", campaign_id="c1", actor_id="a1",
        action_key="fight", dice_rolled=[2], outcome="miss",
    )
    result = compute_world_reaction(
        res_match, [clock], [(actor, tracks)], current_room_id="room_boiler"
    )
    assert len(result.clock_lines) == 1

    # room matches but action does not — should not advance
    res_wrong_action = ActionResolution(
        resolution_id="r2", campaign_id="c1", actor_id="a1",
        action_key="sense", dice_rolled=[2], outcome="miss",
    )
    result2 = compute_world_reaction(
        res_wrong_action, [clock], [(actor, tracks)], current_room_id="room_boiler"
    )
    assert result2.clock_lines == []

    # action matches but room does not — should not advance
    result3 = compute_world_reaction(
        res_match, [clock], [(actor, tracks)], current_room_id="room_other"
    )
    assert result3.clock_lines == []
