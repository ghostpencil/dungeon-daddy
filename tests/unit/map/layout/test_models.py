"""Tests for dungeon_layout geometry models."""
import pytest

from dungeon_daddy.map.dungeon_layout.models import (
    LabelBox,
    LayoutBounds,
    Port,
    RoomRect,
    RoutedEdge,
    RouteSegment,
)

# ---------------------------------------------------------------------------
# RoomRect
# ---------------------------------------------------------------------------

class TestRoomRect:
    def test_edge_properties(self):
        r = RoomRect(x=10, y=20, w=100, h=60)
        assert r.left == 10
        assert r.bottom == 20
        assert r.right == 110
        assert r.top == 80

    def test_center_properties(self):
        r = RoomRect(x=0, y=0, w=100, h=60)
        assert r.cx == 50
        assert r.cy == 30

    def test_inflate_expands_all_sides(self):
        r = RoomRect(x=10, y=10, w=80, h=60)
        inflated = r.inflate(8)
        assert inflated.left == 2
        assert inflated.bottom == 2
        assert inflated.right == 98
        assert inflated.top == 78

    def test_inflate_increases_dimensions(self):
        r = RoomRect(x=0, y=0, w=50, h=40)
        inflated = r.inflate(10)
        assert inflated.w == 70
        assert inflated.h == 60

    def test_contains_point_inside(self):
        r = RoomRect(x=0, y=0, w=100, h=80)
        assert r.contains_point(50, 40) is True

    def test_contains_point_outside(self):
        r = RoomRect(x=0, y=0, w=100, h=80)
        assert r.contains_point(200, 40) is False

    def test_contains_point_on_edge(self):
        r = RoomRect(x=0, y=0, w=100, h=80)
        assert r.contains_point(0, 40) is True
        assert r.contains_point(100, 40) is True


# ---------------------------------------------------------------------------
# Port
# ---------------------------------------------------------------------------

class TestPort:
    def test_construction(self):
        p = Port(room_id="r1", side="right", x=100.0, y=30.0)
        assert p.room_id == "r1"
        assert p.side == "right"
        assert p.x == 100.0
        assert p.y == 30.0

    def test_valid_sides(self):
        for side in ("top", "bottom", "left", "right"):
            p = Port(room_id="r1", side=side, x=0.0, y=0.0)
            assert p.side == side


# ---------------------------------------------------------------------------
# RouteSegment
# ---------------------------------------------------------------------------

class TestRouteSegment:
    def test_length_horizontal(self):
        seg = RouteSegment(start=(0.0, 0.0), end=(5.0, 0.0))
        assert seg.length == pytest.approx(5.0)

    def test_length_vertical(self):
        seg = RouteSegment(start=(0.0, 0.0), end=(0.0, 3.0))
        assert seg.length == pytest.approx(3.0)

    def test_length_diagonal(self):
        seg = RouteSegment(start=(0.0, 0.0), end=(3.0, 4.0))
        assert seg.length == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# RoutedEdge
# ---------------------------------------------------------------------------

class TestRoutedEdge:
    def test_construction(self):
        edge = RoutedEdge(
            connection_id="r1_to_r2",
            points=[(0.0, 0.0), (100.0, 0.0), (100.0, 80.0)],
            source_port="right",
            target_port="bottom",
            score=150.0,
        )
        assert edge.connection_id == "r1_to_r2"
        assert len(edge.points) == 3
        assert edge.source_port == "right"
        assert edge.target_port == "bottom"
        assert edge.score == pytest.approx(150.0)

    def test_bend_count_straight(self):
        edge = RoutedEdge(
            connection_id="r1_to_r2",
            points=[(0.0, 0.0), (100.0, 0.0)],
            source_port="right",
            target_port="left",
            score=100.0,
        )
        assert edge.bend_count == 0

    def test_bend_count_one_bend(self):
        edge = RoutedEdge(
            connection_id="r1_to_r2",
            points=[(0.0, 0.0), (100.0, 0.0), (100.0, 80.0)],
            source_port="right",
            target_port="top",
            score=180.0,
        )
        assert edge.bend_count == 1

    def test_warnings_default_empty(self):
        edge = RoutedEdge(
            connection_id="r1_to_r2",
            points=[(0.0, 0.0), (50.0, 0.0)],
            source_port="right",
            target_port="left",
            score=50.0,
        )
        assert edge.warnings == []


# ---------------------------------------------------------------------------
# LabelBox
# ---------------------------------------------------------------------------

class TestLabelBox:
    def test_construction(self):
        lb = LabelBox(
            connection_id="r1_to_r2",
            text="door",
            x=50.0,
            y=20.0,
            w=40.0,
            h=14.0,
        )
        assert lb.connection_id == "r1_to_r2"
        assert lb.text == "door"
        assert lb.right == pytest.approx(90.0)
        assert lb.top == pytest.approx(34.0)


# ---------------------------------------------------------------------------
# LayoutBounds
# ---------------------------------------------------------------------------

class TestLayoutBounds:
    def test_from_single_rect(self):
        r = RoomRect(x=10, y=20, w=80, h=60)
        bounds = LayoutBounds.from_rects([r])
        assert bounds.min_x == 10
        assert bounds.min_y == 20
        assert bounds.max_x == 90
        assert bounds.max_y == 80

    def test_from_multiple_rects(self):
        rects = [
            RoomRect(x=0, y=0, w=50, h=40),
            RoomRect(x=100, y=80, w=60, h=30),
        ]
        bounds = LayoutBounds.from_rects(rects)
        assert bounds.min_x == 0
        assert bounds.min_y == 0
        assert bounds.max_x == 160
        assert bounds.max_y == 110

    def test_width_and_height(self):
        bounds = LayoutBounds(min_x=10, min_y=20, max_x=110, max_y=70)
        assert bounds.width == 100
        assert bounds.height == 50

    def test_expand_adds_margin(self):
        bounds = LayoutBounds(min_x=10, min_y=20, max_x=110, max_y=70)
        expanded = bounds.expand(20)
        assert expanded.min_x == -10
        assert expanded.min_y == 0
        assert expanded.max_x == 130
        assert expanded.max_y == 90
