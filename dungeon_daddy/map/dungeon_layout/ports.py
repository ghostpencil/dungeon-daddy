"""Port generation for the dungeon layout pipeline.

Assigns a Port to each connection endpoint, snapped to the room edge
on the side that faces the other room's centre.
No Arcade dependency — pure Python.
"""
from __future__ import annotations

from dungeon_daddy.data.models import Connection
from dungeon_daddy.map.dungeon_layout.models import Port, PortSide, RoomRect


def generate_ports(
    rooms: dict[str, RoomRect],
    connections: list[Connection],
) -> dict[str, Port]:
    """Return one Port per connection endpoint.

    Key format: ``"{room_id}__{other_room_id}"``
    """
    result: dict[str, Port] = {}
    for conn in connections:
        src = rooms[conn.from_room]
        tgt = rooms[conn.to_room]
        result[f"{conn.from_room}__{conn.to_room}"] = _port_facing(src, tgt)
        result[f"{conn.to_room}__{conn.from_room}"] = _port_facing(tgt, src)
    return result


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _facing_side(room: RoomRect, other: RoomRect) -> PortSide:
    dx = other.cx - room.cx
    dy = other.cy - room.cy
    if abs(dx) >= abs(dy):
        return "right" if dx >= 0 else "left"
    return "top" if dy >= 0 else "bottom"


def _port_facing(room: RoomRect, other: RoomRect) -> Port:
    side = _facing_side(room, other)
    if side == "right":
        x, y = room.right, room.cy
    elif side == "left":
        x, y = room.left, room.cy
    elif side == "top":
        x, y = room.cx, room.top
    else:
        x, y = room.cx, room.bottom
    return Port(room_id=room.room_id, side=side, x=x, y=y)
