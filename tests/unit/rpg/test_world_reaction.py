"""Unit tests for compute_world_reaction() and its Phase 51.6 helpers."""
from __future__ import annotations

from dungeon_daddy.rpg.models import (
    ActionResolution,
    ActorState,
    ClockState,
    ObjectReactionBinding,
    RoomObject,
    StressTrack,
)
from dungeon_daddy.rpg.world_reaction import (
    compute_world_reaction,
    resolve_scripted_bindings,
    select_ambient_clock,
)


def _resolution(outcome: str, actor_id: str = "a1", action_key: str = "study") -> ActionResolution:
    return ActionResolution(
        resolution_id="res1",
        campaign_id="c1",
        actor_id=actor_id,
        action_key=action_key,
        dice_rolled=[3],
        outcome=outcome,  # type: ignore[arg-type]
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


def _room_clock(
    clock_id: str,
    room_id: str = "R1",
    category: str = "danger",
    label: str = "Scorpion Nest Agitated",
    filled: int = 1,
    segments: int = 6,
) -> ClockState:
    return ClockState(
        clock_id=clock_id, campaign_id="c1", label=label, segments=segments,
        filled=filled, clock_level="room", scope_room_id=room_id, category=category,
    )


def _object(policy: str, bindings: list[ObjectReactionBinding] | None = None) -> RoomObject:
    return RoomObject(
        object_id="obj1", campaign_id="c1", room_id="R1", level_id="level-1",
        slug="statue", display_name="Toppled Artificer Statue",
        archetype="lore_fixture", description="A toppled statue.", current_state="idle",
        reaction_policy=policy,  # type: ignore[arg-type]
        reaction_bindings=bindings or [],
    )


# ---------------------------------------------------------------------------
# Phase 51.6 Slice 7 — ambient policy branch (design §4)
# ---------------------------------------------------------------------------

def test_ambient_miss_advances_single_local_adverse_clock_by_one():
    # Worked example: STUDY-miss on the ambient statue in R1 → nest +1.
    actor, tracks = _pc()
    nest = _room_clock("scorpion-nest")
    result = compute_world_reaction(
        _resolution("miss"), [nest], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1",
        acted_object=_object("ambient"),
    )
    assert len(result.clock_lines) == 1
    assert result.clock_lines[0].clock_id == "scorpion-nest"
    assert result.clock_lines[0].ticks == 1
    assert result.clock_lines[0].new_filled == 2


def test_ambient_partial_advances_local_adverse_clock_by_one():
    actor, tracks = _pc()
    nest = _room_clock("scorpion-nest")
    result = compute_world_reaction(
        _resolution("partial"), [nest], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1",
        acted_object=_object("ambient"),
    )
    assert len(result.clock_lines) == 1
    assert result.clock_lines[0].ticks == 1


def test_ambient_no_local_adverse_clock_is_narration_only():
    actor, tracks = _pc()
    elsewhere = _room_clock("scorpion-nest", room_id="R9")
    result = compute_world_reaction(
        _resolution("miss"), [elsewhere], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1",
        acted_object=_object("ambient"),
    )
    assert result.clock_lines == []
    assert result.stress_lines == []


def test_ambient_applies_no_stress():
    # Stress is a scripted consequence only; the ambient path never applies it.
    actor, tracks = _pc()
    nest = _room_clock("scorpion-nest")
    result = compute_world_reaction(
        _resolution("miss"), [nest], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1",
        acted_object=_object("ambient"),
    )
    assert result.stress_lines == []


def test_ambient_full_does_not_advance():
    actor, tracks = _pc()
    nest = _room_clock("scorpion-nest")
    result = compute_world_reaction(
        _resolution("full"), [nest], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1",
        acted_object=_object("ambient"),
    )
    assert result.clock_lines == []


def test_ambient_critical_never_rolls_back():
    # Polarity fix: the ambient path never rolls a clock back.
    actor, tracks = _pc()
    nest = _room_clock("scorpion-nest", filled=3)
    result = compute_world_reaction(
        _resolution("critical"), [nest], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1",
        acted_object=_object("ambient"),
    )
    assert result.clock_lines == []


def test_ambient_firewall_skips_objective_relationship_faction_intimacy():
    # Even locally room-scoped, these categories are never ambient-eligible;
    # only the adverse clock moves. This is the original bug, dead by construction.
    actor, tracks = _pc()
    nest = _room_clock("scorpion-nest", category="danger")
    objective = _room_clock("power-core", category="objective", label="Restore the Power Core")
    intimacy = _room_clock("factory-learns", category="dungeon_intimacy", label="The Factory Learns")
    relationship = _room_clock("mira", category="relationship", label="Mira Surfaces")
    faction = _room_clock("guild", category="faction_pressure", label="Guild Agenda")
    result = compute_world_reaction(
        _resolution("miss"),
        [nest, objective, intimacy, relationship, faction],
        [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1",
        acted_object=_object("ambient"),
    )
    moved = {line.clock_id for line in result.clock_lines}
    assert moved == {"scorpion-nest"}


def test_ambient_blast_radius_cap_is_one_clock():
    # Two adverse room clocks present → exactly one advances (tightest/lowest id).
    actor, tracks = _pc()
    first = _room_clock("aaa-nest")
    second = _room_clock("bbb-swarm")
    result = compute_world_reaction(
        _resolution("miss"), [second, first], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1",
        acted_object=_object("ambient"),
    )
    assert len(result.clock_lines) == 1
    assert result.clock_lines[0].clock_id == "aaa-nest"


def test_no_acted_object_defaults_to_ambient():
    # Non-object actions fall to the ambient rule by default (§7).
    actor, tracks = _pc()
    nest = _room_clock("scorpion-nest")
    result = compute_world_reaction(
        _resolution("miss"), [nest], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1",
    )
    assert len(result.clock_lines) == 1
    assert result.clock_lines[0].ticks == 1
    assert result.stress_lines == []


# ---------------------------------------------------------------------------
# Phase 51.6 Slice 7 — inert policy branch (design §2)
# ---------------------------------------------------------------------------

def test_inert_applies_no_mechanics():
    actor, tracks = _pc()
    nest = _room_clock("scorpion-nest")
    result = compute_world_reaction(
        _resolution("miss"), [nest], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1",
        acted_object=_object("inert"),
    )
    assert result.clock_lines == []
    assert result.stress_lines == []


# ---------------------------------------------------------------------------
# Phase 51.6 Slice 7 — scripted policy branch (design §5)
# ---------------------------------------------------------------------------

def _binding_row(
    verb: str, outcome: str, *, clock_slug: str | None = None, clock_delta: int = 0,
    stress_track: str | None = None, stress_amount: int = 0, binding_id: str = "b1",
) -> ObjectReactionBinding:
    return ObjectReactionBinding(
        binding_id=binding_id, object_id="obj1", action_verb=verb, outcome=outcome,  # type: ignore[arg-type]
        clock_slug=clock_slug, clock_delta=clock_delta,
        stress_track=stress_track, stress_amount=stress_amount,
    )


def test_scripted_applies_only_authored_clock_binding():
    # Scripted fires only its authored binding — no fan-out to the local adverse clock.
    actor, tracks = _pc()
    overload = ClockState(
        clock_id="clock:crucible:arcane-overload-building", campaign_id="c1",
        label="Arcane Overload Building", segments=8, filled=2,
        clock_level="dungeon", category="danger",
    )
    nest = _room_clock("scorpion-nest")  # locally present but NOT authored
    obj = _object("scripted", [
        _binding_row("tinker", "miss", clock_slug="arcane-overload-building", clock_delta=1),
    ])
    result = compute_world_reaction(
        _resolution("miss", action_key="tinker"), [overload, nest], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1", acted_object=obj,
    )
    moved = {line.clock_id for line in result.clock_lines}
    assert moved == {"clock:crucible:arcane-overload-building"}
    assert result.clock_lines[0].ticks == 1
    assert result.clock_lines[0].new_filled == 3


def test_scripted_no_matching_binding_is_no_op():
    actor, tracks = _pc()
    nest = _room_clock("scorpion-nest")
    obj = _object("scripted", [
        _binding_row("tinker", "miss", clock_slug="arcane-overload-building", clock_delta=1),
    ])
    result = compute_world_reaction(
        _resolution("miss", action_key="study"), [nest], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1", acted_object=obj,
    )
    assert result.clock_lines == []
    assert result.stress_lines == []


def test_scripted_applies_authored_stress_to_acting_actor():
    actor, tracks = _pc()
    tracks["body"] = StressTrack(track_key="body", capacity=4, filled=0)
    obj = _object("scripted", [
        _binding_row("move", "miss", stress_track="body", stress_amount=2),
    ])
    result = compute_world_reaction(
        _resolution("miss", action_key="move"), [], [(actor, tracks)],
        current_room_id="R5", current_level_id="level-1", acted_object=obj,
    )
    assert len(result.stress_lines) == 1
    assert result.stress_lines[0].track_key == "body"
    assert result.stress_lines[0].amount == 2
    assert result.stress_lines[0].new_filled == 2


def test_scripted_never_moves_dungeon_intimacy_clock():
    # D5 by construction: even an authored binding cannot move dungeon_intimacy.
    actor, tracks = _pc()
    intimacy = ClockState(
        clock_id="clock:crucible:factory-learns", campaign_id="c1",
        label="The Factory Learns What You Fear", segments=4, filled=1,
        clock_level="dungeon", category="dungeon_intimacy",
    )
    obj = _object("scripted", [
        _binding_row("sense", "miss", clock_slug="factory-learns", clock_delta=2),
    ])
    result = compute_world_reaction(
        _resolution("miss", action_key="sense"), [intimacy], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1", acted_object=obj,
    )
    assert result.clock_lines == []


def test_scripted_full_outcome_is_no_op():
    actor, tracks = _pc()
    overload = ClockState(
        clock_id="clock:crucible:arcane-overload-building", campaign_id="c1",
        label="Arcane Overload Building", segments=8, filled=2, category="danger",
    )
    obj = _object("scripted", [
        _binding_row("tinker", "miss", clock_slug="arcane-overload-building", clock_delta=1),
    ])
    result = compute_world_reaction(
        _resolution("full", action_key="tinker"), [overload], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1", acted_object=obj,
    )
    assert result.clock_lines == []


def test_scripted_partial_falls_back_to_half_miss():
    actor, tracks = _pc()
    overload = ClockState(
        clock_id="clock:crucible:arcane-overload-building", campaign_id="c1",
        label="Arcane Overload Building", segments=8, filled=2, category="danger",
    )
    obj = _object("scripted", [
        _binding_row("tinker", "miss", clock_slug="arcane-overload-building", clock_delta=2),
    ])
    result = compute_world_reaction(
        _resolution("partial", action_key="tinker"), [overload], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1", acted_object=obj,
    )
    assert len(result.clock_lines) == 1
    assert result.clock_lines[0].ticks == 1  # half of 2


# ---------------------------------------------------------------------------
# Phase 51.6 Slice 7 — summary lines still generated
# ---------------------------------------------------------------------------

def test_ambient_miss_produces_summary_lines():
    actor, tracks = _pc()
    nest = _room_clock("scorpion-nest")
    result = compute_world_reaction(
        _resolution("miss"), [nest], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1",
        acted_object=_object("ambient"),
    )
    assert result.summary_lines[0] == "World reaction (MISS):"
    assert "Clock [Scorpion Nest Agitated]:" in " ".join(result.summary_lines)


def test_narration_only_reaction_reports_no_consequences():
    actor, tracks = _pc()
    result = compute_world_reaction(
        _resolution("miss"), [], [(actor, tracks)],
        current_room_id="R1", current_level_id="level-1",
        acted_object=_object("ambient"),
    )
    assert any("No world consequences." in line for line in result.summary_lines)


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
