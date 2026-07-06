from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.command import MoveParty
from dungeon_daddy.rpg.exit_validator import validate_exit_conditions
from dungeon_daddy.rpg.models import RoomExit
from dungeon_daddy.rpg.service import mark_level_items_inert

_PASSABLE_STATUSES = {"open", "discovered", "one_way"}

HOW_MODIFIER_FLAGS: dict[str, set[str]] = {
    "cautiously": {"suppress_entry_ticks", "trap_chance:-1"},
    "quickly": {"tick_move_clock", "disturb_occupants"},
    "boldly": {"occupants_aware", "advance_npc_reaction"},
    "stealthily": {"suppress_all_entry_ticks"},
    "reverently": {"intimacy:+", "ritual_connector_eligible"},
    "recklessly": {"skip_condition_checks", "force_trap_trigger"},
    "deliberately": {"confirm_one_way"},
}


@dataclass
class MoveResult:
    accepted: bool
    rejection_reason: str | None = None
    events: list[DomainEvent] = field(default_factory=list)
    modifier_flags: set[str] = field(default_factory=set)


def apply_move_party(
    command: MoveParty,
    repo: MemoryRepository,
    campaign_id: str,
    session: SessionState,
    *,
    extra_inventory_slugs: list[str] | None = None,
) -> tuple[SessionState, MoveResult]:
    exit_row = repo.get_exit_by_id(command.exit_id)

    if exit_row is None:
        return session, MoveResult(accepted=False, rejection_reason=f"Unknown exit: {command.exit_id}")

    if exit_row["from_room_id"] != session.current_room_id:
        return session, MoveResult(accepted=False, rejection_reason=f"Exit not accessible from current room: {command.exit_id}")

    if exit_row["status"] not in _PASSABLE_STATUSES:
        return session, MoveResult(accepted=False, rejection_reason=f"Exit is not passable (status={exit_row['status']}): {command.exit_id}")

    flags = HOW_MODIFIER_FLAGS.get(command.how, set())

    exit_obj = RoomExit(**exit_row)
    if "skip_condition_checks" not in flags:
        actors = repo.get_actors_by_campaign(campaign_id)
        inventory_slugs: list[str] = []
        for actor in actors:
            if actor["actor_type"] == "pc":
                for item in repo.get_items_by_actor(actor["actor_id"]):
                    if item["status"] == "active" and item.get("slug"):
                        inventory_slugs.append(item["slug"])

        if extra_inventory_slugs:
            inventory_slugs.extend(extra_inventory_slugs)

        room_objects = repo.get_objects_by_room(campaign_id, session.current_room_id or "")
        clocks = repo.get_clocks(campaign_id)
        approved_memories = [
            e["title"] for e in repo.get_memory_entries_by_campaign(campaign_id)
            if e["status"] == "approved"
        ]

        failure = validate_exit_conditions(exit_obj, inventory_slugs, room_objects, clocks, approved_memories)
        if failure is not None:
            return session, MoveResult(accepted=False, rejection_reason=failure["reason"])

    to_room_id = exit_row["to_room_id"]
    visited = list(session.visited_rooms)
    if to_room_id not in visited:
        visited.append(to_room_id)

    session_update: dict[str, Any] = {"current_room_id": to_room_id, "visited_rooms": visited}

    to_level_id: str | None = exit_row.get("to_level_id")
    if exit_row.get("connector_type") and to_level_id:
        new_level_idx = int(to_level_id.split(":")[-1])
        session_update["current_level_idx"] = new_level_idx
        mark_level_items_inert(repo, campaign_id, exit_row["level_id"])

    new_session = session.model_copy(update=session_update)

    if exit_row["status"] == "one_way":
        repo.update_exit_status(command.exit_id, "sealed")

    event = DomainEvent(
        event_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        event_type="party.moved",
        payload={
            "exit_id": command.exit_id,
            "from_room_id": exit_row["from_room_id"],
            "to_room_id": to_room_id,
            "how": command.how,
        },
    )

    return new_session, MoveResult(accepted=True, events=[event], modifier_flags=flags)
