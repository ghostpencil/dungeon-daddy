"""Unit tests for compute_world_reaction() — Phase 35 step 35-2."""
from __future__ import annotations

from dungeon_daddy.rpg.models import (
    ActionResolution,
    ActorState,
    ClockState,
    ObjectReactionBinding,
    StressTrack,
)
from dungeon_daddy.rpg.world_reaction import (
    compute_world_reaction,
    resolve_scripted_bindings,
    select_ambient_clock,
)


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
        clock_level="room",
        category="danger",
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
    assert result.summary_lines[0] == "World reaction (MISS):"
    combined = " ".join(result.summary_lines)
    assert "Clock [Heat Rising]:" in combined  # the ticked threat clock
    assert "Hero [body]:" in combined          # the stressed PC


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


# ---------------------------------------------------------------------------
# Phase 35.5 — Clock scoping: level filter
# ---------------------------------------------------------------------------

def test_level_clock_advances_on_matching_level():
    resolution = _resolution("miss")
    actor, tracks = _pc()
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Factory Reawakens",
        segments=8, filled=0, clock_level="level", level_id="level-2",
    )
    result = compute_world_reaction(
        resolution, [clock], [(actor, tracks)], current_level_id="level-2"
    )
    assert len(result.clock_lines) == 1


def test_level_clock_skipped_on_wrong_level():
    resolution = _resolution("miss")
    actor, tracks = _pc()
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Factory Reawakens",
        segments=8, filled=0, clock_level="level", level_id="level-2",
    )
    result = compute_world_reaction(
        resolution, [clock], [(actor, tracks)], current_level_id="level-1"
    )
    assert result.clock_lines == []


def test_clock_without_level_id_advances_on_any_level():
    resolution = _resolution("miss")
    actor, tracks = _pc()
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Dungeon Stirs",
        segments=6, filled=0, clock_level="dungeon",
    )
    result = compute_world_reaction(
        resolution, [clock], [(actor, tracks)], current_level_id="level-1"
    )
    assert len(result.clock_lines) == 1


def test_level_clock_advances_when_current_level_unknown():
    # Fail open — don't suppress a clock if we can't determine the level
    resolution = _resolution("miss")
    actor, tracks = _pc()
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Factory Reawakens",
        segments=8, filled=0, clock_level="level", level_id="level-2",
    )
    result = compute_world_reaction(
        resolution, [clock], [(actor, tracks)], current_level_id=None
    )
    assert len(result.clock_lines) == 1


# ---------------------------------------------------------------------------
# Phase 35.6 — Stress routing by action key
# ---------------------------------------------------------------------------

def test_channel_miss_applies_weird_stress():
    resolution = ActionResolution(
        resolution_id="r1", campaign_id="c1", actor_id="a1",
        action_key="channel", dice_rolled=[2], outcome="miss",
    )
    actor, tracks = _pc()
    tracks["weird"] = StressTrack(track_key="weird", capacity=4, filled=0)
    result = compute_world_reaction(resolution, [], [(actor, tracks)])
    assert len(result.stress_lines) == 1
    assert result.stress_lines[0].track_key == "weird"


# ---------------------------------------------------------------------------
# Phase 37.1.2 — Intent-based stress routing through compute_world_reaction
# ---------------------------------------------------------------------------

def test_intent_routes_stress_when_no_clock_overrides():
    # fight defaults to "body"; intent keyword "whisper" → "weird"
    resolution = ActionResolution(
        resolution_id="r1", campaign_id="c1", actor_id="a1",
        action_key="fight", dice_rolled=[1, 2], outcome="miss",
        intent="I listen to the dungeon's whisper",
    )
    actor = ActorState(
        actor_id="a1", campaign_id="c1", actor_type="pc",
        slug="hero", display_name="Hero",
    )
    tracks = {
        "body": StressTrack(track_key="body", capacity=4, filled=0),
        "weird": StressTrack(track_key="weird", capacity=4, filled=0),
    }
    result = compute_world_reaction(resolution, [], [(actor, tracks)])
    assert len(result.stress_lines) == 1
    assert result.stress_lines[0].track_key == "weird"


def test_clock_category_wins_over_intent():
    # danger clock → "body"; intent "whisper" would give "weird" — clock wins
    resolution = ActionResolution(
        resolution_id="r1", campaign_id="c1", actor_id="a1",
        action_key="channel", dice_rolled=[1], outcome="miss",
        intent="I listen to the dungeon's whisper",
    )
    actor = ActorState(
        actor_id="a1", campaign_id="c1", actor_type="pc",
        slug="hero", display_name="Hero",
    )
    tracks = {
        "body": StressTrack(track_key="body", capacity=4, filled=0),
        "weird": StressTrack(track_key="weird", capacity=4, filled=0),
    }
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Danger Rising",
        segments=6, filled=1, category="danger",
    )
    result = compute_world_reaction(resolution, [clock], [(actor, tracks)])
    assert result.stress_lines[0].track_key == "body"


def test_sway_partial_applies_bonds_stress():
    resolution = ActionResolution(
        resolution_id="r1", campaign_id="c1", actor_id="a1",
        action_key="sway", dice_rolled=[4], outcome="partial",
    )
    actor, tracks = _pc()
    tracks["bonds"] = StressTrack(track_key="bonds", capacity=4, filled=0)
    result = compute_world_reaction(resolution, [], [(actor, tracks)])
    assert len(result.stress_lines) == 1
    assert result.stress_lines[0].track_key == "bonds"


def test_sense_miss_with_dungeon_intimacy_clock_applies_weird_stress():
    resolution = ActionResolution(
        resolution_id="r1", campaign_id="c1", actor_id="a1",
        action_key="sense", dice_rolled=[2], outcome="miss",
    )
    actor, tracks = _pc()
    tracks["weird"] = StressTrack(track_key="weird", capacity=4, filled=0)
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Dungeon Learns You",
        segments=6, filled=0, category="dungeon_intimacy",
        action_tags=["sense"],
    )
    result = compute_world_reaction(resolution, [clock], [(actor, tracks)])
    assert result.stress_lines[0].track_key == "weird"


def test_fight_miss_with_relationship_clock_applies_bonds_stress():
    # Category has priority over action key: relationship → bonds beats fight → body
    resolution = ActionResolution(
        resolution_id="r1", campaign_id="c1", actor_id="a1",
        action_key="fight", dice_rolled=[1], outcome="miss",
    )
    actor, tracks = _pc()
    tracks["bonds"] = StressTrack(track_key="bonds", capacity=4, filled=0)
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Dax Remembers",
        segments=6, filled=0, category="relationship",
        clock_level="character",
    )
    result = compute_world_reaction(resolution, [clock], [(actor, tracks)])
    assert result.stress_lines[0].track_key == "bonds"


def test_weird_stress_overflow_flags_fallout():
    resolution = ActionResolution(
        resolution_id="r1", campaign_id="c1", actor_id="a1",
        action_key="channel", dice_rolled=[2], outcome="miss",
    )
    actor, tracks = _pc()
    tracks["weird"] = StressTrack(track_key="weird", capacity=4, filled=3)
    result = compute_world_reaction(resolution, [], [(actor, tracks)])
    assert result.stress_lines[0].track_key == "weird"
    assert result.stress_lines[0].triggered_fallout is True
    assert result.stress_lines[0].new_filled == 4


def test_non_body_stress_only_applied_to_acting_actor():
    resolution = ActionResolution(
        resolution_id="r1", campaign_id="c1", actor_id="a1",
        action_key="sway", dice_rolled=[2], outcome="miss",
    )
    actor1, tracks1 = _pc(actor_id="a1")
    tracks1["bonds"] = StressTrack(track_key="bonds", capacity=4, filled=0)
    actor2, tracks2 = _pc(actor_id="a2")
    tracks2["bonds"] = StressTrack(track_key="bonds", capacity=4, filled=0)
    result = compute_world_reaction(
        resolution, [], [(actor1, tracks1), (actor2, tracks2)]
    )
    assert len(result.stress_lines) == 1
    assert result.stress_lines[0].actor_id == "a1"
    assert result.stress_lines[0].track_key == "bonds"


def test_level_and_room_filters_compose():
    # Clock has both scope_room_id and level_id — both must match
    actor, tracks = _pc()
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Control Room Alert",
        segments=6, filled=0,
        clock_level="level", level_id="level-2",
        scope_room_id="control_room",
    )
    res = _resolution("miss")

    # both match
    r1 = compute_world_reaction(
        res, [clock], [(actor, tracks)],
        current_room_id="control_room", current_level_id="level-2"
    )
    assert len(r1.clock_lines) == 1

    # right room, wrong level
    r2 = compute_world_reaction(
        res, [clock], [(actor, tracks)],
        current_room_id="control_room", current_level_id="level-1"
    )
    assert r2.clock_lines == []

    # right level, wrong room
    r3 = compute_world_reaction(
        res, [clock], [(actor, tracks)],
        current_room_id="other_room", current_level_id="level-2"
    )
    assert r3.clock_lines == []


# ---------------------------------------------------------------------------
# Phase 51.6 Slice 5 — select_ambient_clock (design §4)
# ---------------------------------------------------------------------------

def _adverse_room_clock(
    clock_id: str, room_id: str, category: str = "danger", label: str = "Nest",
) -> ClockState:
    return ClockState(
        clock_id=clock_id, campaign_id="c1", label=label, segments=6, filled=1,
        clock_level="room", scope_room_id=room_id, category=category,
    )


def _adverse_level_clock(
    clock_id: str, level_id: str, category: str = "danger", label: str = "Alarm",
) -> ClockState:
    return ClockState(
        clock_id=clock_id, campaign_id="c1", label=label, segments=6, filled=1,
        clock_level="level", level_id=level_id, category=category,
    )


def test_select_ambient_clock_picks_room_scoped_adverse():
    # Worked example: STUDY-miss on the statue in R1 → "Scorpion Nest Agitated".
    nest = _adverse_room_clock("scorpion-nest", "R1", label="Scorpion Nest Agitated")
    result = select_ambient_clock([nest], room_id="R1", level_id="level-1")
    assert result is nest


def test_select_ambient_clock_none_when_no_local_adverse():
    # Worked example: no local adverse clock → None (narration only).
    elsewhere = _adverse_room_clock("nest", "R9")
    result = select_ambient_clock([elsewhere], room_id="R1", level_id="level-1")
    assert result is None


def test_select_ambient_clock_prefers_room_over_level():
    room = _adverse_room_clock("room-clock", "R1")
    level = _adverse_level_clock("level-clock", "level-1")
    result = select_ambient_clock([level, room], room_id="R1", level_id="level-1")
    assert result is room


def test_select_ambient_clock_ties_broken_by_lowest_id():
    first = _adverse_room_clock("aaa", "R1")
    second = _adverse_room_clock("bbb", "R1")
    result = select_ambient_clock([second, first], room_id="R1", level_id="level-1")
    assert result is first


def test_select_ambient_clock_falls_to_level_when_no_room_clock():
    level = _adverse_level_clock("level-clock", "level-1")
    result = select_ambient_clock([level], room_id="R1", level_id="level-1")
    assert result is level


def test_select_ambient_clock_ignores_non_adverse_categories():
    # objective / relationship / faction_pressure / dungeon_intimacy are firewalled.
    objective = _adverse_room_clock("obj", "R1", category="objective")
    intimacy = _adverse_room_clock("intim", "R1", category="dungeon_intimacy")
    result = select_ambient_clock([objective, intimacy], room_id="R1", level_id="level-1")
    assert result is None


def test_select_ambient_clock_ignores_dungeon_scope():
    dungeon = ClockState(
        clock_id="overload", campaign_id="c1", label="Arcane Overload Building",
        segments=8, filled=2, clock_level="dungeon", category="danger",
    )
    result = select_ambient_clock([dungeon], room_id="R1", level_id="level-1")
    assert result is None


def test_select_ambient_clock_ignores_inactive():
    done = _adverse_room_clock("nest", "R1")
    done.status = "completed"
    result = select_ambient_clock([done], room_id="R1", level_id="level-1")
    assert result is None


def test_select_ambient_clock_recognizes_synonym_category_as_adverse():
    # A pre-normalization "threat" clock is still adverse (→ danger).
    threat = _adverse_room_clock("nest", "R1", category="threat")
    result = select_ambient_clock([threat], room_id="R1", level_id="level-1")
    assert result is threat


# ---------------------------------------------------------------------------
# Phase 51.6 Slice 6 — resolve_scripted_bindings (design §5/§9)
# ---------------------------------------------------------------------------

def _binding(
    verb: str,
    outcome: str,
    *,
    clock_slug: str | None = "arcane-overload-building",
    clock_delta: int = 0,
    stress_track: str | None = None,
    stress_amount: int = 0,
    binding_id: str = "b1",
) -> ObjectReactionBinding:
    return ObjectReactionBinding(
        binding_id=binding_id,
        object_id="obj1",
        action_verb=verb,
        outcome=outcome,  # type: ignore[arg-type]
        clock_slug=clock_slug,
        clock_delta=clock_delta,
        stress_track=stress_track,
        stress_amount=stress_amount,
    )


def test_resolve_scripted_bindings_matches_verb_and_outcome():
    binding = _binding("tinker", "miss", clock_delta=1)
    result = resolve_scripted_bindings([binding], "tinker", "miss")
    assert len(result) == 1
    assert result[0].clock_slug == "arcane-overload-building"
    assert result[0].clock_delta == 1


def test_resolve_scripted_bindings_wildcard_verb_matches_any():
    binding = _binding("*", "miss", clock_delta=2)
    result = resolve_scripted_bindings([binding], "study", "miss")
    assert len(result) == 1
    assert result[0].clock_delta == 2


def test_resolve_scripted_bindings_skips_non_matching_verb():
    binding = _binding("tinker", "miss", clock_delta=1)
    result = resolve_scripted_bindings([binding], "study", "miss")
    assert result == []


def test_resolve_scripted_bindings_skips_non_matching_outcome_for_miss_query():
    # Query outcome="miss" with only a partial row → no match, no fallback.
    binding = _binding("tinker", "partial", clock_delta=1)
    result = resolve_scripted_bindings([binding], "tinker", "miss")
    assert result == []


def test_resolve_scripted_bindings_empty_returns_nothing():
    result = resolve_scripted_bindings([], "tinker", "miss")
    assert result == []


def test_resolve_scripted_bindings_partial_uses_authored_partial_when_present():
    miss = _binding("tinker", "miss", clock_delta=2, binding_id="m")
    partial = _binding("tinker", "partial", clock_delta=1, binding_id="p")
    result = resolve_scripted_bindings([miss, partial], "tinker", "partial")
    assert len(result) == 1
    assert result[0].clock_delta == 1  # authored partial, not halved miss


def test_resolve_scripted_bindings_partial_falls_back_to_half_miss():
    miss = _binding("tinker", "miss", clock_delta=2, stress_track="body", stress_amount=2)
    result = resolve_scripted_bindings([miss], "tinker", "partial")
    assert len(result) == 1
    assert result[0].clock_delta == 1  # 2 // 2
    assert result[0].stress_amount == 1  # 2 // 2


def test_resolve_scripted_bindings_partial_fallback_min_one_when_miss_nonzero():
    # half of 1 rounds down to 0, but a nonzero miss binding stays at least 1.
    miss = _binding("tinker", "miss", clock_delta=1)
    result = resolve_scripted_bindings([miss], "tinker", "partial")
    assert result[0].clock_delta == 1


def test_resolve_scripted_bindings_partial_fallback_zero_stays_zero():
    # A miss binding with no stress → the halved fallback keeps stress at 0.
    miss = _binding("tinker", "miss", clock_delta=2, stress_amount=0)
    result = resolve_scripted_bindings([miss], "tinker", "partial")
    assert result[0].stress_amount == 0
