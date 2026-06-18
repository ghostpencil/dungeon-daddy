from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.command import ConsumeItem, ConsumeKitCharge, EquipItem, GiveItem, PlayerCommand, TakeItem, UnequipItem

_log = logging.getLogger(__name__)


@dataclass
class CommandValidationResult:
    accepted: bool = False
    rejection_reason: str | None = None
    rejection_events: list[DomainEvent] = field(default_factory=list)


def validate_command(
    command: PlayerCommand,
    repo: MemoryRepository,
    campaign_id: str,
) -> CommandValidationResult:
    result = CommandValidationResult()

    if isinstance(command, ConsumeKitCharge):
        items = repo.get_items(campaign_id)
        item = next((i for i in items if i["item_id"] == command.item_id), None)

        if item is None:
            reason: str | None = f"Unknown item: {command.item_id}"
        elif item["item_type"] != "class_kit":
            reason = f"Item is not a class_kit: {command.item_id}"
        elif item["status"] != "active":
            reason = f"Item is not active: {command.item_id}"
        elif (item.get("charges_current") or 0) <= 0:
            reason = f"No charges remaining: {command.item_id}"
        else:
            reason = None

        if reason is not None:
            _log.info("Command rejected [%s]: %s", command.kind, reason)
            result.rejection_reason = reason
            result.rejection_events.append(
                DomainEvent(
                    event_id=str(uuid.uuid4()),
                    campaign_id=campaign_id,
                    event_type="command.rejected",
                    payload={"kind": command.kind, "reason": reason},
                )
            )
        else:
            result.accepted = True

    elif isinstance(command, ConsumeItem):
        items = repo.get_items(campaign_id)
        item = next((i for i in items if i["item_id"] == command.item_id), None)

        if item is None:
            reason = f"Unknown item: {command.item_id}"
        elif item["status"] != "active":
            reason = f"Item is not active: {command.item_id}"
        else:
            reason = None

        if reason is not None:
            _log.info("Command rejected [%s]: %s", command.kind, reason)
            result.rejection_reason = reason
            result.rejection_events.append(
                DomainEvent(
                    event_id=str(uuid.uuid4()),
                    campaign_id=campaign_id,
                    event_type="command.rejected",
                    payload={"kind": command.kind, "reason": reason},
                )
            )
        else:
            result.accepted = True

    elif isinstance(command, GiveItem):
        items = repo.get_items(campaign_id)
        item = next((i for i in items if i["item_id"] == command.item_id), None)
        target = repo.get_actor(command.to_actor_id)

        if item is None:
            reason = f"Unknown item: {command.item_id}"
        elif target is None:
            reason = f"Unknown target actor: {command.to_actor_id}"
        elif target.get("actor_type") != "pc":
            reason = f"Target actor is not a player character: {command.to_actor_id}"
        else:
            target_items = repo.get_items_by_actor(command.to_actor_id)
            dungeon_item_count = sum(
                1 for i in target_items if i["item_type"] == "dungeon_item" and i["status"] == "active"
            )
            if dungeon_item_count >= 10:
                reason = f"Target actor is at the dungeon item cap (10): {command.to_actor_id}"
            else:
                reason = None

        if reason is not None:
            _log.info("Command rejected [%s]: %s", command.kind, reason)
            result.rejection_reason = reason
            result.rejection_events.append(
                DomainEvent(
                    event_id=str(uuid.uuid4()),
                    campaign_id=campaign_id,
                    event_type="command.rejected",
                    payload={"kind": command.kind, "reason": reason},
                )
            )
        else:
            result.accepted = True

    elif isinstance(command, TakeItem):
        items = repo.get_items(campaign_id)
        item = next((i for i in items if i["item_id"] == command.item_id), None)

        if item is None:
            reason = f"Unknown item: {command.item_id}"
        elif not item.get("owner_actor_id"):
            reason = f"Item has no owner: {command.item_id}"
        else:
            reason = None

        if reason is not None:
            _log.info("Command rejected [%s]: %s", command.kind, reason)
            result.rejection_reason = reason
            result.rejection_events.append(
                DomainEvent(
                    event_id=str(uuid.uuid4()),
                    campaign_id=campaign_id,
                    event_type="command.rejected",
                    payload={"kind": command.kind, "reason": reason},
                )
            )
        else:
            result.accepted = True

    elif isinstance(command, (EquipItem, UnequipItem)):
        items = repo.get_items(campaign_id)
        item = next((i for i in items if i["item_id"] == command.item_id), None)

        if item is None:
            reason = f"Unknown item: {command.item_id}"
        elif item["item_type"] != "equipped_gear":
            reason = f"Item is not equipped_gear: {command.item_id}"
        elif item["status"] != "active":
            reason = f"Item is not active: {command.item_id}"
        elif not item.get("owner_actor_id"):
            reason = f"Item has no owner: {command.item_id}"
        else:
            reason = None

        if reason is not None:
            _log.info("Command rejected [%s]: %s", command.kind, reason)
            result.rejection_reason = reason
            result.rejection_events.append(
                DomainEvent(
                    event_id=str(uuid.uuid4()),
                    campaign_id=campaign_id,
                    event_type="command.rejected",
                    payload={"kind": command.kind, "reason": reason},
                )
            )
        else:
            result.accepted = True

    return result
