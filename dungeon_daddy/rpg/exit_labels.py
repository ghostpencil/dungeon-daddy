"""Player-facing exit noun labels for the VNA action panel (Phase 50 verify fix).

Disambiguates same-type exits (two ``Door``s in one room) without leaking
undiscovered rooms: a discovered-but-unvisited exit shows a compass *direction*
derived from the two rooms' grid centres; once the destination has been visited
the label upgrades to the room name. Pure logic — no DB, no Arcade.

Grid convention (matches ``data/dungeon.js``): ``+x`` is east, ``+y`` is south
(map north is up).
"""
from __future__ import annotations

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


def compass_direction(from_room, to_room) -> str | None:
    """Cardinal direction from one room to another by grid centre.

    Returns the dominant axis (``"north"``/``"south"``/``"east"``/``"west"``),
    or ``None`` when the two centres coincide.
    """
    fx, fy = _center(from_room)
    tx, ty = _center(to_room)
    dx, dy = tx - fx, ty - fy
    if dx == 0 and dy == 0:
        return None
    if abs(dx) >= abs(dy):
        return "east" if dx > 0 else "west"
    return "south" if dy > 0 else "north"


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
    if exit_row.get("status") in _LOCKED_LABEL_STATUSES:
        label = f"{LOCK_PREFIX}{label}"
    return label
