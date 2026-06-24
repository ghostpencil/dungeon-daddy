"""Player-facing exit noun labels for the VNA action panel (Phase 50 verify fix).

Disambiguates same-type exits (two ``Door``s in one room) without leaking
undiscovered rooms: a discovered-but-unvisited exit shows a compass *direction*
derived from the two rooms' grid centres; once the destination has been visited
the label upgrades to the room name. Pure logic — no DB, no Arcade.

Coordinate convention: directions are derived from the **rendered layout**
positions the player actually sees on the map (Arcade y-up screen space), not
the raw ``dungeon.json`` grid — the layout pipeline re-grids rooms by their
connections, so a raw "far east" room can render directly south of the hub.
``+x`` is east, ``+y`` is north (screen up). Eight points so diagonal rooms
read honestly (e.g. ``"southwest"``).
"""
from __future__ import annotations

import math
from typing import Mapping, Collection

# Prepended to an exit whose revealed status is a key-gated lock. A padlock glyph
# so the player can tell a locked door from an open one at a glance. Kept as a
# named constant so the marker is trivial to swap if the UI font lacks the glyph.
LOCK_PREFIX = "\N{LOCK} "

# Statuses that mean "revealed and locked" (needs a key/condition) — a one-way
# passage is a known status but not a lock, so it is excluded.
_LOCKED_LABEL_STATUSES = frozenset({"locked", "blocked"})


def _center(room) -> tuple[float, float]:
    return (room.x + room.w / 2, room.y + room.h / 2)


# Eight compass points indexed by atan2 octant (0 = east, counter-clockwise),
# with ``+y`` pointing north (the renderer's y-up screen space).
_OCTANTS = (
    "east", "northeast", "north", "northwest",
    "west", "southwest", "south", "southeast",
)


def compass_direction(from_room, to_room) -> str | None:
    """Eight-point compass direction from one room to another by centre.

    Returns one of the eight :data:`_OCTANTS` names, or ``None`` when the two
    centres coincide. ``+y`` is north, so a destination drawn below the source
    reads ``"south"``.
    """
    fx, fy = _center(from_room)
    tx, ty = _center(to_room)
    dx, dy = tx - fx, ty - fy
    if dx == 0 and dy == 0:
        return None
    octant = round(math.degrees(math.atan2(dy, dx)) / 45.0) % 8
    return _OCTANTS[octant]


def exit_noun_label(
    exit_row: Mapping,
    *,
    from_room,
    rooms_by_id: Mapping,
    visited_rooms: Collection[str],
) -> str:
    """Disambiguated label for an exit noun.

    Visited destination → ``"<base> -> <room name>"``; otherwise append the
    compass direction (``"<base> North"``). Falls back to the plain base label
    when the room geometry is unavailable (e.g. a cross-level connector, or no
    dungeon loaded). A revealed-locked exit is prefixed with :data:`LOCK_PREFIX`.
    """
    base = exit_row.get("label") or "Exit"
    to_id = exit_row.get("to_room_id")
    dest = rooms_by_id.get(to_id) if to_id is not None else None
    if dest is None or from_room is None:
        label = base
    elif to_id in set(visited_rooms):
        label = f"{base} -> {dest.name}"
    else:
        direction = compass_direction(from_room, dest)
        label = f"{base} {direction.title()}" if direction else base
    if exit_row.get("status") in _LOCKED_LABEL_STATUSES or exit_row.get("requires_item_slug"):
        label = f"{LOCK_PREFIX}{label}"
    return label
