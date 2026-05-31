"""Unit tests for hit_test.py — room and connection hit testing."""
from dungeon_daddy.map.dungeon_layout.hit_test import hit_test, hit_test_connection, hit_test_room
from dungeon_daddy.map.dungeon_layout.models import RoutedEdge, RoomRect


def _room(room_id: str, x: float, y: float, w: float = 80.0, h: float = 50.0) -> RoomRect:
    return RoomRect(room_id=room_id, x=x, y=y, w=w, h=h)


class TestHitTestRoom:
    def test_point_inside_returns_room_id(self):
        rooms = [_room("R1", 100, 200)]
        assert hit_test_room(rooms, 140, 225) == "R1"

    def test_point_outside_all_rooms_returns_none(self):
        rooms = [_room("R1", 100, 200), _room("R2", 300, 200)]
        assert hit_test_room(rooms, 50, 50) is None

    def test_boundary_point_counts_as_inside(self):
        # exact left edge
        rooms = [_room("R1", 100, 200)]
        assert hit_test_room(rooms, 100, 220) == "R1"


def _edge(connection_id: str, points: list[tuple[float, float]]) -> RoutedEdge:
    return RoutedEdge(
        connection_id=connection_id,
        points=points,
        source_port="right",
        target_port="left",
        score=1.0,
    )


class TestHitTestConnection:
    def test_horizontal_segment_within_tolerance(self):
        # segment runs from (100, 200) to (300, 200); point is 5 px above midpoint
        edges = [_edge("R1→R2", [(100, 200), (300, 200)])]
        assert hit_test_connection(edges, 200, 205, tolerance=8.0) == "R1→R2"

    def test_vertical_segment_within_tolerance(self):
        edges = [_edge("R1→R3", [(150, 100), (150, 400)])]
        assert hit_test_connection(edges, 155, 250, tolerance=8.0) == "R1→R3"

    def test_point_beyond_tolerance_returns_none(self):
        edges = [_edge("R1→R2", [(100, 200), (300, 200)])]
        assert hit_test_connection(edges, 200, 215, tolerance=8.0) is None

    def test_multi_segment_route_near_second_segment(self):
        # L-shaped route: right then up
        edges = [_edge("R2→R4", [(100, 100), (300, 100), (300, 300)])]
        # point near the vertical second segment
        assert hit_test_connection(edges, 305, 200, tolerance=8.0) == "R2→R4"


class TestHitTest:
    def test_room_wins_over_connection_when_both_match(self):
        # room at (100,100) size 80x50; connection edge runs through the room interior
        rooms = [_room("R1", 100, 100)]
        edges = [_edge("R1→R2", [(140, 125), (300, 125)])]
        room_id, conn_id = hit_test(rooms, edges, 140, 125, tolerance=8.0)
        assert room_id == "R1"
        assert conn_id is None

    def test_connection_returned_when_no_room_matches(self):
        rooms = [_room("R1", 100, 100)]
        edges = [_edge("R1→R2", [(180, 125), (300, 125)])]
        # point is between room right edge (180) and the edge — outside the room
        room_id, conn_id = hit_test(rooms, edges, 220, 127, tolerance=8.0)
        assert room_id is None
        assert conn_id == "R1→R2"
