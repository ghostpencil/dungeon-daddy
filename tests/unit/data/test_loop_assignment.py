"""Tests for the loop auto-assignment algorithm."""
from __future__ import annotations

import importlib.resources
import json

import pytest

from dungeon_daddy.data.loop_assignment import auto_assign_loop_rooms
from dungeon_daddy.data.models import Connection, Dungeon, Level, Room

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tomb() -> Dungeon:
    pkg = importlib.resources.files("dungeon_daddy.data")
    raw = (pkg / "samples" / "tomb_of_the_forgotten_king.json").read_text(encoding="utf-8")
    return Dungeon.model_validate(json.loads(raw))


@pytest.fixture(scope="module")
def level1(tomb: Dungeon) -> Level:
    return tomb.levels[0]


@pytest.fixture(scope="module")
def level2(tomb: Dungeon) -> Level:
    return tomb.levels[1]


def _linear_level() -> Level:
    """Three rooms in a chain: R-1 ↔ R-2 ↔ R-3.  Only one path exists."""
    rooms = [
        Room(id="R-1", num=1, name="First",  x=0, y=0, w=2, h=2, type="hall", note=""),
        Room(id="R-2", num=2, name="Middle", x=3, y=0, w=2, h=2, type="hall", note=""),
        Room(id="R-3", num=3, name="Last",   x=6, y=0, w=2, h=2, type="hall", note=""),
    ]
    connections = [
        Connection(**{"from": "R-1", "to": "R-2", "type": "door", "note": ""}),
        Connection(**{"from": "R-2", "to": "R-3", "type": "door", "note": ""}),
    ]
    return Level(
        id=99, name="Linear", summary="", ecology="", loop="",
        width=10, height=5, entries=[], rooms=rooms, connections=connections,
    )


# ---------------------------------------------------------------------------
# Slice 1 — auto_assign_loop_rooms: entry detection
# ---------------------------------------------------------------------------

def test_entry_is_room_with_most_connections(level2: Level) -> None:
    """Level 2 has 2-E with 3 connections — it should be chosen as entry."""
    result = auto_assign_loop_rooms(level2)
    assert result.entry == "2-E"


def test_entry_tie_breaks_to_lowest_num(level1: Level) -> None:
    """Level 1: all rooms have 2 connections; lowest num wins → 1-A (num=1)."""
    result = auto_assign_loop_rooms(level1)
    assert result.entry == "1-A"


# ---------------------------------------------------------------------------
# Slice 1 — goal detection (BFS-furthest)
# ---------------------------------------------------------------------------

def test_goal_is_bfs_furthest_room_from_entry(level2: Level) -> None:
    """From 2-E the furthest rooms are 2-A and 2-B (dist 2); lowest num → 2-A."""
    result = auto_assign_loop_rooms(level2)
    assert result.goal == "2-A"


def test_goal_tie_breaks_to_lowest_num(level1: Level) -> None:
    """From 1-A the furthest rooms are 1-D and 1-E (both dist 2); lowest num → 1-D."""
    result = auto_assign_loop_rooms(level1)
    assert result.goal == "1-D"


# ---------------------------------------------------------------------------
# Slice 1 — path_a (shortest path)
# ---------------------------------------------------------------------------

def test_path_a_is_shortest_path_entry_to_goal(level1: Level) -> None:
    """Shortest path 1-A → 1-D is [1-A, 1-B, 1-D] (2 hops)."""
    result = auto_assign_loop_rooms(level1)
    assert result.path_a == ["1-A", "1-B", "1-D"]


# ---------------------------------------------------------------------------
# Slice 1 — path_b (alternate with fewest overlapping intermediates)
# ---------------------------------------------------------------------------

def test_path_b_is_alternate_with_fewest_overlapping_rooms(level1: Level) -> None:
    """Alternate 1-A → 1-D avoids 1-B (path_a intermediate) → [1-A, 1-C, 1-E, 1-D]."""
    result = auto_assign_loop_rooms(level1)
    assert result.path_b == ["1-A", "1-C", "1-E", "1-D"]


# ---------------------------------------------------------------------------
# Slice 1 — linear fallback
# ---------------------------------------------------------------------------

def test_linear_dungeon_path_b_equals_path_a() -> None:
    """When only one path exists, path_b degrades gracefully to path_a."""
    level = _linear_level()
    result = auto_assign_loop_rooms(level)
    assert result.path_b == result.path_a
