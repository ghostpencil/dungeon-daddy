from __future__ import annotations

from typing import Any, cast

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.discover_exit import passive_hidden_exit_hint

_VISIBLE_STATUSES = {"open", "discovered"}
_LOCKED_STATUSES = {"locked", "blocked", "one_way"}

# Exits the player already knows about (traversable or visibly locked) — i.e.
# everything except undiscovered (``hidden``) and permanently ``sealed`` exits.
# Shared with the Play-mode VNA noun list so hidden exits aren't move targets.
PLAYER_KNOWN_EXIT_STATUSES = frozenset(_VISIBLE_STATUSES | _LOCKED_STATUSES)


def build_room_context(
    room_id: str,
    campaign_id: str,
    session: SessionState,
    repo: MemoryRepository,
    *,
    resonance_point: bool = False,
) -> dict[str, Any]:
    objects = repo.get_objects_by_room(campaign_id, room_id)
    resonance_point = resonance_point or any(
        o["archetype"] == "resonance_point" for o in objects
    )

    exits = repo.get_exits_by_room(campaign_id, room_id)

    visible_exits = [
        {
            "exit_id": e["exit_id"],
            "label": e["label"],
            "status": e["status"],
            "exit_type": e["exit_type"],
            "connector_type": e["connector_type"],
            "to_room_id": e["to_room_id"],
        }
        for e in exits
        if e["status"] in _VISIBLE_STATUSES
    ]

    locked_exits = [
        {
            "exit_id": e["exit_id"],
            "label": e["label"],
            "status": e["status"],
            "reason": e["status"],
            "missing_condition": _missing_condition(e),
        }
        for e in exits
        if e["status"] in _LOCKED_STATUSES
    ]

    return {
        "room_id": room_id,
        "resonance_point": resonance_point,
        "visible_exits": visible_exits,
        "locked_exits": locked_exits,
        "hidden_exit_hint": passive_hidden_exit_hint(campaign_id, room_id, repo),
        "visited_rooms": list(session.visited_rooms),
    }


def _missing_condition(exit_row: dict[str, Any]) -> str | None:
    if exit_row.get("requires_item_slug"):
        return cast(str, exit_row["requires_item_slug"])
    if exit_row.get("requires_memory_slug"):
        return cast(str, exit_row["requires_memory_slug"])
    if exit_row.get("requires_clock_slug"):
        return cast(str, exit_row["requires_clock_slug"])
    if exit_row.get("requires_object_state"):
        return cast(str, exit_row["requires_object_state"])
    return None
