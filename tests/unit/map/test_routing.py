"""Tests for dungeon_daddy/map/routing.py — pure geometry helpers."""
from __future__ import annotations

import math
import pytest

from dungeon_daddy.data.models import Room, Waypoint
from dungeon_daddy.map.routing import (
    get_room_rect,
    get_room_port,
    line_intersects_rect,
    path_intersects_any_room,
    calculate_path_length,
    select_port_direction,
    straight_path_blocked,
    route_orthogonal,
    route_detour,
    route_waypoints,
    is_route_problematic,
    CONNECTION_OBSTACLE_MARGIN,
)


def _room(id: str, x: int, y: int, w: int = 2, h: int = 2) -> Room:
    return Room(id=id, num=1, name=id, x=x, y=y, w=w, h=h, type="hall", note="")


# ---------------------------------------------------------------------------
# get_room_rect
# ---------------------------------------------------------------------------

def test_get_room_rect_returns_left_bottom_right_top():
    room = _room("R1", x=3, y=5, w=4, h=2)
    assert get_room_rect(room) == (3, 5, 7, 7)


# ---------------------------------------------------------------------------
# get_room_port
# ---------------------------------------------------------------------------

def test_get_room_port_north():
    room = _room("R1", x=0, y=0, w=4, h=2)
    assert get_room_port(room, "north") == (2.0, 2.0)


def test_get_room_port_south():
    room = _room("R1", x=0, y=0, w=4, h=2)
    assert get_room_port(room, "south") == (2.0, 0.0)


def test_get_room_port_east():
    room = _room("R1", x=0, y=0, w=4, h=2)
    assert get_room_port(room, "east") == (4.0, 1.0)


def test_get_room_port_west():
    room = _room("R1", x=0, y=0, w=4, h=2)
    assert get_room_port(room, "west") == (0.0, 1.0)


# ---------------------------------------------------------------------------
# line_intersects_rect
# ---------------------------------------------------------------------------

def test_line_intersects_rect_crossing_returns_true():
    rect = (2, 2, 6, 6)
    assert line_intersects_rect((0, 4), (8, 4), rect) is True


def test_line_intersects_rect_missing_returns_false():
    rect = (2, 2, 6, 6)
    assert line_intersects_rect((0, 0), (1, 0), rect) is False


def test_line_intersects_rect_diagonal_crossing_returns_true():
    rect = (2, 2, 6, 6)
    assert line_intersects_rect((0, 0), (8, 8), rect) is True


def test_line_intersects_rect_parallel_outside_returns_false():
    rect = (2, 2, 6, 6)
    assert line_intersects_rect((0, 7), (8, 7), rect) is False


# ---------------------------------------------------------------------------
# path_intersects_any_room
# ---------------------------------------------------------------------------

def test_path_intersects_any_room_true_when_crossing_intermediate():
    source = _room("A", x=0, y=4)
    blocker = _room("B", x=4, y=3, w=2, h=2)
    target = _room("C", x=8, y=4)
    # Horizontal path from (2,5) to (8,5) passes through blocker at x=4..6, y=3..5
    path = [(2.0, 5.0), (8.0, 5.0)]
    rooms = [source, blocker, target]
    assert path_intersects_any_room(path, rooms, "A", "C") is True


def test_path_intersects_any_room_ignores_source_and_target():
    source = _room("A", x=0, y=0, w=3, h=3)
    target = _room("B", x=6, y=0, w=3, h=3)
    # Path starts inside source rect and ends inside target rect — should be ignored
    path = [(1.5, 1.5), (7.5, 1.5)]
    rooms = [source, target]
    assert path_intersects_any_room(path, rooms, "A", "B") is False


def test_path_intersects_any_room_false_when_clear():
    source = _room("A", x=0, y=0)
    blocker = _room("B", x=0, y=5, w=2, h=2)
    target = _room("C", x=8, y=0)
    # Horizontal path at y=1 — blocker is at y=5..7, so no intersection
    path = [(2.0, 1.0), (8.0, 1.0)]
    rooms = [source, blocker, target]
    assert path_intersects_any_room(path, rooms, "A", "C") is False


# ---------------------------------------------------------------------------
# calculate_path_length
# ---------------------------------------------------------------------------

def test_calculate_path_length_two_points():
    path = [(0.0, 0.0), (3.0, 4.0)]
    assert calculate_path_length(path) == pytest.approx(5.0)


def test_calculate_path_length_multi_segment():
    path = [(0.0, 0.0), (3.0, 0.0), (3.0, 4.0)]
    assert calculate_path_length(path) == pytest.approx(7.0)


def test_calculate_path_length_single_point_is_zero():
    assert calculate_path_length([(1.0, 2.0)]) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# select_port_direction
# ---------------------------------------------------------------------------

def test_select_port_direction_target_right_returns_east_west():
    src = _room("A", x=0, y=0, w=2, h=2)
    tgt = _room("B", x=6, y=0, w=2, h=2)
    assert select_port_direction(src, tgt) == ("east", "west")


def test_select_port_direction_target_left_returns_west_east():
    src = _room("A", x=6, y=0, w=2, h=2)
    tgt = _room("B", x=0, y=0, w=2, h=2)
    assert select_port_direction(src, tgt) == ("west", "east")


def test_select_port_direction_target_above_returns_north_south():
    src = _room("A", x=0, y=0, w=2, h=2)
    tgt = _room("B", x=0, y=6, w=2, h=2)
    assert select_port_direction(src, tgt) == ("north", "south")


def test_select_port_direction_target_below_returns_south_north():
    src = _room("A", x=0, y=6, w=2, h=2)
    tgt = _room("B", x=0, y=0, w=2, h=2)
    assert select_port_direction(src, tgt) == ("south", "north")


def test_select_port_direction_diagonal_tie_prefers_horizontal():
    # dx == dy in magnitude → horizontal should win (east/west)
    src = _room("A", x=0, y=0, w=2, h=2)
    tgt = _room("B", x=4, y=4, w=2, h=2)   # center-to-center: dx=4, dy=4
    assert select_port_direction(src, tgt) == ("east", "west")


# ---------------------------------------------------------------------------
# straight_path_blocked
# ---------------------------------------------------------------------------

def test_straight_path_blocked_true_when_blocker_on_path():
    # A(east port) → C(west port) is a horizontal line; B sits in the middle
    src = _room("A", x=0, y=4, w=2, h=2)   # east port at (2, 5)
    blocker = _room("B", x=4, y=3, w=2, h=4)  # rect (4,3,6,7) — crosses y=5
    tgt = _room("C", x=8, y=4, w=2, h=2)   # west port at (8, 5)
    assert straight_path_blocked(src, tgt, [src, blocker, tgt]) is True


def test_straight_path_blocked_false_when_path_is_clear():
    src = _room("A", x=0, y=4, w=2, h=2)
    tgt = _room("C", x=8, y=4, w=2, h=2)
    bystander = _room("B", x=4, y=10, w=2, h=2)  # far above — doesn't cross y=5
    assert straight_path_blocked(src, tgt, [src, bystander, tgt]) is False


def test_straight_path_blocked_ignores_source_and_target_rooms():
    # Path exits through source and enters through target — both must be skipped
    src = _room("A", x=0, y=0, w=4, h=4)   # large room; east port at (4, 2)
    tgt = _room("B", x=8, y=0, w=4, h=4)   # large room; west port at (8, 2)
    # No intermediate rooms — only source and target in list
    assert straight_path_blocked(src, tgt, [src, tgt]) is False


# ---------------------------------------------------------------------------
# route_orthogonal
# ---------------------------------------------------------------------------

def test_route_orthogonal_returns_h_first_when_v_first_is_blocked():
    # A east port (2,1) → C west port (6,5)
    # H-first corner: (6,1) — clear
    # V-first corner: (2,5) — blocker B at rect(2,2,4,6) blocks seg (2,1)→(2,5)
    a = _room("A", x=0, y=0, w=2, h=2)
    c = _room("C", x=6, y=4, w=2, h=2)
    b = _room("B", x=2, y=2, w=2, h=4)
    path = route_orthogonal(a, c, [a, b, c])
    assert path[0] == pytest.approx((2.0, 1.0))   # from_port
    assert path[1] == pytest.approx((6.0, 1.0))   # H-first corner (to_x, from_y)
    assert path[2] == pytest.approx((6.0, 5.0))   # to_port


def test_route_orthogonal_returns_v_first_when_h_first_is_blocked():
    # A north port (1,2) → C south port (5,6)
    # H-first corner: (5,2) — blocker B at rect(2,1,4,4) blocks seg (1,2)→(5,2)
    # V-first corner: (1,6) — clear
    a = _room("A", x=0, y=0, w=2, h=2)
    c = _room("C", x=4, y=6, w=2, h=2)
    b = _room("B", x=2, y=1, w=2, h=3)
    path = route_orthogonal(a, c, [a, b, c])
    assert path[0] == pytest.approx((1.0, 2.0))   # from_port
    assert path[1] == pytest.approx((1.0, 6.0))   # V-first corner (from_x, to_y)
    assert path[2] == pytest.approx((5.0, 6.0))   # to_port


# ---------------------------------------------------------------------------
# route_detour
# ---------------------------------------------------------------------------
# Geometry used across detour tests:
#   A at (0,0,w=2,h=2): east port (2,1)
#   B (blocker) at (4,-1,w=4,h=8): rect=(4,-1,8,7)
#   C at (10,4,w=2,h=2): west port (10,5)
#
# H-first path [(2,1),(10,1),(10,5)]: seg (2,1)→(10,1) crosses B (y=1 in [-1,7]). BLOCKED.
# V-first path [(2,1),(2,5),(10,5)]: seg (2,5)→(10,5) crosses B (y=5 in [-1,7]). BLOCKED.
# Both orthogonal routes have score ≥ 10000 — detour is needed.

def _detour_rooms():
    a = _room("A", x=0, y=0, w=2, h=2)
    b = _room("B", x=4, y=-1, w=4, h=8)
    c = _room("C", x=10, y=4, w=2, h=2)
    return a, b, c


def test_route_detour_avoids_blocking_room():
    a, b, c = _detour_rooms()
    path = route_detour(a, c, [a, b, c])
    assert not path_intersects_any_room(path, [a, b, c], "A", "C")


def test_route_detour_returns_orthogonal_when_already_clean():
    # No blocker between A and C — orthogonal route is already clean.
    a = _room("A", x=0, y=0, w=2, h=2)
    c = _room("C", x=10, y=4, w=2, h=2)
    path = route_detour(a, c, [a, c])
    ortho = route_orthogonal(a, c, [a, c])
    assert path == ortho


def test_route_detour_picks_cleaner_direction_when_one_detour_also_blocked():
    # Same base geometry but add D blocking the top detour path.
    # Top detour goes via y = 7+16 = 23; D at (4,21,w=4,h=4) blocks that horizontal.
    # Bottom detour via y = -1-16 = -17 is clear → route_detour must choose bottom.
    a, b, c = _detour_rooms()
    d = _room("D", x=4, y=21, w=4, h=4)   # rect (4,21,8,25) — blocks top detour at y=23
    all_rooms = [a, b, c, d]
    path = route_detour(a, c, all_rooms)
    assert not path_intersects_any_room(path, all_rooms, "A", "C")


# ---------------------------------------------------------------------------
# route_waypoints
# ---------------------------------------------------------------------------

def test_route_waypoints_inserts_waypoints_between_ports():
    # A east port (2,1), C west port (8,5); two manual waypoints in between
    a = _room("A", x=0, y=0, w=2, h=2)
    c = _room("C", x=8, y=4, w=2, h=2)
    waypoints = [Waypoint(x=4.0, y=1.0), Waypoint(x=4.0, y=5.0)]
    path = route_waypoints(a, c, waypoints)
    assert path[0] == pytest.approx(get_room_port(a, "east"))   # from port
    assert path[1] == pytest.approx((4.0, 1.0))
    assert path[2] == pytest.approx((4.0, 5.0))
    assert path[3] == pytest.approx(get_room_port(c, "west"))   # to port


def test_route_waypoints_empty_list_returns_straight_port_to_port():
    a = _room("A", x=0, y=0, w=2, h=2)
    c = _room("C", x=8, y=4, w=2, h=2)
    path = route_waypoints(a, c, [])
    assert len(path) == 2
    assert path[0] == pytest.approx(get_room_port(a, "east"))
    assert path[1] == pytest.approx(get_room_port(c, "west"))


# ---------------------------------------------------------------------------
# is_route_problematic
# ---------------------------------------------------------------------------

def test_is_route_problematic_clean_path_returns_false():
    a = _room("A", x=0, y=0, w=2, h=2)
    c = _room("C", x=10, y=0, w=2, h=2)
    path = [(1.0, 1.0), (11.0, 1.0)]
    assert is_route_problematic(path, [a, c], "A", "C") is False


def test_is_route_problematic_blocked_path_returns_true():
    a = _room("A", x=0, y=0, w=2, h=2)
    blocker = _room("B", x=4, y=0, w=2, h=2)
    c = _room("C", x=10, y=0, w=2, h=2)
    path = [(1.0, 1.0), (11.0, 1.0)]   # straight line through blocker
    assert is_route_problematic(path, [a, blocker, c], "A", "C") is True


# ---------------------------------------------------------------------------
# route_detour — degenerate horizontal alignment (fy == ty)
# ---------------------------------------------------------------------------

def test_route_detour_degenerate_horizontal_alignment_avoids_blocker():
    # fy == ty: east port of A and west port of C share the same y=5.
    # A blocker sits directly between them; top and bottom bypass walls force
    # the algorithm to use left/right candidates.
    # Old code: left/right candidates collapse to straight lines through the blocker.
    # Fixed code: candidates step vertically first so they genuinely bypass it.
    a = _room("A", x=0, y=4, w=2, h=2)    # east port (2, 5)
    b = _room("B", x=4, y=4, w=4, h=2)    # rect (4, 4, 8, 6) — blocks y=5
    c = _room("C", x=10, y=4, w=2, h=2)   # west port (10, 5) → fy == ty == 5
    top_wall = _room("T", x=1, y=9, w=10, h=2)   # blocks clamped top bypass at y=10
    bot_wall = _room("D", x=1, y=-1, w=10, h=2)  # blocks clamped bottom bypass at y=0
    all_rooms = [a, b, c, top_wall, bot_wall]
    path = route_detour(a, c, all_rooms)
    assert not path_intersects_any_room(path, all_rooms, "A", "C")


# ---------------------------------------------------------------------------
# SI-6 — routing edge cases (unconditional, no fixture files)
# ---------------------------------------------------------------------------

def test_routing_single_room_level_returns_empty_connections():
    room = _room("R1", x=5, y=5)
    rooms = [room]
    connections: list = []
    room_map = {r.id: r for r in rooms}
    paths = [route_detour(room_map[c.from_room], room_map[c.to_room], rooms) for c in connections]
    assert paths == []


def test_routing_adjacent_rooms_no_detour_needed():
    # A and B share the edge at x=2; no intermediate room to route around
    a = _room("A", x=0, y=0, w=2, h=2)
    b = _room("B", x=2, y=0, w=2, h=2)
    path = route_detour(a, b, [a, b])
    assert not is_route_problematic(path, [a, b], "A", "B")
    assert len(path) <= 3  # orthogonal (≤ 2 segments), not a multi-bend detour


def test_routing_room_at_grid_boundary():
    # A is pinned to the origin; verify no IndexError and no negative path coordinates
    a = _room("A", x=0, y=0, w=2, h=2)
    b = _room("B", x=6, y=0, w=2, h=2)
    path = route_detour(a, b, [a, b])
    assert all(x >= 0 and y >= 0 for x, y in path)
