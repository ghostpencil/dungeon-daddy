from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository


@dataclass
class DiscoverResult:
    accepted: bool
    rejection_reason: str | None = None
    events: list[DomainEvent] = field(default_factory=list)


def discover_exit(
    exit_id: str,
    campaign_id: str,
    memory_title: str,
    repo: MemoryRepository,
) -> DiscoverResult:
    row = repo.get_exit_by_id(exit_id)
    if row is None:
        return DiscoverResult(accepted=False, rejection_reason=f"Unknown exit: {exit_id}")

    if row["status"] != "hidden":
        return DiscoverResult(
            accepted=False,
            rejection_reason=f"Exit is not hidden (status={row['status']}): {exit_id}",
        )

    repo.update_exit_status(exit_id, "discovered")

    repo.save_memory_entry(
        memory_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        entry_type="discovery",
        title=memory_title,
        status="approved",
    )

    event = DomainEvent(
        event_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        event_type="exit.discovered",
        payload={"exit_id": exit_id},
    )

    return DiscoverResult(accepted=True, events=[event])


def passive_hidden_exit_hint(
    campaign_id: str,
    room_id: str,
    repo: MemoryRepository,
) -> int:
    """Return count of hidden exits if any PC has sense >= 2, else 0."""
    actors = repo.get_actors_by_campaign(campaign_id)
    for actor in actors:
        if actor["actor_type"] != "pc":
            continue
        ratings = repo.get_actor_action_ratings(actor["actor_id"])
        for r in ratings:
            if r["action_key"] == "sense" and r["rating"] >= 2:
                return repo.get_hidden_exit_count(campaign_id, room_id)
    return 0
