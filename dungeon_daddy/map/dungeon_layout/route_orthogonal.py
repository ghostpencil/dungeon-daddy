"""Obstacle-aware orthogonal routing for the dungeon layout pipeline.

Routes each connection as an orthogonal polyline (L-shaped dogleg or straight).
No Arcade dependency — pure Python.
"""
from __future__ import annotations

import math

from dungeon_daddy.data.models import Connection
from dungeon_daddy.map.dungeon_layout.models import Port, RoutedEdge, RoomRect

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def route_connections(
    rooms: dict[str, RoomRect],
    ports: dict[str, Port],
    connections: list[Connection],
    clearance: float = 16.0,
) -> list[RoutedEdge]:
    """Return one RoutedEdge per connection, using orthogonal dogleg routing."""
    obstacles = {rid: r.inflate(clearance) for rid, r in rooms.items()}
    edges: list[RoutedEdge] = []
    for conn in connections:
        src_key = f"{conn.from_room}__{conn.to_room}"
        tgt_key = f"{conn.to_room}__{conn.from_room}"
        src = ports[src_key]
        tgt = ports[tgt_key]
        edge = _route_one(conn, src, tgt, src_key, tgt_key, obstacles, rooms)
        edges.append(edge)
    return edges


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _route_one(
    conn: Connection,
    src: Port,
    tgt: Port,
    src_key: str,
    tgt_key: str,
    obstacles: dict[str, RoomRect],
    rooms: dict[str, RoomRect],
) -> RoutedEdge:
    connection_id = f"{conn.from_room}→{conn.to_room}"
    exclude = {conn.from_room, conn.to_room}

    candidates = _dogleg_candidates(src, tgt)
    best = min(candidates, key=lambda pts: _score(pts, obstacles, exclude))
    score = _score(best, obstacles, exclude)

    return RoutedEdge(
        connection_id=connection_id,
        points=best,
        source_port=src_key,
        target_port=tgt_key,
        score=score,
    )


def _dogleg_candidates(src: Port, tgt: Port) -> list[list[tuple[float, float]]]:
    """Generate orthogonal candidate paths (straight or L-shaped doglegs)."""
    sx, sy = src.x, src.y
    tx, ty = tgt.x, tgt.y

    candidates: list[list[tuple[float, float]]] = []

    # Straight line — only when truly collinear (orthogonal)
    if sx == tx or sy == ty:
        candidates.append([(sx, sy), (tx, ty)])

    # H-then-V: move horizontally to tx, then vertically to ty
    candidates.append([(sx, sy), (tx, sy), (tx, ty)])

    # V-then-H: move vertically to ty, then horizontally to tx
    candidates.append([(sx, sy), (sx, ty), (tx, ty)])

    return candidates


def _score(
    points: list[tuple[float, float]],
    obstacles: dict[str, RoomRect],
    exclude: set[str],
) -> float:
    total_length = sum(
        math.dist(points[i], points[i + 1]) for i in range(len(points) - 1)
    )
    bend_count = max(0, len(points) - 2)
    crossings = _count_crossings(points, obstacles, exclude)
    return total_length + bend_count * 24.0 + crossings * 100_000.0


def _count_crossings(
    points: list[tuple[float, float]],
    obstacles: dict[str, RoomRect],
    exclude: set[str],
) -> int:
    """Count how many obstacle rooms the polyline passes through."""
    count = 0
    for rid, rect in obstacles.items():
        if rid in exclude:
            continue
        if _polyline_intersects_rect(points, rect):
            count += 1
    return count


def _polyline_intersects_rect(
    points: list[tuple[float, float]],
    rect: RoomRect,
) -> bool:
    """Return True if any segment of the polyline passes through rect."""
    for i in range(len(points) - 1):
        if _segment_intersects_rect(points[i], points[i + 1], rect):
            return True
    return False


def _segment_intersects_rect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    rect: RoomRect,
) -> bool:
    """Return True if the axis-aligned segment p1→p2 overlaps rect."""
    x1, y1 = p1
    x2, y2 = p2
    # Clamp to segment bounding box
    seg_left   = min(x1, x2)
    seg_right  = max(x1, x2)
    seg_bottom = min(y1, y2)
    seg_top    = max(y1, y2)
    # AABB overlap
    return (
        seg_left   < rect.right
        and seg_right  > rect.left
        and seg_bottom < rect.top
        and seg_top    > rect.bottom
    )
