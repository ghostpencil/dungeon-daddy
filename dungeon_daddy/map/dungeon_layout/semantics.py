"""Semantic analysis for the dungeon layout pipeline.

Classifies each room into a layout role and selects a floor template.
No Arcade dependency — pure Python.
"""
from __future__ import annotations

from typing import Literal

from dungeon_daddy.data.models import Level, Room

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

RoomRole = Literal[
    "entrance", "exit", "hub", "boss", "objective",
    "key_room", "lock_room", "treasure", "hazard",
    "secret", "utility", "corridor", "side_room",
    "transition", "descent", "elevator", "stairs",
    "hall", "study", "library", "forge", "unknown",
]

LayoutTemplate = Literal[
    "linear", "hub_spoke", "branch_merge",
    "lock_key", "boss_endcap", "loop", "freeform",
]

# ---------------------------------------------------------------------------
# Keyword tables
# ---------------------------------------------------------------------------

_ENTRANCE_KEYWORDS = {"entrance", "entry", "landing", "arrival", "approach", "receiving"}
_STAIRS_KEYWORDS = {"stairs", "staircase", "stair"}
_BOSS_KEYWORDS = {"boss", "lair", "throne", "core", "final"}
_OBJECTIVE_KEYWORDS = {"objective", "sanctum"}
_KEY_KEYWORDS = {"key", "control", "lever", "mechanism"}
_LOCK_KEYWORDS = {"locked", "gate", "sealed"}
_EXIT_KEYWORDS = {"exit"}
_DESCENT_KEYWORDS = {"descent", "shaft", "descend"}
_ELEVATOR_KEYWORDS = {"elevator"}
_HUB_NAME_KEYWORDS = {"nexus", "junction", "crossroads"}
_TREASURE_KEYWORDS = {"treasury", "reliquary", "vault"}
_HAZARD_KEYWORDS = {"trap", "hazard", "anomaly", "pit", "electrified"}
_HALL_KEYWORDS = {"hall", "hallway", "processional"}
_LIBRARY_KEYWORDS = {"library", "scriptorium", "archive"}
_FORGE_KEYWORDS = {"forge", "foundry", "molten", "factory"}

_HUB_DEGREE_THRESHOLD = 3  # rooms with >= this many connections are candidates


def _tokens(text: str) -> set[str]:
    """Lowercase words from a string, split on non-alpha chars."""
    import re
    return set(re.split(r"[^a-z]+", text.lower())) - {""}


def _matches(keywords: set[str], room: Room) -> bool:
    tokens = _tokens(room.name)
    for tag in room.tags:
        tokens |= _tokens(tag)
    return bool(keywords & tokens)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_room_role(room: Room, degree: int) -> RoomRole:
    """Return the layout role for a single room.

    Explicit ``room.layout_role`` wins; otherwise infers from name/tags/degree.
    """
    if room.layout_role is not None:
        return room.layout_role  # type: ignore[return-value]

    if _matches(_DESCENT_KEYWORDS, room):
        return "descent"
    if _matches(_ELEVATOR_KEYWORDS, room):
        return "elevator"
    if _matches(_STAIRS_KEYWORDS, room):
        return "stairs"
    if _matches(_ENTRANCE_KEYWORDS, room):
        return "entrance"
    if _matches(_BOSS_KEYWORDS, room):
        return "boss"
    if _matches(_OBJECTIVE_KEYWORDS, room):
        return "objective"
    if _matches(_EXIT_KEYWORDS, room):
        return "exit"
    if _matches(_KEY_KEYWORDS, room):
        return "key_room"
    if _matches(_LOCK_KEYWORDS, room):
        return "lock_room"
    if _matches(_HUB_NAME_KEYWORDS, room) or degree >= _HUB_DEGREE_THRESHOLD:
        return "hub"
    if _matches(_TREASURE_KEYWORDS, room):
        return "treasure"
    if _matches(_HAZARD_KEYWORDS, room):
        return "hazard"
    if _matches(_HALL_KEYWORDS, room):
        return "hall"
    if _matches(_LIBRARY_KEYWORDS, room):
        return "library"
    if _matches(_FORGE_KEYWORDS, room):
        return "forge"

    return "unknown"


def classify_all_roles(level: Level) -> dict[str, RoomRole]:
    """Return ``{room_id: role}`` for every room in *level*.

    Resolution order per room:
    1. explicit ``room.layout_role``
    2. floor-level ``layout_metadata`` references (entrance, objective)
    3. name/tag/degree inference
    4. ``unknown``
    """
    degrees: dict[str, int] = {r.id: 0 for r in level.rooms}
    for conn in level.connections:
        degrees[conn.from_room] = degrees.get(conn.from_room, 0) + 1
        degrees[conn.to_room] = degrees.get(conn.to_room, 0) + 1

    roles: dict[str, RoomRole] = {
        room.id: classify_room_role(room, degrees.get(room.id, 0))
        for room in level.rooms
    }

    meta = level.layout_metadata
    if meta is None:
        return roles

    room_by_id = {room.id: room for room in level.rooms}

    if meta.entrance_room_id and meta.entrance_room_id in roles:
        room = room_by_id[meta.entrance_room_id]
        if room.layout_role is None:
            roles[meta.entrance_room_id] = "entrance"

    for obj_id in meta.objective_room_ids:
        room = room_by_id.get(obj_id)
        if room is not None and room.layout_role is None:
            roles[obj_id] = "objective"

    return roles


def classify_template(level: Level, roles: dict[str, RoomRole]) -> LayoutTemplate:
    """Return the layout template for *level*.

    Explicit ``level.floor_tags`` win; otherwise infers from graph shape.
    """
    _VALID: set[LayoutTemplate] = {
        "linear", "hub_spoke", "branch_merge",
        "lock_key", "boss_endcap", "loop", "freeform",
    }
    for tag in level.floor_tags:
        if tag in _VALID:
            return tag

    degrees = {r.id: 0 for r in level.rooms}
    for conn in level.connections:
        degrees[conn.from_room] = degrees.get(conn.from_room, 0) + 1
        degrees[conn.to_room] = degrees.get(conn.to_room, 0) + 1

    if not degrees:
        return "freeform"

    sorted_degrees = sorted(degrees.values(), reverse=True)
    max_deg = sorted_degrees[0]
    avg_deg = sum(sorted_degrees) / len(sorted_degrees)

    # hub_spoke: one room dominates heavily
    if max_deg >= _HUB_DEGREE_THRESHOLD and max_deg >= avg_deg * 2:
        return "hub_spoke"

    # linear: exactly two endpoints (degree 1) and all internal rooms have degree 2
    endpoints = sum(1 for d in sorted_degrees if d == 1)
    internal_ok = all(d == 2 for d in sorted_degrees if d != 1)
    if endpoints == 2 and internal_ok:
        return "linear"

    return "freeform"
