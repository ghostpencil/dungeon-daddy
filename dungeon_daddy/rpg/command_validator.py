from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.command import ActivateObject, ConsumeItem, ConsumeKitCharge, DropItem, EquipItem, GiveItem, PickUpItem, PlayerCommand, TakeItem, UnequipItem

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

    elif isinstance(command, PickUpItem):
        items = repo.get_items(campaign_id)
        item = next((i for i in items if i["item_id"] == command.item_id), None)
        actor = repo.get_actor(command.actor_id)

        if item is None:
            reason = f"Unknown item: {command.item_id}"
        elif item["item_type"] != "dungeon_item":
            reason = f"Item is not a dungeon_item: {command.item_id}"
        elif item["status"] != "active":
            reason = f"Item is not active: {command.item_id}"
        elif item.get("owner_actor_id") is not None:
            reason = f"Item is already owned: {command.item_id}"
        elif actor is None:
            reason = f"Unknown actor: {command.actor_id}"
        elif actor.get("actor_type") != "pc":
            reason = f"Actor is not a player character: {command.actor_id}"
        else:
            actor_items = repo.get_items_by_actor(command.actor_id)
            dungeon_item_count = sum(
                1 for i in actor_items if i["item_type"] == "dungeon_item" and i["status"] == "active"
            )
            reason = f"Actor is at the dungeon item cap (10): {command.actor_id}" if dungeon_item_count >= 10 else None

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

    elif isinstance(command, DropItem):
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

    elif isinstance(command, ActivateObject):
        obj = repo.get_room_object(command.object_id)

        if obj is None:
            reason = f"Unknown object: {command.object_id}"
        else:
            transition = next(
                (
                    t
                    for t in obj["transitions"]
                    if t["from_state"] == obj["current_state"] and t["trigger"] == command.trigger
                ),
                None,
            )
            if transition is None:
                reason = (
                    f"No transition for trigger '{command.trigger}' from state "
                    f"'{obj['current_state']}': {command.object_id}"
                )
            elif transition["requires_item_slug"] is not None:
                actor_items = repo.get_items_by_actor(command.actor_id)
                has_required = any(
                    i["slug"] == transition["requires_item_slug"] and i["status"] == "active"
                    for i in actor_items
                )
                reason = (
                    None
                    if has_required
                    else f"Missing required item '{transition['requires_item_slug']}': {command.object_id}"
                )
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
