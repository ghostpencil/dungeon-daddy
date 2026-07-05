"""Deterministic world reaction rules — Phase 35."""
from __future__ import annotations

import dataclasses
import uuid

from dungeon_daddy.rpg.models import (
    ActionResolution,
    ActorState,
    ClockState,
    ObjectReactionBinding,
    ReactionClockLine,
    ReactionStressLine,
    StressTrack,
    WorldReaction,
    is_adverse,
    normalize_clock_category,
)
from dungeon_daddy.rpg.stress_routing import choose_stress_track

_CLOCK_TICKS: dict[str, int] = {
    "miss": 2,
    "partial": 1,
    "full": 0,
    "critical": -1,
}

_STRESS_AMOUNT: dict[str, int] = {
    "miss": 2,
    "partial": 1,
    "full": 0,
    "critical": 0,
}


def select_ambient_clock(
    active_clocks: list[ClockState],
    room_id: str | None,
    level_id: str | None,
) -> ClockState | None:
    """Pick the single tightest-scoped active adverse clock local to the party.

    Phase 51.6 ambient tier (design §4): gather active adverse
    (danger/pursuit/ritual) clocks whose scope covers the party's current room
    or level, then return the tightest-scoped one — room beats level, ties
    broken by lowest ``clock_id``. Dungeon/quest/character/faction-scoped clocks
    are not ambient-eligible (they move only via scripted bindings). Ignores
    ``action_tags`` entirely; the caller advances the returned clock by +1.
    Returns ``None`` when no local adverse clock exists — the caller then
    applies no mechanical consequence (narration only).
    """
    room_scoped: list[ClockState] = []
    level_scoped: list[ClockState] = []
    for clock in active_clocks:
        if clock.status != "active":
            continue
        if not is_adverse(normalize_clock_category(clock.category)):
            continue
        if (clock.clock_level == "room"
                and clock.scope_room_id is not None
                and clock.scope_room_id == room_id):
            room_scoped.append(clock)
        elif (clock.clock_level == "level"
                and clock.level_id is not None
                and clock.level_id == level_id):
            level_scoped.append(clock)

    pool = room_scoped or level_scoped
    if not pool:
        return None
    return min(pool, key=lambda c: c.clock_id)


@dataclasses.dataclass(frozen=True)
class Consequence:
    """A resolved scripted world-reaction effect (Phase 51.6 §5).

    The applied effect portion of an :class:`ObjectReactionBinding` — after
    verb/outcome matching and any partial-fallback scaling. May advance a clock,
    apply stress, or both.
    """

    clock_slug: str | None
    clock_delta: int
    stress_track: str | None
    stress_amount: int


def _binding_matches_verb(binding: ObjectReactionBinding, verb: str) -> bool:
    return binding.action_verb == verb or binding.action_verb == "*"


def _half_magnitude(value: int) -> int:
    """Halve toward zero, rounding down, but keep a nonzero value at least 1."""
    if value == 0:
        return 0
    sign = 1 if value > 0 else -1
    return sign * max(1, abs(value) // 2)


def _consequence(binding: ObjectReactionBinding, *, scale_half: bool = False) -> Consequence:
    if scale_half:
        return Consequence(
            clock_slug=binding.clock_slug,
            clock_delta=_half_magnitude(binding.clock_delta),
            stress_track=binding.stress_track,
            stress_amount=_half_magnitude(binding.stress_amount),
        )
    return Consequence(
        clock_slug=binding.clock_slug,
        clock_delta=binding.clock_delta,
        stress_track=binding.stress_track,
        stress_amount=binding.stress_amount,
    )


def resolve_scripted_bindings(
    bindings: list[ObjectReactionBinding],
    verb: str,
    outcome: str,
) -> list[Consequence]:
    """Resolve a `scripted` object's authored bindings for a verb × outcome.

    Phase 51.6 (design §5/§9): match bindings whose ``action_verb`` equals
    ``verb`` (or the ``"*"`` wildcard) and whose ``outcome`` matches. A
    ``partial`` outcome with no authored partial row falls back to the object's
    matching ``miss`` binding at **half magnitude, rounded down** (min 1 when the
    miss binding is nonzero). Returns an empty list when nothing matches — no
    fan-out to unrelated clocks.
    """
    matched = [
        b for b in bindings
        if b.outcome == outcome and _binding_matches_verb(b, verb)
    ]
    if matched:
        return [_consequence(b) for b in matched]
    if outcome == "partial":
        miss = [
            b for b in bindings
            if b.outcome == "miss" and _binding_matches_verb(b, verb)
        ]
        return [_consequence(b, scale_half=True) for b in miss]
    return []


def compute_world_reaction(
    resolution: ActionResolution,
    threat_clocks: list[ClockState],
    pc_actors: list[tuple[ActorState, dict[str, StressTrack]]],
    current_room_id: str | None = None,
    current_level_id: str | None = None,
) -> WorldReaction:
    """Map an action resolution to deterministic world consequences."""
    outcome = resolution.outcome
    clock_ticks = _CLOCK_TICKS[outcome]
    stress_amount = _STRESS_AMOUNT[outcome]

    clock_lines: list[ReactionClockLine] = []
    matched_clocks: list[ClockState] = []
    for clock in threat_clocks:
        if clock.status != "active":
            continue
        if clock.scope_room_id is not None and clock.scope_room_id != current_room_id:
            continue
        if (clock.level_id is not None and current_level_id is not None
                and clock.level_id != current_level_id):
            continue
        if clock.action_tags and resolution.action_key not in clock.action_tags:
            continue
        new_filled = max(0, min(clock.segments, clock.filled + clock_ticks))
        new_status = "completed" if new_filled >= clock.segments else "active"
        if clock_ticks == 0:
            continue
        matched_clocks.append(clock)
        clock_lines.append(ReactionClockLine(
            clock_id=clock.clock_id,
            label=clock.label,
            ticks=clock_ticks,
            new_filled=new_filled,
            new_status=new_status,
            reason=outcome,
        ))

    stress_lines: list[ReactionStressLine] = []
    if stress_amount > 0:
        track_key = choose_stress_track(
            action_key=resolution.action_key,
            intent=resolution.intent,
            matched_clocks=matched_clocks,
        )
        for actor, tracks in pc_actors:
            if actor.actor_id != resolution.actor_id:
                continue
            track = tracks.get(track_key, StressTrack(track_key=track_key))
            new_filled = min(track.capacity, track.filled + stress_amount)
            triggered_fallout = new_filled >= track.capacity
            stress_lines.append(ReactionStressLine(
                actor_id=actor.actor_id,
                display_name=actor.display_name,
                track_key=track_key,
                amount=stress_amount,
                new_filled=new_filled,
                triggered_fallout=triggered_fallout,
                reason=f"{outcome} consequence — {track_key}",
            ))

    summary_lines = _build_summary(outcome, clock_lines, stress_lines)

    return WorldReaction(
        reaction_id=str(uuid.uuid4()),
        campaign_id=resolution.campaign_id,
        source_resolution_id=resolution.resolution_id,
        outcome=outcome,
        clock_lines=clock_lines,
        stress_lines=stress_lines,
        summary_lines=summary_lines,
    )


def _build_summary(
    outcome: str,
    clock_lines: list[ReactionClockLine],
    stress_lines: list[ReactionStressLine],
) -> list[str]:
    lines: list[str] = [f"World reaction ({outcome.upper()}):"]
    for cl in clock_lines:
        direction = "+" if cl.ticks > 0 else ""
        lines.append(
            f"  Clock [{cl.label}]: {cl.new_filled - cl.ticks}→{cl.new_filled}"
            f" ({direction}{cl.ticks})"
            + (" COMPLETED" if cl.new_status == "completed" else "")
        )
    for sl in stress_lines:
        lines.append(
            f"  {sl.display_name} [{sl.track_key}]: {sl.new_filled - sl.amount}→{sl.new_filled}"
            + (" — FALLOUT" if sl.triggered_fallout else "")
        )
    if not clock_lines and not stress_lines:
        lines.append("  No world consequences.")
    return lines
