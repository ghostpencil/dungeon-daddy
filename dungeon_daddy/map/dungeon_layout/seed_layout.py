"""Critical-path-first seed layout for the dungeon layout pipeline.

Takes a Level + role map + LayoutTemplate and returns placed RoomRects.
No Arcade dependency — pure Python.
"""
from __future__ import annotations

import math

from dungeon_daddy.data.models import Level
from dungeon_daddy.map.dungeon_layout.models import RoomRect
from dungeon_daddy.map.dungeon_layout.semantics import LayoutTemplate, RoomRole

ROOM_W: float = 120.0
ROOM_H: float = 80.0
ROOM_GAP: float = 60.0

_TERMINAL_ROLES = frozenset({"boss", "objective", "exit"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_seed_layout(
    level: Level,
    roles: dict[str, RoomRole],
    template: LayoutTemplate,
) -> dict[str, RoomRect]:
    """Place all rooms in *level* according to *template*.

    Returns ``{room_id: RoomRect}`` for every room.
    """
    if template == "linear":
        return _layout_linear(level, roles)
    if template == "hub_spoke":
        return _layout_hub_spoke(level, roles)
    return _layout_grid(level, roles)


# ---------------------------------------------------------------------------
# Template implementations
# ---------------------------------------------------------------------------

def _layout_linear(level: Level, roles: dict[str, RoomRole]) -> dict[str, RoomRect]:
    room_ids = [r.id for r in level.rooms]
    path = _critical_path(level, roles)
    path_set = set(path)
    off_path = [rid for rid in room_ids if rid not in path_set]

    result: dict[str, RoomRect] = {}
    stride = ROOM_W + ROOM_GAP

    for i, rid in enumerate(path):
        result[rid] = RoomRect(room_id=rid, x=i * stride, y=0.0, w=ROOM_W, h=ROOM_H)

    # Off-path rooms go in a row below
    for i, rid in enumerate(off_path):
        result[rid] = RoomRect(
            room_id=rid,
            x=i * stride,
            y=-(ROOM_H + ROOM_GAP),
            w=ROOM_W,
            h=ROOM_H,
        )

    return result


def _layout_hub_spoke(level: Level, roles: dict[str, RoomRole]) -> dict[str, RoomRect]:
    room_ids = [r.id for r in level.rooms]

    hub_id = next((rid for rid in room_ids if roles.get(rid) == "hub"), None)
    if hub_id is None:
        degrees = _compute_degrees(level)
        hub_id = max(room_ids, key=lambda rid: degrees.get(rid, 0))

    spokes = [rid for rid in room_ids if rid != hub_id]
    result: dict[str, RoomRect] = {}

    result[hub_id] = RoomRect(room_id=hub_id, x=0.0, y=0.0, w=ROOM_W, h=ROOM_H)

    radius = ROOM_W + ROOM_GAP * 2
    n = max(len(spokes), 1)
    for i, rid in enumerate(spokes):
        angle = 2 * math.pi * i / n
        result[rid] = RoomRect(
            room_id=rid,
            x=radius * math.cos(angle),
            y=radius * math.sin(angle),
            w=ROOM_W,
            h=ROOM_H,
        )

    return result


def _layout_grid(level: Level, roles: dict[str, RoomRole]) -> dict[str, RoomRect]:
    cols = max(1, math.ceil(math.sqrt(len(level.rooms))))
    stride_x = ROOM_W + ROOM_GAP
    stride_y = ROOM_H + ROOM_GAP

    result: dict[str, RoomRect] = {}
    for i, room in enumerate(level.rooms):
        col = i % cols
        row = i // cols
        result[room.id] = RoomRect(
            room_id=room.id,
            x=col * stride_x,
            y=-row * stride_y,
            w=ROOM_W,
            h=ROOM_H,
        )
    return result


# ---------------------------------------------------------------------------
# Critical path
# ---------------------------------------------------------------------------

def _critical_path(level: Level, roles: dict[str, RoomRole]) -> list[str]:
    room_ids = [r.id for r in level.rooms]
    if not room_ids:
        return []

    entrance = next(
        (rid for rid in room_ids if roles.get(rid) == "entrance"), room_ids[0]
    )
    terminals = {rid for rid in room_ids if roles.get(rid) in _TERMINAL_ROLES}

    if not terminals:
        dist = _bfs_dist(level, entrance)
        farthest = max(room_ids, key=lambda rid: dist.get(rid, 0))
        terminals = {farthest}

    best: list[str] = []
    for terminal in terminals:
        path = _bfs_path(level, entrance, terminal)
        if len(path) > len(best):
            best = path

    return best if best else [entrance]


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def _adjacency(level: Level) -> dict[str, list[str]]:
    adj: dict[str, list[str]] = {r.id: [] for r in level.rooms}
    for conn in level.connections:
        adj.setdefault(conn.from_room, []).append(conn.to_room)
        adj.setdefault(conn.to_room, []).append(conn.from_room)
    return adj


def _bfs_dist(level: Level, start: str) -> dict[str, int]:
    adj = _adjacency(level)
    dist = {start: 0}
    queue = [start]
    while queue:
        curr = queue.pop(0)
        for nb in adj.get(curr, []):
            if nb not in dist:
                dist[nb] = dist[curr] + 1
                queue.append(nb)
    return dist


def _bfs_path(level: Level, start: str, end: str) -> list[str]:
    if start == end:
        return [start]
    adj = _adjacency(level)
    prev: dict[str, str | None] = {start: None}
    queue = [start]
    while queue:
        curr = queue.pop(0)
        if curr == end:
            path: list[str] = []
            node: str | None = end
            while node is not None:
                path.append(node)
                node = prev[node]
            return list(reversed(path))
        for nb in adj.get(curr, []):
            if nb not in prev:
                prev[nb] = curr
                queue.append(nb)
    return []


def _compute_degrees(level: Level) -> dict[str, int]:
    degrees: dict[str, int] = {r.id: 0 for r in level.rooms}
    for conn in level.connections:
        degrees[conn.from_room] = degrees.get(conn.from_room, 0) + 1
        degrees[conn.to_room] = degrees.get(conn.to_room, 0) + 1
    return degrees
