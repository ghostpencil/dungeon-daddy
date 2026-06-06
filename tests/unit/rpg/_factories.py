"""Shared model factories for RPG unit tests."""
from __future__ import annotations

from dungeon_daddy.rpg.models import ActorState, StressTrack


def make_pc(
    actor_id: str = "pc_1",
    campaign_id: str = "camp_1",
    *,
    body: int = 0,
    composure: int = 0,
    bonds: int = 0,
    weird: int = 0,
) -> ActorState:
    return ActorState(
        actor_id=actor_id,
        campaign_id=campaign_id,
        actor_type="pc",
        slug="hero",
        display_name="Hero",
        stress={
            "body":      StressTrack(track_key="body",      capacity=4, filled=body),
            "composure": StressTrack(track_key="composure", capacity=4, filled=composure),
            "bonds":     StressTrack(track_key="bonds",     capacity=4, filled=bonds),
            "weird":     StressTrack(track_key="weird",     capacity=4, filled=weird),
        },
    )
