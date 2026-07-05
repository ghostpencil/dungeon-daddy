from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.command import (
    ActivateObject,
    CombineItems,
    ConsumeItem,
    ConsumeKitCharge,
    DropItem,
    EquipItem,
    GiveItem,
    PickUpItem,
    PlayerCommand,
    TakeItem,
    UnequipItem,
)
from dungeon_daddy.rpg.command_validator import CommandValidationResult
from dungeon_daddy.rpg.models import ClockState
from dungeon_daddy.rpg.service import RpgService

_log = logging.getLogger(__name__)


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

    elif isinstance(command, PickUpItem):
        repo.update_item_owner(command.item_id, command.actor_id)
        repo.update_item_room(command.item_id, None)
        result.events.append(
            DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="item.picked_up",
                payload={"item_id": command.item_id, "actor_id": command.actor_id},
            )
        )

    elif isinstance(command, DropItem):
        repo.update_item_owner(command.item_id, None)
        repo.update_item_room(command.item_id, command.room_id)
        result.events.append(
            DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="item.dropped",
                payload={"item_id": command.item_id, "room_id": command.room_id},
            )
        )

    elif isinstance(command, CombineItems):
        items = repo.get_items(campaign_id)
        item_a = next((i for i in items if i["item_id"] == command.item_a_id), None)
        item_b = next((i for i in items if i["item_id"] == command.item_b_id), None)
        if item_a is None or item_b is None:
            return result

        repo.update_item_status(command.item_a_id, "consumed")
        repo.update_item_status(command.item_b_id, "consumed")
        result.events.append(
            DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="items.combined",
                payload={
                    "item_a_id": command.item_a_id,
                    "item_b_id": command.item_b_id,
                    "actor_id": command.actor_id,
                },
            )
        )

        result_slug = item_a.get("combination_result_slug")
        if result_slug:
            target = next(
                (
                    i for i in items
                    if i["slug"] == result_slug
                    and i.get("owner_actor_id") is None
                    and i.get("room_id") is None
                ),
                None,
            )
            if target is not None:
                repo.update_item_owner(target["item_id"], command.actor_id)
                repo.update_item_status(target["item_id"], "active")
                result.events.append(
                    DomainEvent(
                        event_id=str(uuid.uuid4()),
                        campaign_id=campaign_id,
                        event_type="item.spawned",
                        payload={
                            "item_id": target["item_id"],
                            "slug": result_slug,
                            "actor_id": command.actor_id,
                        },
                    )
                )
            else:
                _log.info("Combine spawn no-op: no unplaced inert item with slug '%s'", result_slug)

    elif isinstance(command, ActivateObject):
        obj = repo.get_room_object(command.object_id)
        if obj is None:
            return result
        transition = next(
            (
                t for t in obj["transitions"]
                if t["from_state"] == obj["current_state"] and t["trigger"] == command.trigger
            ),
            None,
        )
        if transition is None:
            return result

        repo.update_object_state(command.object_id, transition["to_state"])
        result.events.append(
            DomainEvent(
                event_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="object.transitioned",
                payload={
                    "object_id": command.object_id,
                    "from_state": obj["current_state"],
                    "to_state": transition["to_state"],
                    "trigger": command.trigger,
                },
            )
        )

        spawns_slug = transition.get("spawns_item_slug")
        if spawns_slug:
            all_items = repo.get_items(campaign_id)
            target = next(
                (
                    i for i in all_items
                    if i["slug"] == spawns_slug
                    and i.get("owner_actor_id") is None
                    and i.get("room_id") is None
                ),
                None,
            )
            if target is not None:
                repo.update_item_room(target["item_id"], obj["room_id"])
                repo.update_item_status(target["item_id"], "active")
                result.events.append(
                    DomainEvent(
                        event_id=str(uuid.uuid4()),
                        campaign_id=campaign_id,
                        event_type="item.spawned",
                        payload={"item_id": target["item_id"], "slug": spawns_slug, "room_id": obj["room_id"]},
                    )
                )
            else:
                _log.info("Spawn no-op: no unplaced inert item with slug '%s'", spawns_slug)

        required_slug = transition.get("requires_item_slug")
        if required_slug:
            actor_items = repo.get_items_by_actor(command.actor_id)
            held = next(
                (i for i in actor_items if i["slug"] == required_slug and i["status"] == "active"),
                None,
            )
            if held is not None:
                repo.update_item_status(held["item_id"], "consumed")
                result.events.append(
                    DomainEvent(
                        event_id=str(uuid.uuid4()),
                        campaign_id=campaign_id,
                        event_type="item.consumed",
                        payload={"item_id": held["item_id"], "reason": "activated"},
                    )
                )

        advances_slug = transition.get("advances_clock_slug")
        if advances_slug:
            clocks = repo.get_clocks(campaign_id)
            clock_dict = next(
                (c for c in clocks if c["clock_id"].endswith(f":{advances_slug}")),
                None,
            )
            if clock_dict is not None:
                clock = ClockState(**clock_dict)
                service = RpgService()
                updated_clock, clock_event = service.advance_clock(clock, ticks=1)
                repo.update_clock_progress(clock_dict["clock_id"], updated_clock.filled, updated_clock.status)
                result.events.append(clock_event)
            else:
                _log.info("Clock advance no-op: no clock with slug '%s'", advances_slug)

    return result
