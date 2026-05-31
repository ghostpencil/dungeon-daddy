"""Hit testing for Graph Mode — room (point-in-rect) and connection (segment tolerance).

No Arcade dependency. All geometry is in abstract layout space.
"""
from __future__ import annotations

import math

from dungeon_daddy.map.dungeon_layout.models import RoutedEdge, RoomRect


def hit_test_room(rooms: list[RoomRect], px: float, py: float) -> str | None:
    """Return the room_id of the first room that contains (px, py), or None."""
    for room in rooms:
        if room.contains_point(px, py):
            return room.room_id
    return None


def _point_to_segment_dist(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    """Perpendicular distance from point (px, py) to segment (ax, ay)–(bx, by)."""
    dx, dy = bx - ax, by - ay
    len_sq = dx * dx + dy * dy
    if len_sq == 0.0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def hit_test_connection(
    edges: list[RoutedEdge], px: float, py: float, tolerance: float = 8.0
) -> str | None:
    """Return the connection_id of the first edge whose polyline is within tolerance of (px, py)."""
    for edge in edges:
        pts = edge.points
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            if _point_to_segment_dist(px, py, ax, ay, bx, by) <= tolerance:
                return edge.connection_id
    return None


def hit_test(
    rooms: list[RoomRect],
    edges: list[RoutedEdge],
    px: float,
    py: float,
    tolerance: float = 8.0,
) -> tuple[str | None, str | None]:
    """Return (room_id, connection_id). Room wins: connection_id is None when a room matches."""
    room_id = hit_test_room(rooms, px, py)
    if room_id is not None:
        return room_id, None
    return None, hit_test_connection(edges, px, py, tolerance)
