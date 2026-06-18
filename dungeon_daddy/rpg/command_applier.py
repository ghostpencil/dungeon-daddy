from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.command import ConsumeItem, ConsumeKitCharge, EquipItem, GiveItem, PlayerCommand, TakeItem, UnequipItem
from dungeon_daddy.rpg.command_validator import CommandValidationResult


@dataclass
class CommandApplyResult:
    events: list[DomainEvent] = field(default_factory=list)


def apply_command(
    command: PlayerCommand,
    validation_result: CommandValidationResult,
    repo: MemoryRepository,
    campaign_id: str,
) -> CommandApplyResult:
    result = CommandApplyResult()
    if not validation_result.accepted:
        return result

    if isinstance(command, ConsumeKitCharge):
        items = repo.get_items(campaign_id)
        item = next((i for i in items if i["item_id"] == command.item_id), None)
        if item is None:
            return result

        new_charges = item["charges_current"] - 1
        repo.update_item_charges(command.item_id, new_charges)

        result.events.append(
            DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="kit.charge_consumed",
                payload={
                    "item_id": command.item_id,
                    "charges_current": new_charges,
                    "reason": command.reason,
                },
            )
        )

    elif isinstance(command, ConsumeItem):
        repo.update_item_status(command.item_id, "consumed")
        result.events.append(
            DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="item.consumed",
                payload={"item_id": command.item_id, "reason": command.reason},
            )
        )

    elif isinstance(command, GiveItem):
        repo.update_item_owner(command.item_id, command.to_actor_id)
        result.events.append(
            DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="item.transferred",
                payload={"item_id": command.item_id, "to_actor_id": command.to_actor_id},
            )
        )

    elif isinstance(command, TakeItem):
        repo.update_item_status(command.item_id, "lost")
        result.events.append(
            DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="item.removed",
                payload={"item_id": command.item_id},
            )
        )

    elif isinstance(command, EquipItem):
        repo.update_item_equipped(command.item_id, True)
        result.events.append(
            DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="item.equipped",
                payload={"item_id": command.item_id},
            )
        )

    elif isinstance(command, UnequipItem):
        repo.update_item_equipped(command.item_id, False)
        result.events.append(
            DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="item.unequipped",
                payload={"item_id": command.item_id},
            )
        )

    return result
