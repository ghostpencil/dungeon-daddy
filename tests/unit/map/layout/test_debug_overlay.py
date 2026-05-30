"""Tests for dungeon_daddy.map.dungeon_layout.debug_overlay."""
from __future__ import annotations

from dungeon_daddy.map.dungeon_layout.debug_overlay import (
    DebugOverlay,
    build_debug_overlay,
)
from dungeon_daddy.map.dungeon_layout.models import (
    LabelBox,
    LayoutBounds,
    Port,
    RoomRect,
    RoutedEdge,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _room(room_id: str, x: float = 0.0, y: float = 0.0) -> RoomRect:
    return RoomRect(room_id=room_id, x=x, y=y, w=100.0, h=60.0)


def _bounds() -> LayoutBounds:
    return LayoutBounds(min_x=0.0, min_y=0.0, max_x=500.0, max_y=400.0)


def _edge(connection_id: str, warnings: list[str] | None = None) -> RoutedEdge:
    return RoutedEdge(
        connection_id=connection_id,
        points=[(0.0, 0.0), (100.0, 0.0), (100.0, 60.0)],
        source_port="right",
        target_port="top",
        score=50.0,
        warnings=warnings or [],
    )


# ---------------------------------------------------------------------------
# Cycle 1 — DebugOverlay model holds all expected fields
# ---------------------------------------------------------------------------

def test_debug_overlay_holds_all_fields():
    bounds = _bounds()
    room = _room("r1")
    obstacle = room.inflate(16.0)
    port = Port(room_id="r1", side="right", x=100.0, y=30.0)
    edge = _edge("r1→r2")
    label = LabelBox(connection_id="r1→r2", text="door", x=50.0, y=10.0, w=40.0, h=14.0)

    overlay = DebugOverlay(
        enabled=True,
        rooms=[room],
        obstacles=[obstacle],
        ports=[port],
        edges=[edge],
        labels=[label],
        bounds=bounds,
        illegal_crossings=["r1→r2"],
    )

    assert overlay.enabled is True
    assert overlay.rooms == [room]
    assert overlay.obstacles == [obstacle]
    assert overlay.ports == [port]
    assert overlay.edges == [edge]
    assert overlay.labels == [label]
    assert overlay.bounds == bounds
    assert overlay.illegal_crossings == ["r1→r2"]


# ---------------------------------------------------------------------------
# Cycle 2 — build_debug_overlay returns DebugOverlay with enabled=True
# ---------------------------------------------------------------------------

def test_build_debug_overlay_returns_enabled_overlay():
    rooms = {"r1": _room("r1")}
    overlay = build_debug_overlay(
        rooms=rooms,
        obstacles=[],
        ports=[],
        edges=[],
        labels=[],
        bounds=_bounds(),
    )
    assert isinstance(overlay, DebugOverlay)
    assert overlay.enabled is True
    assert len(overlay.rooms) == 1


# ---------------------------------------------------------------------------
# Cycle 3 — build_debug_overlay with no obstacles passes empty list
# ---------------------------------------------------------------------------

def test_build_debug_overlay_empty_obstacles():
    overlay = build_debug_overlay(
        rooms={"r1": _room("r1")},
        obstacles=[],
        ports=[],
        edges=[],
        labels=[],
        bounds=_bounds(),
    )
    assert overlay.obstacles == []


# ---------------------------------------------------------------------------
# Cycle 4 — build_debug_overlay extracts illegal crossings from edge warnings
# ---------------------------------------------------------------------------

def test_build_debug_overlay_extracts_illegal_crossings():
    edges = [
        _edge("r1→r2", warnings=["ILLEGAL_ROOM_CROSSING"]),
        _edge("r2→r3", warnings=[]),
        _edge("r3→r4", warnings=["ILLEGAL_ROOM_CROSSING"]),
    ]
    overlay = build_debug_overlay(
        rooms={"r1": _room("r1")},
        obstacles=[],
        ports=[],
        edges=edges,
        labels=[],
        bounds=_bounds(),
    )
    assert overlay.illegal_crossings == ["r1→r2", "r3→r4"]


def test_build_debug_overlay_no_illegal_crossings_when_clean():
    edges = [_edge("r1→r2")]
    overlay = build_debug_overlay(
        rooms={},
        obstacles=[],
        ports=[],
        edges=edges,
        labels=[],
        bounds=_bounds(),
    )
    assert overlay.illegal_crossings == []
