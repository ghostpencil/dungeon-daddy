"""Formatting for the mechanical result chat bubble (Phase 38.6)."""
from __future__ import annotations

from dungeon_daddy.rpg.models import ActionResolution, WorldReaction

_OUTCOME_LABELS: dict[str, str] = {
    "critical": "Critical Success",
    "full": "Full Success",
    "partial": "Partial Success",
    "miss": "Miss",
}


def format_mechanical_bubble(
    actor_name: str,
    action_key: str,
    resolution: ActionResolution,
    reaction: WorldReaction | None = None,
) -> str:
    """Return a multiline mechanical summary for the chat panel."""
    outcome_label = _OUTCOME_LABELS.get(resolution.outcome, resolution.outcome.title())
    best_die = max(resolution.dice_rolled) if resolution.dice_rolled else 0
    header = f"{actor_name} rolls {action_key.upper()} — {outcome_label} [{best_die}]"

    lines = [header]
    if reaction is not None:
        reaction_lines: list[str] = []
        for cl in reaction.clock_lines:
            if cl.ticks > 0:
                reaction_lines.append(f"- {cl.label} +{cl.ticks}")
        for sl in reaction.stress_lines:
            if sl.amount > 0:
                reaction_lines.append(f"- {sl.display_name} {sl.track_key} +{sl.amount}")
        if reaction_lines:
            lines.append("World Reaction:")
            lines.extend(reaction_lines)

    return "\n".join(lines)
