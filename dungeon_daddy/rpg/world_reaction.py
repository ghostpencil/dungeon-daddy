"""Deterministic world reaction rules — Phase 51.6 (World Reaction Policy).

Supersedes the Phase 35 tag fan-out: a miss/partial now reacts per the acted-upon
object's ``reaction_policy`` (ambient / scripted / inert), not by matching action
tags against every clock.
"""
from __future__ import annotations

import dataclasses
import logging
import uuid

from dungeon_daddy.rpg.models import (
    ActionResolution,
    ActorState,
    ClockState,
    ObjectReactionBinding,
    ReactionClockLine,
    ReactionStressLine,
    RoomObject,
    StressTrack,
    WorldReaction,
    is_adverse,
    normalize_clock_category,
)
from dungeon_daddy.rpg.seed_pack import derive_clock_id

_log = logging.getLogger(__name__)

# Outcomes on which the ambient path advances its selected clock by +1. Full is
# a no-op (success flows through transitions/objectives) and critical never
# rolls a clock back — the ambient path only ever moves adverse pressure forward.
_AMBIENT_TICK_OUTCOMES: frozenset[str] = frozenset({"miss", "partial"})


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


def _advance_clock_line(clock: ClockState, ticks: int, reason: str) -> ReactionClockLine:
    new_filled = max(0, min(clock.segments, clock.filled + ticks))
    new_status = "completed" if new_filled >= clock.segments else "active"
    return ReactionClockLine(
        clock_id=clock.clock_id,
        label=clock.label,
        ticks=ticks,
        new_filled=new_filled,
        new_status=new_status,
        reason=reason,
    )


def _find_clock_by_slug(clocks: list[ClockState], slug: str) -> ClockState | None:
    """Resolve a binding's ``clock_slug`` to a live clock.

    Two id conventions exist in the wild: ``campaign.seeder._clock_id`` writes the
    string form ``clock:{campaign}:{slug}`` (matched on the suffix), while
    ``rpg.seed_pack.derive_clock_id`` — the path that actually seeded the live
    Crucible — writes ``uuid5(campaign_slug:slug)``. We match both, or every
    scripted CLOCK binding silently no-ops on a seed-pack save. A bare
    ``clock_id == slug`` is also accepted for tests/unseeded data.
    """
    for clock in clocks:
        if clock.clock_id == slug or clock.clock_id.endswith(f":{slug}"):
            return clock
        campaign_slug = clock.campaign_id.split(":")[-1]
        if clock.clock_id == derive_clock_id(campaign_slug, slug):
            return clock
    return None


def _apply_stress_lines(
    resolution: ActionResolution,
    pc_actors: list[tuple[ActorState, dict[str, StressTrack]]],
    track_key: str,
    amount: int,
) -> list[ReactionStressLine]:
    lines: list[ReactionStressLine] = []
    for actor, tracks in pc_actors:
        if actor.actor_id != resolution.actor_id:
            continue
        track = tracks.get(track_key, StressTrack(track_key=track_key))
        new_filled = min(track.capacity, track.filled + amount)
        lines.append(ReactionStressLine(
            actor_id=actor.actor_id,
            display_name=actor.display_name,
            track_key=track_key,
            amount=amount,
            new_filled=new_filled,
            triggered_fallout=new_filled >= track.capacity,
            reason=f"{resolution.outcome} consequence — {track_key}",
        ))
    return lines


def _ambient_consequences(
    resolution: ActionResolution,
    threat_clocks: list[ClockState],
    current_room_id: str | None,
    current_level_id: str | None,
) -> tuple[list[ReactionClockLine], list[ReactionStressLine]]:
    """Ambient path (design §4): +1 on the single tightest-scoped local adverse clock.

    Only miss/partial react; no stress; the blast radius is capped at one clock by
    ``select_ambient_clock`` returning at most one. Returns ``([], [])`` when no
    local adverse clock exists (narration only).
    """
    if resolution.outcome not in _AMBIENT_TICK_OUTCOMES:
        return [], []
    clock = select_ambient_clock(threat_clocks, current_room_id, current_level_id)
    if clock is None:
        return [], []
    return [_advance_clock_line(clock, 1, reason=resolution.outcome)], []


def _scripted_consequences(
    resolution: ActionResolution,
    threat_clocks: list[ClockState],
    pc_actors: list[tuple[ActorState, dict[str, StressTrack]]],
    bindings: list[ObjectReactionBinding],
) -> tuple[list[ReactionClockLine], list[ReactionStressLine]]:
    """Scripted path (design §5): apply only the object's authored bindings.

    No tag fan-out. ``dungeon_intimacy`` is never moved here even if a binding
    names it — D5 says it moves only via the objective service (firewall by
    construction). Stress is authored on the binding, not inferred.
    """
    clock_lines: list[ReactionClockLine] = []
    stress_lines: list[ReactionStressLine] = []
    for cons in resolve_scripted_bindings(
        bindings, resolution.action_key, resolution.outcome
    ):
        if cons.clock_slug is not None and cons.clock_delta != 0:
            clock = _find_clock_by_slug(threat_clocks, cons.clock_slug)
            if clock is None:
                _log.warning(
                    "Scripted reaction binding names unresolved clock slug %r "
                    "(action=%s outcome=%s) — no clock advanced.",
                    cons.clock_slug, resolution.action_key, resolution.outcome,
                )
            elif clock.status != "active":
                # A completed/paused clock is a legitimate runtime state, not an
                # authoring error — stay quiet.
                pass
            elif normalize_clock_category(clock.category) == "dungeon_intimacy":
                _log.warning(
                    "Scripted reaction binding names dungeon_intimacy clock %r — "
                    "the D5 firewall skips it; advance it via the objective service.",
                    cons.clock_slug,
                )
            else:
                clock_lines.append(
                    _advance_clock_line(clock, cons.clock_delta, reason=resolution.outcome)
                )
        if cons.stress_track is not None and cons.stress_amount != 0:
            stress_lines.extend(
                _apply_stress_lines(resolution, pc_actors, cons.stress_track, cons.stress_amount)
            )
    return clock_lines, stress_lines


def compute_world_reaction(
    resolution: ActionResolution,
    threat_clocks: list[ClockState],
    pc_actors: list[tuple[ActorState, dict[str, StressTrack]]],
    current_room_id: str | None = None,
    current_level_id: str | None = None,
    acted_object: RoomObject | None = None,
) -> WorldReaction:
    """Map an action resolution to deterministic world consequences (Phase 51.6).

    Branches on the acted-upon object's ``reaction_policy`` (design §2/§7):

    - ``scripted`` → only the object's authored ``reaction_bindings`` fire.
    - ``ambient`` → at most one tick on the nearest local adverse clock (§4).
    - ``inert`` → no mechanics (pure flavor).

    A non-object action (``acted_object is None``) falls to the ambient rule by
    default. The clock-category firewall (§3) is enforced by construction: the
    ambient path only ever touches adverse, locally-scoped clocks, and the
    scripted path never moves ``dungeon_intimacy`` (D5).
    """
    outcome = resolution.outcome
    policy = acted_object.reaction_policy if acted_object is not None else "ambient"

    if policy == "scripted":
        bindings = acted_object.reaction_bindings if acted_object is not None else []
        clock_lines, stress_lines = _scripted_consequences(
            resolution, threat_clocks, pc_actors, bindings
        )
    elif policy == "inert":
        clock_lines, stress_lines = [], []
    else:  # ambient (default; also all non-object actions)
        clock_lines, stress_lines = _ambient_consequences(
            resolution, threat_clocks, current_room_id, current_level_id
        )

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
