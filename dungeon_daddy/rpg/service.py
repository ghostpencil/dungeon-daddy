from __future__ import annotations

import uuid
from typing import Literal

from dungeon_daddy.rpg.actions import resolve_action
from dungeon_daddy.rpg.clocks import advance_clock, create_clock
from dungeon_daddy.rpg.stress import create_default_stress_tracks, is_track_filled, mark_stress
from dungeon_daddy.rpg.world_reaction import compute_world_reaction
from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import (
    ActionRequest,
    ActionResolution,
    ActorState,
    ClockState,
    RoomObject,
    StressTrack,
    WorldReaction,
)


class RpgService:
    def create_actor(
        self,
        campaign_id: str,
        actor_type: Literal["pc", "npc", "monster", "dungeon"],
        slug: str,
        display_name: str,
        concept: str | None = None,
    ) -> ActorState:
        tracks = create_default_stress_tracks() if actor_type == "pc" else {}
        return ActorState(
            actor_id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            actor_type=actor_type,
            slug=slug,
            display_name=display_name,
            concept=concept,
            stress=tracks,
        )

    def resolve_action(
        self,
        request: ActionRequest,
        fixed: list[int] | None = None,
    ) -> tuple[ActionResolution, DomainEvent]:
        resolution = resolve_action(request, fixed=fixed)
        event = DomainEvent(
            event_id=str(uuid.uuid4()),
            campaign_id=request.campaign_id,
            event_type="action.resolved",
            payload=resolution.model_dump(),
        )
        return resolution, event

    def advance_clock(
        self,
        clock: ClockState,
        ticks: int,
    ) -> tuple[ClockState, DomainEvent]:
        updated = advance_clock(clock, ticks=ticks)
        event = DomainEvent(
            event_id=str(uuid.uuid4()),
            campaign_id=clock.campaign_id,
            event_type="clock.advanced",
            payload=updated.model_dump(),
        )
        return updated, event

    def react_to_resolution(
        self,
        resolution: ActionResolution,
        threat_clocks: list[ClockState],
        pc_actors: list[tuple[ActorState, dict[str, StressTrack]]],
        current_room_id: str | None = None,
        current_level_id: str | None = None,
        acted_object: RoomObject | None = None,
    ) -> tuple[WorldReaction, DomainEvent]:
        reaction = compute_world_reaction(
            resolution, threat_clocks, pc_actors,
            current_room_id=current_room_id,
            current_level_id=current_level_id,
            acted_object=acted_object,
        )
        event = DomainEvent(
            event_id=str(uuid.uuid4()),
            campaign_id=resolution.campaign_id,
            event_type="world.reacted",
            payload=reaction.model_dump(),
        )
        return reaction, event

    def apply_stress(
        self,
        actor_id: str,
        campaign_id: str,
        track: StressTrack,
        amount: int = 1,
    ) -> tuple[StressTrack, DomainEvent]:
        updated = mark_stress(track, amount=amount)
        event = DomainEvent(
            event_id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            event_type="stress.marked",
            payload={
                "actor_id": actor_id,
                "track_key": updated.track_key,
                "filled": updated.filled,
                "needs_fallout": is_track_filled(updated),
            },
        )
        return updated, event


def refresh_kits(repo: MemoryRepository, actor_id: str) -> list[str]:
    """Set charges_current = charges_max for the actor's active class_kit items."""
    refreshed: list[str] = []
    for item in repo.get_items_by_actor(actor_id):
        if item["item_type"] == "class_kit" and item["status"] == "active":
            repo.update_item_charges(item["item_id"], item["charges_max"])
            refreshed.append(item["item_id"])
    return refreshed


def mark_level_items_inert(
    repo: MemoryRepository,
    campaign_id: str,
    level_id: str,
) -> list[str]:
    """Set status='inert' for all active items bound to the given level."""
    affected: list[str] = []
    for item in repo.get_items(campaign_id):
        if item["level_id"] == level_id and item["status"] == "active":
            repo.update_item_status(item["item_id"], "inert")
            affected.append(item["item_id"])
    return affected


def compute_effective_ratings(
    actor_id: str,
    base_ratings: dict[str, int],
    repo: MemoryRepository,
) -> dict[str, int]:
    """Return base action ratings plus modifiers from the actor's equipped gear features."""
    effective = dict(base_ratings)
    for item in repo.get_items_by_actor(actor_id):
        if item["item_type"] == "equipped_gear" and item.get("is_equipped"):
            for feature in item.get("features", []):
                if feature["feature_type"] == "rating_modifier":
                    key = feature["action_key"]
                    effective[key] = effective.get(key, 0) + feature["modifier"]
    return effective
