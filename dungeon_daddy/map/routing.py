"""Pure geometry helpers for obstacle-aware connection routing.

All coordinates are in grid-cell space (same units as Room.x/y/w/h).
No Arcade calls — these are plain math functions.
"""
from __future__ import annotations

import math

from dungeon_daddy.data.models import Room, Waypoint

Rect = tuple[float, float, float, float]   # (left, bottom, right, top)
Point = tuple[float, float]
Path = list[Point]

# Routing constants
CONNECTION_OBSTACLE_MARGIN = 16
ROUTE_BOUNDING_MARGIN = 4
INTERSECTION_WEIGHT = 5000
ESCAPE_WEIGHT = 500
MAX_DETOUR_RATIO = 5.0
MAX_BEND_COUNT = 6


def get_room_rect(room: Room) -> Rect:
    return (float(room.x), float(room.y), float(room.x + room.w), float(room.y + room.h))


def get_room_port(room: Room, direction: str) -> Point:
    left, bottom, right, top = get_room_rect(room)
    cx = (left + right) / 2
    cy = (bottom + top) / 2
    match direction:
        case "north":
            return (cx, top)
        case "south":
            return (cx, bottom)
        case "east":
            return (right, cy)
        case "west":
            return (left, cy)
        case _:
            raise ValueError(f"Unknown direction: {direction!r}")


def get_local_bounds(from_room: Room, to_room: Room, margin: float = ROUTE_BOUNDING_MARGIN) -> Rect:
    fl, fb, fr, ft = get_room_rect(from_room)
    tl, tb, tr, tt = get_room_rect(to_room)
    return (
        min(fl, tl) - margin,
        min(fb, tb) - margin,
        max(fr, tr) + margin,
        max(ft, tt) + margin,
    )


def line_intersects_rect(p1: Point, p2: Point, rect: Rect) -> bool:
    """Return True if segment p1→p2 intersects the rectangle (using Liang-Barsky)."""
    left, bottom, right, top = rect
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    p = [-dx, dx, -dy, dy]
    q = [p1[0] - left, right - p1[0], p1[1] - bottom, top - p1[1]]
    t0, t1 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0.0:
            if qi < 0.0:
                return False
        elif pi < 0.0:
            t0 = max(t0, qi / pi)
        else:
            t1 = min(t1, qi / pi)
    return t0 <= t1


def path_intersects_any_room(path: Path, rooms: list[Room], source_id: str, target_id: str) -> bool:
    skip = {source_id, target_id}
    for room in rooms:
        if room.id in skip:
            continue
        rect = get_room_rect(room)
        for i in range(len(path) - 1):
            if line_intersects_rect(path[i], path[i + 1], rect):
                return True
    return False


def select_port_direction(from_room: Room, to_room: Room) -> tuple[str, str]:
    """Return (from_direction, to_direction) based on relative room center positions."""
    fl, fb, fr, ft = get_room_rect(from_room)
    tl, tb, tr, tt = get_room_rect(to_room)
    fcx, fcy = (fl + fr) / 2, (fb + ft) / 2
    tcx, tcy = (tl + tr) / 2, (tb + tt) / 2
    dx = tcx - fcx
    dy = tcy - fcy
    if abs(dx) >= abs(dy):
        return ("east", "west") if dx > 0 else ("west", "east")
    return ("north", "south") if dy > 0 else ("south", "north")


def straight_path_blocked(from_room: Room, to_room: Room, all_rooms: list[Room]) -> bool:
    """Return True if the straight port-to-port path crosses any unrelated room."""
    fd, td = select_port_direction(from_room, to_room)
    from_port = get_room_port(from_room, fd)
    to_port = get_room_port(to_room, td)
    return path_intersects_any_room([from_port, to_port], all_rooms, from_room.id, to_room.id)


def calculate_path_length(path: Path) -> float:
    return sum(
        math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
        for i in range(len(path) - 1)
    )


def _room_center(room: Room) -> Point:
    left, b, r, t = get_room_rect(room)
    return (left + r) / 2, (b + t) / 2


def _escape_distance(path: Path, bounds: Rect) -> float:
    ll, lb, lr, lt = bounds
    return sum(
        max(0.0, ll - x) + max(0.0, x - lr) + max(0.0, lb - y) + max(0.0, y - lt)
        for x, y in path
    )


def _detour_ratio_penalty(path_length: float, direct_distance: float) -> float:
    if direct_distance <= 0:
        return 0.0
    ratio = path_length / direct_distance
    if ratio > 3.0:
        return 1200 + (ratio - 3.0) * 2000
    if ratio > 2.0:
        return 200 + (ratio - 2.0) * 1000
    if ratio > 1.5:
        return (ratio - 1.5) * 400
    return 0.0


def _score_path(
    path: Path,
    all_rooms: list[Room],
    source_id: str,
    target_id: str,
    bend_count: int,
    local_bounds: Rect | None = None,
    direct_distance: float | None = None,
) -> float:
    skip = {source_id, target_id}
    intersections = sum(
        1 for room in all_rooms
        if room.id not in skip and any(
            line_intersects_rect(path[i], path[i + 1], get_room_rect(room))
            for i in range(len(path) - 1)
        )
    )
    length = calculate_path_length(path)
    escape = _escape_distance(path, local_bounds) * ESCAPE_WEIGHT if local_bounds is not None else 0.0
    ratio_penalty = _detour_ratio_penalty(length, direct_distance) if direct_distance is not None else 0.0
    return (
        intersections * INTERSECTION_WEIGHT
        + length * 10
        + bend_count * 100
        + escape
        + ratio_penalty
    )


def route_orthogonal(from_room: Room, to_room: Room, all_rooms: list[Room]) -> Path:
    """Return the lower-scoring 2-segment orthogonal route between two rooms."""
    fd, td = select_port_direction(from_room, to_room)
    from_port = get_room_port(from_room, fd)
    to_port = get_room_port(to_room, td)
    fx, fy = from_port
    tx, ty = to_port
    h_first: Path = [from_port, (tx, fy), to_port]
    v_first: Path = [from_port, (fx, ty), to_port]
    local = get_local_bounds(from_room, to_room)
    fcx, fcy = _room_center(from_room)
    tcx, tcy = _room_center(to_room)
    direct_dist = math.hypot(tcx - fcx, tcy - fcy)
    h_score = _score_path(h_first, all_rooms, from_room.id, to_room.id, bend_count=1, local_bounds=local, direct_distance=direct_dist)
    v_score = _score_path(v_first, all_rooms, from_room.id, to_room.id, bend_count=1, local_bounds=local, direct_distance=direct_dist)
    return h_first if h_score <= v_score else v_first


def _find_blocking_room(path: Path, rooms: list[Room], source_id: str, target_id: str) -> Room | None:
    skip = {source_id, target_id}
    for room in rooms:
        if room.id not in skip:
            for i in range(len(path) - 1):
                if line_intersects_rect(path[i], path[i + 1], get_room_rect(room)):
                    return room
    return None


def route_waypoints(from_room: Room, to_room: Room, waypoints: list[Waypoint]) -> Path:
    """Return a path using manual waypoints between the two room ports."""
    fd, td = select_port_direction(from_room, to_room)
    from_port = get_room_port(from_room, fd)
    to_port = get_room_port(to_room, td)
    mid: Path = [(float(wp.x), float(wp.y)) for wp in waypoints]
    return [from_port, *mid, to_port]


def is_route_problematic(path: Path, all_rooms: list[Room], source_id: str, target_id: str) -> bool:
    """Return True if path still intersects any unrelated room (route could not be cleanly resolved)."""
    return path_intersects_any_room(path, all_rooms, source_id, target_id)


def route_detour(from_room: Room, to_room: Room, all_rooms: list[Room]) -> Path:
    """Route around a blocking room when both orthogonal options still intersect rooms."""
    best_ortho = route_orthogonal(from_room, to_room, all_rooms)
    blocker = _find_blocking_room(best_ortho, all_rooms, from_room.id, to_room.id)
    if blocker is None:
        return best_ortho

    fd, td = select_port_direction(from_room, to_room)
    from_port = get_room_port(from_room, fd)
    to_port = get_room_port(to_room, td)
    fx, fy = from_port
    tx, ty = to_port
    bl, bb, br, bt = get_room_rect(blocker)
    m = CONNECTION_OBSTACLE_MARGIN

    local = get_local_bounds(from_room, to_room)
    ll, lb, lr, lt = local

    # Clamp bypass positions to local bounds
    bypass_top    = min(bt + m, lt)
    bypass_bottom = max(bb - m, lb)
    bypass_left   = max(bl - m, ll)
    bypass_right  = min(br + m, lr)

    fcx, fcy = _room_center(from_room)
    tcx, tcy = _room_center(to_room)
    direct_dist = math.hypot(tcx - fcx, tcy - fcy)

    if fy == ty:
        # Left/right candidates degenerate when ports share the same y.
        # Replace them with 5-point paths that step vertically to bypass the blocker.
        offset = ROUTE_BOUNDING_MARGIN / 2
        above_y = min(fy + offset, lt)
        below_y = max(fy - offset, lb)
        candidates: list[Path] = [
            [from_port, (fx, bypass_top),    (tx, bypass_top),    to_port],
            [from_port, (fx, bypass_bottom), (tx, bypass_bottom), to_port],
            [from_port, (fx, above_y), (bypass_left,  above_y), (tx, above_y), to_port],
            [from_port, (fx, below_y), (bypass_right, below_y), (tx, below_y), to_port],
        ]
    elif fx == tx:
        # Top/bottom candidates degenerate when ports share the same x.
        # Replace them with 5-point paths that step horizontally to bypass the blocker.
        offset = ROUTE_BOUNDING_MARGIN / 2
        right_x = min(fx + offset, lr)
        left_x  = max(fx - offset, ll)
        candidates = [
            [from_port, (bypass_left,  fy), (bypass_left,  ty), to_port],
            [from_port, (bypass_right, fy), (bypass_right, ty), to_port],
            [from_port, (right_x, fy), (right_x, bypass_top),    (right_x, ty), to_port],
            [from_port, (left_x,  fy), (left_x,  bypass_bottom), (left_x,  ty), to_port],
        ]
    else:
        candidates = [
            [from_port, (fx, bypass_top),    (tx, bypass_top),    to_port],
            [from_port, (fx, bypass_bottom), (tx, bypass_bottom), to_port],
            [from_port, (bypass_left,  fy), (bypass_left,  ty), to_port],
            [from_port, (bypass_right, fy), (bypass_right, ty), to_port],
        ]

    return min(
        candidates,
        key=lambda c: _score_path(
            c, all_rooms, from_room.id, to_room.id,
            bend_count=len(c) - 2,
            local_bounds=local,
            direct_distance=direct_dist,
        ),
    )
