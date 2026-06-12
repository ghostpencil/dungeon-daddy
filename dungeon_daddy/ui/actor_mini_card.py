from __future__ import annotations

from dataclasses import dataclass, field

from dungeon_daddy.rpg.models import ActorState


@dataclass
class ActorMiniCardData:
    actor_name: str
    stress_summary: list[tuple[str, int, int]] = field(default_factory=list)
    has_fallout: bool = False
    actions: dict[str, int] = field(default_factory=dict)


def build_actor_mini_card(actor: ActorState) -> ActorMiniCardData:
    summary = [
        (track.track_key, track.filled, track.capacity)
        for track in actor.stress.values()
    ]
    has_fallout = any(track.filled >= track.capacity for track in actor.stress.values())
    return ActorMiniCardData(
        actor_name=actor.display_name,
        stress_summary=summary,
        has_fallout=has_fallout,
        actions=dict(actor.actions),
    )
