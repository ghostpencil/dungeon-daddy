from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository


@dataclass
class ExitActionResult:
    accepted: bool
    rejection_reason: str | None = None
    events: list[DomainEvent] = field(default_factory=list)


def unlock_exit(
    exit_id: str,
    campaign_id: str,
    repo: MemoryRepository,
) -> ExitActionResult:
    row = repo.get_exit_by_id(exit_id)
    if row is None:
        return ExitActionResult(accepted=False, rejection_reason=f"Unknown exit: {exit_id}")

    if row["status"] != "locked":
        return ExitActionResult(
            accepted=False,
            rejection_reason=f"Exit is not locked (status={row['status']}): {exit_id}",
        )

    repo.update_exit_status(exit_id, "open")

    event = DomainEvent(
        event_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        event_type="exit.unlocked",
        payload={"exit_id": exit_id},
    )

    return ExitActionResult(accepted=True, events=[event])


def clear_exit_key_requirement(
    exit_id: str,
    campaign_id: str,
    repo: MemoryRepository,
) -> ExitActionResult:
    row = repo.get_exit_by_id(exit_id)
    if row is None:
        return ExitActionResult(accepted=False, rejection_reason=f"Unknown exit: {exit_id}")

    repo.update_exit_requires_item_slug(exit_id, None)

    event = DomainEvent(
        event_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        event_type="exit.key_requirement_cleared",
        payload={"exit_id": exit_id},
    )

    return ExitActionResult(accepted=True, events=[event])


def seal_exit(
    exit_id: str,
    campaign_id: str,
    repo: MemoryRepository,
) -> ExitActionResult:
    row = repo.get_exit_by_id(exit_id)
    if row is None:
        return ExitActionResult(accepted=False, rejection_reason=f"Unknown exit: {exit_id}")

    if row["status"] != "one_way":
        return ExitActionResult(
            accepted=False,
            rejection_reason=f"Exit is not one_way (status={row['status']}): {exit_id}",
        )

    repo.update_exit_status(exit_id, "sealed")

    event = DomainEvent(
        event_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        event_type="exit.sealed",
        payload={"exit_id": exit_id},
    )

    return ExitActionResult(accepted=True, events=[event])
