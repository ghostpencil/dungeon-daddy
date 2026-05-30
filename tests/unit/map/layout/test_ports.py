"""Tests for dungeon_daddy.map.dungeon_layout.ports."""
from __future__ import annotations

from dungeon_daddy.data.models import Connection
from dungeon_daddy.map.dungeon_layout.models import RoomRect
from dungeon_daddy.map.dungeon_layout.ports import generate_ports


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _conn(from_id: str, to_id: str) -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": "door"})


def _room(room_id: str, x: float, y: float, w: float = 120.0, h: float = 80.0) -> RoomRect:
    return RoomRect(room_id=room_id, x=x, y=y, w=w, h=h)


# ---------------------------------------------------------------------------
# Cycle 1 — port side is "right" when target is clearly to the right
# ---------------------------------------------------------------------------

def test_port_side_right_when_target_is_to_the_right() -> None:
    rooms = {
        "a": _room("a", x=0, y=0),
        "b": _room("b", x=300, y=0),
    }
    conns = [_conn("a", "b")]

    ports = generate_ports(rooms, conns)

    assert ports["a__b"].side == "right"


# ---------------------------------------------------------------------------
# Cycle 2 — port side is "left" when target is clearly to the left
# ---------------------------------------------------------------------------

def test_port_side_left_when_target_is_to_the_left() -> None:
    rooms = {
        "a": _room("a", x=300, y=0),
        "b": _room("b", x=0, y=0),
    }
    conns = [_conn("a", "b")]

    ports = generate_ports(rooms, conns)

    assert ports["a__b"].side == "left"


# ---------------------------------------------------------------------------
# Cycle 3 — port side is "top" when target is clearly above
# ---------------------------------------------------------------------------

def test_port_side_top_when_target_is_above() -> None:
    rooms = {
        "a": _room("a", x=0, y=0),
        "b": _room("b", x=0, y=300),
    }
    conns = [_conn("a", "b")]

    ports = generate_ports(rooms, conns)

    assert ports["a__b"].side == "top"


# ---------------------------------------------------------------------------
# Cycle 4 — port side is "bottom" when target is clearly below
# ---------------------------------------------------------------------------

def test_port_side_bottom_when_target_is_below() -> None:
    rooms = {
        "a": _room("a", x=0, y=300),
        "b": _room("b", x=0, y=0),
    }
    conns = [_conn("a", "b")]

    ports = generate_ports(rooms, conns)

    assert ports["a__b"].side == "bottom"


# ---------------------------------------------------------------------------
# Cycle 5 — port coords snap to room edge midpoint
# ---------------------------------------------------------------------------

def test_port_coords_snapped_to_edge_midpoint() -> None:
    # room "a": x=0, y=0, w=120, h=80  →  right edge at x=120, cy=40
    rooms = {
        "a": _room("a", x=0, y=0, w=120, h=80),
        "b": _room("b", x=300, y=0),
    }
    conns = [_conn("a", "b")]

    ports = generate_ports(rooms, conns)

    p = ports["a__b"]
    assert p.x == 120.0  # room.right
    assert p.y == 40.0   # room.cy


# ---------------------------------------------------------------------------
# Cycle 6 — dict has two entries per connection (source + target)
# ---------------------------------------------------------------------------

def test_one_connection_produces_two_port_entries() -> None:
    rooms = {
        "a": _room("a", x=0, y=0),
        "b": _room("b", x=300, y=0),
    }
    conns = [_conn("a", "b")]

    ports = generate_ports(rooms, conns)

    assert "a__b" in ports
    assert "b__a" in ports
    assert len(ports) == 2


# ---------------------------------------------------------------------------
# Cycle 7 — multiple connections produce all expected endpoint keys
# ---------------------------------------------------------------------------

def test_multiple_connections_all_endpoints_present() -> None:
    rooms = {
        "hub": _room("hub", x=150, y=150),
        "s1":  _room("s1",  x=0,   y=150),
        "s2":  _room("s2",  x=300, y=150),
        "s3":  _room("s3",  x=150, y=0),
    }
    conns = [_conn("hub", "s1"), _conn("hub", "s2"), _conn("hub", "s3")]

    ports = generate_ports(rooms, conns)

    expected_keys = {"hub__s1", "s1__hub", "hub__s2", "s2__hub", "hub__s3", "s3__hub"}
    assert set(ports.keys()) == expected_keys
