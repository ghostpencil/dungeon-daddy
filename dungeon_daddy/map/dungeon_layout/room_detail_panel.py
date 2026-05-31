"""Room detail panel data assembly for Graph Mode.

Pure data — no Arcade dependency.
Assembles panel content from a Level + LayoutResult for a selected room.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from dungeon_daddy.data.models import Level
from dungeon_daddy.map.dungeon_layout import LayoutResult


@dataclass
class ConnectionDetail:
    room_id: str
    room_name: str
    label: str
    role: str | None
    graph_notes: str | None


@dataclass
class RoomDetailPanelData:
    room_id: str
    room_name: str
    role: str | None
    visual_priority: str | None
    on_critical_path: bool
    on_optional_branch: bool
    graph_notes: str | None
    note: str
    connections: list[ConnectionDetail] = field(default_factory=list)


def build_room_detail(
    room_id: str,
    level: Level,
    result: LayoutResult,
) -> RoomDetailPanelData | None:
    """Return panel data for *room_id*, or None if the room is not found in *level*."""
    room = next((r for r in level.rooms if r.id == room_id), None)
    if room is None:
        return None

    role: str | None = room.layout_role
    if role is None:
        inferred = result.room_roles.get(room_id)
        role = str(inferred) if inferred is not None else None

    on_critical_path = room_id in result.critical_path

    optional_branches: list[list[str]] = []
    if level.layout_metadata is not None:
        optional_branches = level.layout_metadata.optional_branches
    on_optional_branch = any(room_id in branch for branch in optional_branches)

    connections: list[ConnectionDetail] = []
    room_names = result.room_names
    for conn in level.connections:
        if conn.from_room == room_id:
            adj_id = conn.to_room
        elif conn.to_room == room_id:
            adj_id = conn.from_room
        else:
            continue
        connections.append(ConnectionDetail(
            room_id=adj_id,
            room_name=room_names.get(adj_id, adj_id),
            label=conn.type,
            role=conn.layout_connection_role,
            graph_notes=conn.graph_notes,
        ))

    return RoomDetailPanelData(
        room_id=room_id,
        room_name=room_names.get(room_id, room.name),
        role=role,
        visual_priority=room.visual_priority,
        on_critical_path=on_critical_path,
        on_optional_branch=on_optional_branch,
        graph_notes=room.graph_notes,
        note=room.note,
        connections=connections,
    )
