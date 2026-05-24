"""Routing quality validation for dungeon map JSON files.

Encodes the acceptance criteria from FEATURE_MAP_CONNECTION_ROUTING_2.md.
Add JSON files to tests/fixtures/ to include additional maps.

These tests define what the routing system MUST achieve after the feature
is implemented.  On the current (pre-fix) code they will fail for connections
that produce perimeter loops or large detours.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from dungeon_daddy.data.models import Dungeon, Level, Room
from dungeon_daddy.map.routing import (
    calculate_path_length,
    get_room_rect,
    route_detour,
)

# Spec constants — mirror routing.py once the feature lands
_MAX_DETOUR_RATIO      = 5.0
_ROUTE_BOUNDING_MARGIN = 4
_MAX_BEND_COUNT        = 6

_FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _room_center(room: Room) -> tuple[float, float]:
    l, b, r, t = get_room_rect(room)
    return (l + r) / 2, (b + t) / 2


def _direct_distance(a: Room, b: Room) -> float:
    ax, ay = _room_center(a)
    bx, by = _room_center(b)
    return math.hypot(bx - ax, by - ay)


def _local_bounds(
    a: Room, b: Room, margin: int = _ROUTE_BOUNDING_MARGIN
) -> tuple[float, float, float, float]:
    al, ab, ar, at = get_room_rect(a)
    bl, bb, br, bt = get_room_rect(b)
    return min(al, bl) - margin, min(ab, bb) - margin, max(ar, br) + margin, max(at, bt) + margin


def _escape_distance(path: list, bounds: tuple[float, float, float, float]) -> float:
    left, bottom, right, top = bounds
    return sum(
        max(0.0, left - x) + max(0.0, x - right) + max(0.0, bottom - y) + max(0.0, y - top)
        for x, y in path
    )


# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

def _load_all_fixtures() -> list[tuple[str, Dungeon]]:
    if not _FIXTURES_DIR.exists():
        return []
    return [
        (p.stem, Dungeon.model_validate(json.loads(p.read_text(encoding="utf-8"))))
        for p in sorted(_FIXTURES_DIR.glob("*.json"))
    ]


_ALL_FIXTURES = _load_all_fixtures()


def _connection_params() -> list:
    params = []
    for map_name, dungeon in _ALL_FIXTURES:
        for level in dungeon.levels:
            room_by_id = {r.id: r for r in level.rooms}
            for conn in level.connections:
                if conn.waypoints:
                    continue  # manual waypoints override routing; skip
                fr = room_by_id.get(conn.from_room)
                tr = room_by_id.get(conn.to_room)
                if fr is None or tr is None:
                    continue
                cid = f"{map_name}/L{level.id}/{conn.from_room}→{conn.to_room}"
                params.append(pytest.param(level, fr, tr, id=cid))
    return params


_PARAMS = _connection_params()

if not _PARAMS:
    pytest.skip(
        "No routing fixtures found in tests/fixtures/ — add at least one dungeon JSON "
        "to exercise the routing validation tests.",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("level,from_room,to_room", _PARAMS)
def test_route_stays_within_local_bounds(
    level: Level, from_room: Room, to_room: Room
) -> None:
    """Detour waypoints must not escape the local bounding region of the two rooms.

    This is the primary acceptance criterion: fixes the perimeter-loop bug where
    unclamped waypoints send routes far beyond the area of the connected rooms.
    """
    path = route_detour(from_room, to_room, level.rooms)
    bounds = _local_bounds(from_room, to_room)
    escape = _escape_distance(path, bounds)
    assert escape == pytest.approx(0.0), (
        f"Route escapes local bounds {bounds} by {escape:.1f} grid units.\n"
        f"  from={from_room.id} ({from_room.name}), to={to_room.id} ({to_room.name})\n"
        f"  path={path}"
    )


@pytest.mark.parametrize("level,from_room,to_room", _PARAMS)
def test_detour_ratio_within_limit(
    level: Level, from_room: Room, to_room: Room
) -> None:
    """Routed path length must not exceed MAX_DETOUR_RATIO × direct room distance."""
    path = route_detour(from_room, to_room, level.rooms)
    dd = _direct_distance(from_room, to_room)
    if dd < 1.0:
        return  # adjacent/overlapping rooms — ratio is not meaningful
    length = calculate_path_length(path)
    ratio = length / dd
    assert ratio <= _MAX_DETOUR_RATIO, (
        f"detour_ratio={ratio:.2f} exceeds limit of {_MAX_DETOUR_RATIO}.\n"
        f"  from={from_room.id} ({from_room.name}), to={to_room.id} ({to_room.name})\n"
        f"  path_length={length:.1f}, direct={dd:.1f}\n"
        f"  path={path}"
    )


@pytest.mark.parametrize("level,from_room,to_room", _PARAMS)
def test_bend_count_within_limit(
    level: Level, from_room: Room, to_room: Room
) -> None:
    """A routed path must not have more than MAX_BEND_COUNT intermediate waypoints."""
    path = route_detour(from_room, to_room, level.rooms)
    bends = max(0, len(path) - 2)
    assert bends <= _MAX_BEND_COUNT, (
        f"bend_count={bends} exceeds limit of {_MAX_BEND_COUNT}.\n"
        f"  from={from_room.id} ({from_room.name}), to={to_room.id} ({to_room.name})\n"
        f"  path={path}"
    )
