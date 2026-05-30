"""Tests for dungeon_daddy.map.dungeon_layout.seed_layout."""
from __future__ import annotations

from dungeon_daddy.data.models import Connection, Level, Room
from dungeon_daddy.map.dungeon_layout.seed_layout import compute_seed_layout


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_room(room_id: str, name: str = "") -> Room:
    return Room(
        id=room_id,
        num=0,
        name=name or room_id,
        x=0, y=0, w=10, h=10,
        type="room",
        note="",
    )


def _make_conn(from_id: str, to_id: str) -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": "door"})


def _make_level(rooms: list[Room], connections: list[Connection]) -> Level:
    return Level(
        id=1,
        name="Test Level",
        summary="",
        ecology="",
        loop="",
        width=100,
        height=100,
        entries=[],
        rooms=rooms,
        connections=connections,
    )


# ---------------------------------------------------------------------------
# Cycle 1 — tracer bullet: every room is placed
# ---------------------------------------------------------------------------

def test_all_rooms_placed_freeform() -> None:
    rooms = [_make_room("r1"), _make_room("r2"), _make_room("r3")]
    level = _make_level(rooms, [])
    roles = {"r1": "entrance", "r2": "unknown", "r3": "exit"}

    result = compute_seed_layout(level, roles, "freeform")

    assert set(result.keys()) == {"r1", "r2", "r3"}


# ---------------------------------------------------------------------------
# Cycle 2 — linear: entrance is leftmost on the critical path
# ---------------------------------------------------------------------------

def test_linear_entrance_is_leftmost() -> None:
    rooms = [_make_room("r1", "Entrance Hall"), _make_room("r2"), _make_room("r3", "Boss Lair")]
    conns = [_make_conn("r1", "r2"), _make_conn("r2", "r3")]
    level = _make_level(rooms, conns)
    roles = {"r1": "entrance", "r2": "unknown", "r3": "boss"}

    result = compute_seed_layout(level, roles, "linear")

    assert result["r1"].x < result["r2"].x < result["r3"].x


# ---------------------------------------------------------------------------
# Cycle 3 — linear: no two rooms overlap
# ---------------------------------------------------------------------------

def _overlaps(a, b) -> bool:
    return (
        a.left < b.right
        and a.right > b.left
        and a.bottom < b.top
        and a.top > b.bottom
    )


def test_linear_no_overlaps() -> None:
    rooms = [
        _make_room("r1", "Entrance"),
        _make_room("r2"),
        _make_room("r3"),
        _make_room("r4", "Boss"),
    ]
    conns = [_make_conn("r1", "r2"), _make_conn("r2", "r3"), _make_conn("r3", "r4")]
    level = _make_level(rooms, conns)
    roles = {"r1": "entrance", "r2": "unknown", "r3": "unknown", "r4": "boss"}

    rects = list(compute_seed_layout(level, roles, "linear").values())

    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert not _overlaps(a, b), f"{a.room_id} overlaps {b.room_id}"


# ---------------------------------------------------------------------------
# Cycle 4 — hub-spoke: hub room is nearest to origin
# ---------------------------------------------------------------------------

def test_hub_spoke_hub_is_central() -> None:
    rooms = [
        _make_room("hub"),
        _make_room("s1"),
        _make_room("s2"),
        _make_room("s3"),
    ]
    conns = [
        _make_conn("hub", "s1"),
        _make_conn("hub", "s2"),
        _make_conn("hub", "s3"),
    ]
    level = _make_level(rooms, conns)
    roles = {"hub": "hub", "s1": "unknown", "s2": "unknown", "s3": "unknown"}

    result = compute_seed_layout(level, roles, "hub_spoke")

    hub_rect = result["hub"]
    hub_dist = (hub_rect.cx ** 2 + hub_rect.cy ** 2) ** 0.5
    for rid in ("s1", "s2", "s3"):
        r = result[rid]
        spoke_dist = (r.cx ** 2 + r.cy ** 2) ** 0.5
        assert hub_dist < spoke_dist, f"hub not closer to origin than spoke {rid}"
