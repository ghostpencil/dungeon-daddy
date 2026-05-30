"""Tests for dungeon_daddy.map.dungeon_layout.labels."""
from __future__ import annotations

from dungeon_daddy.map.dungeon_layout.labels import place_labels
from dungeon_daddy.map.dungeon_layout.models import RoomRect, RoutedEdge

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _edge(connection_id: str, points: list[tuple[float, float]]) -> RoutedEdge:
    return RoutedEdge(
        connection_id=connection_id,
        points=points,
        source_port="",
        target_port="",
        score=0.0,
    )


def _room(room_id: str, x: float, y: float, w: float = 100.0, h: float = 60.0) -> RoomRect:
    return RoomRect(room_id=room_id, x=x, y=y, w=w, h=h)


# ---------------------------------------------------------------------------
# Cycle 1 — empty input produces empty output
# ---------------------------------------------------------------------------

def test_empty_edges_returns_empty_list() -> None:
    result = place_labels([], {}, {})
    assert result == []


# ---------------------------------------------------------------------------
# Cycle 2 — one LabelBox per edge
# ---------------------------------------------------------------------------

def test_returns_one_label_per_edge() -> None:
    edge = _edge("a→b", [(0.0, 0.0), (200.0, 0.0)])
    result = place_labels([edge], {}, {"a→b": "Door"})
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Cycle 3 — LabelBox carries correct connection_id and text
# ---------------------------------------------------------------------------

def test_label_box_connection_id_and_text() -> None:
    edge = _edge("hall→boss", [(0.0, 0.0), (200.0, 0.0)])
    result = place_labels([edge], {}, {"hall→boss": "Iron Gate"})
    lb = result[0]
    assert lb.connection_id == "hall→boss"
    assert lb.text == "Iron Gate"


# ---------------------------------------------------------------------------
# Cycle 4 — label centre is at 25%, 50%, or 75% along the longest segment
# ---------------------------------------------------------------------------

def test_label_centre_is_at_fraction_of_longest_segment() -> None:
    """Single horizontal segment: centre-x must be at 50, 100, or 150."""
    edge = _edge("a→b", [(0.0, 0.0), (200.0, 0.0)])
    label_w = 60.0
    result = place_labels([edge], {}, {"a→b": "x"}, label_w=label_w)
    lb = result[0]
    cx = lb.x + label_w / 2
    assert cx in {50.0, 100.0, 150.0}


# ---------------------------------------------------------------------------
# Cycle 5 — label avoids overlap with rooms
# ---------------------------------------------------------------------------

def test_label_avoids_room_overlap() -> None:
    """A room covering all above-line positions forces the label below the edge."""
    # Horizontal edge along y=0; room covers y=5..105, forcing label below
    edge = _edge("a→b", [(0.0, 0.0), (200.0, 0.0)])
    rooms = {"blocker": _room("blocker", x=0.0, y=5.0, w=200.0, h=100.0)}
    result = place_labels([edge], rooms, {"a→b": "Door"})
    lb = result[0]
    # All "above" candidates sit inside the room (y≈8..22); label must be below y=0
    assert lb.y < 0.0


# ---------------------------------------------------------------------------
# Cycle 6 — labels for two co-routed edges do not overlap each other
# ---------------------------------------------------------------------------

def test_labels_for_two_edges_do_not_overlap() -> None:
    """Two edges sharing geometry and a room that blocks all below-candidates.

    Without label-avoidance scoring, both would place at the 25%-above position.
    With avoidance, the second label is pushed to a different fraction.
    """
    edge1 = _edge("a→b", [(0.0, 0.0), (200.0, 0.0)])
    edge2 = _edge("c→d", [(0.0, 0.0), (200.0, 0.0)])
    # Room covers all below-line slots (y=-30..0) so both labels must go above
    rooms = {"floor": _room("floor", x=-10.0, y=-30.0, w=220.0, h=30.0)}
    result = place_labels(
        [edge1, edge2], rooms, {"a→b": "Door", "c→d": "Arch"}
    )
    assert len(result) == 2
    lb1, lb2 = result
    overlapping = (
        lb1.x < lb2.right and lb1.right > lb2.x
        and lb1.y < lb2.top and lb1.top > lb2.y
    )
    assert not overlapping
