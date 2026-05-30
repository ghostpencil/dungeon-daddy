"""Tests for dungeon_daddy.map.dungeon_layout.route_orthogonal."""
from __future__ import annotations

from dungeon_daddy.data.models import Connection
from dungeon_daddy.map.dungeon_layout.models import Port, RoomRect
from dungeon_daddy.map.dungeon_layout.route_orthogonal import route_connections


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _conn(from_id: str, to_id: str) -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": "door"})


def _room(room_id: str, x: float, y: float, w: float = 100.0, h: float = 60.0) -> RoomRect:
    return RoomRect(room_id=room_id, x=x, y=y, w=w, h=h)


def _port(room_id: str, side: str, x: float, y: float) -> Port:
    return Port(room_id=room_id, side=side, x=x, y=y)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cycle 1 — collinear rooms produce a straight 2-point route
# ---------------------------------------------------------------------------

def test_horizontal_connection_produces_straight_route() -> None:
    """Two rooms on the same horizontal axis: straight line, 0 bends."""
    rooms = {
        "a": _room("a", x=0,   y=0),
        "b": _room("b", x=200, y=0),
    }
    # port on right edge of "a", left edge of "b"
    ports = {
        "a__b": _port("a", "right", 100.0, 30.0),
        "b__a": _port("b", "left",  200.0, 30.0),
    }
    conns = [_conn("a", "b")]

    edges = route_connections(rooms, ports, conns)

    assert len(edges) == 1
    edge = edges[0]
    assert edge.bend_count == 0
    assert len(edge.points) == 2
    assert edge.points[0] == (100.0, 30.0)
    assert edge.points[-1] == (200.0, 30.0)


# ---------------------------------------------------------------------------
# Cycle 2 — offset rooms produce an L-shaped route (3 points, 1 bend)
# ---------------------------------------------------------------------------

def test_offset_rooms_produce_l_shaped_route() -> None:
    """Rooms offset in both x and y: route has exactly 1 bend (3 points)."""
    rooms = {
        "a": _room("a", x=0,   y=0),
        "b": _room("b", x=200, y=200),
    }
    # src on right edge of "a", tgt on left edge of "b"
    ports = {
        "a__b": _port("a", "right", 100.0, 30.0),
        "b__a": _port("b", "left",  200.0, 230.0),
    }
    conns = [_conn("a", "b")]

    edges = route_connections(rooms, ports, conns)

    edge = edges[0]
    assert edge.bend_count == 1
    assert len(edge.points) == 3
    assert edge.points[0] == (100.0, 30.0)
    assert edge.points[-1] == (200.0, 230.0)


# ---------------------------------------------------------------------------
# Cycle 3 — best dogleg chosen by score (both are equal here; midpoint unique)
# ---------------------------------------------------------------------------

def test_both_dogleg_candidates_have_equal_length_symmetric_case() -> None:
    """Symmetric offset: both L-shapes have equal total length.
    Verify the router returns a valid 3-point route regardless of which wins.
    """
    rooms = {
        "a": _room("a", x=0,   y=0),
        "b": _room("b", x=100, y=100),
    }
    ports = {
        "a__b": _port("a", "right", 50.0, 30.0),
        "b__a": _port("b", "left",  100.0, 130.0),
    }
    conns = [_conn("a", "b")]

    edges = route_connections(rooms, ports, conns)
    edge = edges[0]

    # Either H-then-V or V-then-H is fine; must be exactly 3 points
    assert edge.bend_count == 1
    # The intermediate point must be either (100, 30) or (50, 130)
    mid = edge.points[1]
    assert mid in {(100.0, 30.0), (50.0, 130.0)}


# ---------------------------------------------------------------------------
# Cycle 4 — obstacle room forces selection of the non-crossing route
# ---------------------------------------------------------------------------

def test_obstacle_room_forces_non_crossing_route() -> None:
    """An obstacle room blocks the H-then-V dogleg; V-then-H wins instead.

    Layout:
      "a" right-port at (100, 30)
      "b" left-port  at (200, 230)
      "block" at x=120..160, y=20..40 — inflated left=104 > 100 so V-then-H
        segment at x=100 misses it; H-then-V segment at y=30 hits it.

      H-then-V: (100,30)→(200,30)→(200,230) — segment at y=30 crosses block
      V-then-H: (100,30)→(100,230)→(200,230) — x=100 < inflated block left=104
    """
    rooms = {
        "a":     _room("a",     x=0,   y=0,   w=100, h=60),
        "b":     _room("b",     x=200, y=200, w=100, h=60),
        "block": _room("block", x=120, y=20,  w=40,  h=20),
    }
    ports = {
        "a__b": _port("a", "right", 100.0, 30.0),
        "b__a": _port("b", "left",  200.0, 230.0),
    }
    conns = [_conn("a", "b")]

    edges = route_connections(rooms, ports, conns)
    edge = edges[0]

    # V-then-H should win: intermediate point is at (100, 230)
    assert edge.points[1] == (100.0, 230.0)


# ---------------------------------------------------------------------------
# Cycle 5 — empty connections list produces empty result
# ---------------------------------------------------------------------------

def test_empty_connections_returns_empty_list() -> None:
    rooms = {"a": _room("a", x=0, y=0)}
    ports: dict[str, Port] = {}
    conns: list[Connection] = []

    edges = route_connections(rooms, ports, conns)

    assert edges == []


# ---------------------------------------------------------------------------
# Cycle 6 — connection_id in RoutedEdge matches "{from_room}→{to_room}"
# ---------------------------------------------------------------------------

def test_routed_edge_connection_id_format() -> None:
    rooms = {
        "hall": _room("hall", x=0,   y=0),
        "boss": _room("boss", x=200, y=0),
    }
    ports = {
        "hall__boss": _port("hall", "right", 100.0, 30.0),
        "boss__hall": _port("boss", "left",  200.0, 30.0),
    }
    conns = [_conn("hall", "boss")]

    edges = route_connections(rooms, ports, conns)

    assert edges[0].connection_id == "hall→boss"


# ---------------------------------------------------------------------------
# Cycle 7 — source_port and target_port store the port dict keys
# ---------------------------------------------------------------------------

def test_routed_edge_port_keys_match_input_ports() -> None:
    rooms = {
        "a": _room("a", x=0,   y=0),
        "b": _room("b", x=200, y=0),
    }
    ports = {
        "a__b": _port("a", "right", 100.0, 30.0),
        "b__a": _port("b", "left",  200.0, 30.0),
    }
    conns = [_conn("a", "b")]

    edges = route_connections(rooms, ports, conns)
    edge = edges[0]

    assert edge.source_port == "a__b"
    assert edge.target_port == "b__a"
