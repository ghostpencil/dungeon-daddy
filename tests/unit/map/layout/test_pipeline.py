"""Tests for dungeon_daddy.map.dungeon_layout (pipeline entry point)."""
from __future__ import annotations

from dungeon_daddy.data.models import Connection, Level, Room
from dungeon_daddy.map.dungeon_layout import run_layout_pipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _room(room_id: str, name: str = "") -> Room:
    return Room(
        id=room_id, num=0, name=name or room_id,
        x=0, y=0, w=10, h=10, type="room", note="",
    )


def _conn(from_id: str, to_id: str) -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": "door"})


def _level(rooms: list[Room], connections: list[Connection]) -> Level:
    return Level(
        id=1, name="Test Level", summary="", ecology="", loop="",
        width=100, height=100, entries=[],
        rooms=rooms, connections=connections,
    )


# ---------------------------------------------------------------------------
# Cycle 1 — one RoomRect per room
# ---------------------------------------------------------------------------

def test_pipeline_returns_one_rect_per_room() -> None:
    level = _level(
        rooms=[_room("a"), _room("b"), _room("c")],
        connections=[_conn("a", "b"), _conn("b", "c")],
    )
    result = run_layout_pipeline(level)
    assert set(result.rooms.keys()) == {"a", "b", "c"}


# ---------------------------------------------------------------------------
# Cycle 2 — bounds covers all rooms
# ---------------------------------------------------------------------------

def test_pipeline_bounds_covers_all_rooms() -> None:
    level = _level(
        rooms=[_room("a"), _room("b")],
        connections=[_conn("a", "b")],
    )
    result = run_layout_pipeline(level)
    b = result.bounds
    for rect in result.rooms.values():
        assert b.min_x <= rect.x
        assert b.min_y <= rect.y
        assert b.max_x >= rect.x + rect.w
        assert b.max_y >= rect.y + rect.h


# ---------------------------------------------------------------------------
# Cycle 3 — debug overlay disabled by default
# ---------------------------------------------------------------------------

def test_pipeline_debug_overlay_disabled_by_default() -> None:
    level = _level(rooms=[_room("a")], connections=[])
    result = run_layout_pipeline(level)
    assert result.debug_overlay.enabled is False


# ---------------------------------------------------------------------------
# Cycle 4 — debug overlay contains room geometry
# ---------------------------------------------------------------------------

def test_pipeline_debug_overlay_contains_rooms() -> None:
    level = _level(
        rooms=[_room("a"), _room("b")],
        connections=[_conn("a", "b")],
    )
    result = run_layout_pipeline(level)
    overlay_ids = {r.room_id for r in result.debug_overlay.rooms}
    assert overlay_ids == {"a", "b"}


# ---------------------------------------------------------------------------
# Cycle 5 — empty level returns graceful result
# ---------------------------------------------------------------------------

def test_pipeline_empty_level_returns_empty_result() -> None:
    level = _level(rooms=[], connections=[])
    result = run_layout_pipeline(level)
    assert result.rooms == {}
    assert result.edges == []
    assert result.labels == []


# ---------------------------------------------------------------------------
# Cycle 6 — cross-level connections (stairs) are silently skipped
# ---------------------------------------------------------------------------

def test_pipeline_skips_cross_level_connections() -> None:
    """A connection to a room not in this level must not crash the pipeline."""
    level = _level(
        rooms=[_room("1-A"), _room("1-B")],
        connections=[
            _conn("1-A", "1-B"),          # intra-level — routed
            _conn("1-B", "2-A"),          # cross-level — must be skipped silently
        ],
    )
    result = run_layout_pipeline(level)
    # Only the intra-level connection should produce a routed edge
    assert len(result.edges) == 1
    assert result.edges[0].connection_id == "1-A→1-B"
