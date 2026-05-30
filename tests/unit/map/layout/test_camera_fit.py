"""Tests for camera_fit.compute_layout_bounds."""
import pytest

from dungeon_daddy.map.dungeon_layout.camera_fit import compute_layout_bounds
from dungeon_daddy.map.dungeon_layout.models import LabelBox, LayoutBounds, RoomRect, RoutedEdge


def _room(x: float, y: float, w: float, h: float) -> RoomRect:
    return RoomRect(x=x, y=y, w=w, h=h)


def _edge(points: list[tuple[float, float]]) -> RoutedEdge:
    return RoutedEdge(
        connection_id="e",
        points=points,
        source_port="p1",
        target_port="p2",
        score=1.0,
    )


def _label(x: float, y: float, w: float, h: float) -> LabelBox:
    return LabelBox(connection_id="l", text="T", x=x, y=y, w=w, h=h)


# ---------------------------------------------------------------------------
# Behavior 1: rooms only
# ---------------------------------------------------------------------------

def test_rooms_only_bounds_cover_all_rooms() -> None:
    rooms = [_room(0, 0, 10, 10), _room(20, 30, 5, 5)]
    result = compute_layout_bounds(rooms=rooms, edges=[], labels=[])
    assert result.min_x == 0
    assert result.min_y == 0
    assert result.max_x == 25
    assert result.max_y == 35


# ---------------------------------------------------------------------------
# Behavior 2: edges only
# ---------------------------------------------------------------------------

def test_edges_only_bounds_cover_all_waypoints() -> None:
    edges = [_edge([(5, 10), (15, 10), (15, 40)])]
    result = compute_layout_bounds(rooms=[], edges=edges, labels=[])
    assert result.min_x == 5
    assert result.min_y == 10
    assert result.max_x == 15
    assert result.max_y == 40


# ---------------------------------------------------------------------------
# Behavior 3: labels only
# ---------------------------------------------------------------------------

def test_labels_only_bounds_cover_all_label_boxes() -> None:
    labels = [_label(3, 7, 12, 4)]  # right=15, top=11
    result = compute_layout_bounds(rooms=[], edges=[], labels=labels)
    assert result.min_x == 3
    assert result.min_y == 7
    assert result.max_x == 15
    assert result.max_y == 11


# ---------------------------------------------------------------------------
# Behavior 4: mixed input
# ---------------------------------------------------------------------------

def test_mixed_input_bounds_cover_all_geometry() -> None:
    rooms = [_room(0, 0, 10, 10)]
    edges = [_edge([(12, 5), (20, 5)])]
    labels = [_label(-5, -3, 2, 2)]  # left=-5, bottom=-3, right=-3, top=-1
    result = compute_layout_bounds(rooms=rooms, edges=edges, labels=labels)
    assert result.min_x == -5
    assert result.min_y == -3
    assert result.max_x == 20
    assert result.max_y == 10


# ---------------------------------------------------------------------------
# Behavior 5: margin expands bounds symmetrically
# ---------------------------------------------------------------------------

def test_margin_expands_bounds_symmetrically() -> None:
    rooms = [_room(10, 10, 20, 20)]
    result = compute_layout_bounds(rooms=rooms, edges=[], labels=[], margin=5.0)
    assert result.min_x == 5.0
    assert result.min_y == 5.0
    assert result.max_x == 35.0
    assert result.max_y == 35.0


# ---------------------------------------------------------------------------
# Behavior 6: empty input raises ValueError
# ---------------------------------------------------------------------------

def test_empty_input_raises_value_error() -> None:
    with pytest.raises(ValueError):
        compute_layout_bounds(rooms=[], edges=[], labels=[])
