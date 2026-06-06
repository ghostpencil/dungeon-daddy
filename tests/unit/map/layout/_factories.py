"""Shared model factories for map/layout unit tests."""
from __future__ import annotations

from dungeon_daddy.data.models import Connection, Level, Room


def _room(room_id: str, name: str = "") -> Room:
    return Room(
        id=room_id, num=0, name=name or room_id,
        x=0, y=0, w=10, h=10, type="room", note="",
    )


def _conn(from_id: str, to_id: str) -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": "door"})


def _level(rooms: list[Room], connections: list[Connection]) -> Level:
    return Level(
        id=1, name="Test Level", summary="", ecology="", loop="",
        width=100, height=100, entries=[],
        rooms=rooms, connections=connections,
    )
