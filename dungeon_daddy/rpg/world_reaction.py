"""Deterministic world reaction rules — Phase 35."""
from __future__ import annotations

import uuid

from dungeon_daddy.rpg.models import (
    ActionResolution,
    ActorState,
    ClockState,
    ReactionClockLine,
    ReactionStressLine,
    StressTrack,
    WorldReaction,
)

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


def compute_world_reaction(
    resolution: ActionResolution,
    threat_clocks: list[ClockState],
    pc_actors: list[tuple[ActorState, dict[str, StressTrack]]],
    current_room_id: str | None = None,
) -> WorldReaction:
    """Map an action resolution to deterministic world consequences."""
    outcome = resolution.outcome
    clock_ticks = _CLOCK_TICKS[outcome]
    stress_amount = _STRESS_AMOUNT[outcome]

    clock_lines: list[ReactionClockLine] = []
    for clock in threat_clocks:
        if clock.status != "active":
            continue
        if clock.scope_room_id is not None and clock.scope_room_id != current_room_id:
            continue
        if clock.action_tags and resolution.action_key not in clock.action_tags:
            continue
        new_filled = max(0, min(clock.segments, clock.filled + clock_ticks))
        new_status = "completed" if new_filled >= clock.segments else "active"
        if clock_ticks == 0:
            continue
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
        for actor, tracks in pc_actors:
            if actor.actor_id != resolution.actor_id:
                continue
            track = tracks.get("body", StressTrack(track_key="body"))
            new_filled = min(track.capacity, track.filled + stress_amount)
            triggered_fallout = new_filled >= track.capacity
            stress_lines.append(ReactionStressLine(
                actor_id=actor.actor_id,
                display_name=actor.display_name,
                track_key="body",
                amount=stress_amount,
                new_filled=new_filled,
                triggered_fallout=triggered_fallout,
                reason=f"{outcome} consequence",
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
