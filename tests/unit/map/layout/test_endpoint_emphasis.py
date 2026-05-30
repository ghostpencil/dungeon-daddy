"""Tests for dungeon_layout.endpoint_emphasis — EndpointEmphasisDetector."""
from dungeon_daddy.map.dungeon_layout.endpoint_emphasis import (
    EndpointEmphasisDetector,
    EndpointEmphasisResult,
)
from dungeon_daddy.map.dungeon_layout.models import RoomRect


# ---------------------------------------------------------------------------
# Cycle 1 — empty roles/rooms → no endpoint, AMBIGUOUS_ENDPOINT_ROLE warning
# ---------------------------------------------------------------------------

def test_empty_input_gives_no_endpoint_and_ambiguous_warning():
    result = EndpointEmphasisDetector().detect(
        roles={},
        rooms={},
        connections=[],
    )
    assert result.endpoint_room_id is None
    assert result.endpoint_role is None
    assert "AMBIGUOUS_ENDPOINT_ROLE" in result.warnings


# ---------------------------------------------------------------------------
# Cycle 2 — boss room is detected as endpoint, is_emphasized=True
# ---------------------------------------------------------------------------

def test_boss_room_detected_as_endpoint():
    rooms = {"R1": RoomRect(room_id="R1", x=0, y=0, w=120, h=80)}
    result = EndpointEmphasisDetector().detect(
        roles={"R1": "boss"},
        rooms=rooms,
        connections=[],
    )
    assert result.endpoint_room_id == "R1"
    assert result.endpoint_role == "boss"
    assert result.is_emphasized is True
    assert "AMBIGUOUS_ENDPOINT_ROLE" not in result.warnings


# ---------------------------------------------------------------------------
# Cycle 3 — objective room is detected as endpoint, is_emphasized=True
# ---------------------------------------------------------------------------

def test_objective_room_detected_as_endpoint():
    rooms = {"R1": RoomRect(room_id="R1", x=0, y=0, w=120, h=80)}
    result = EndpointEmphasisDetector().detect(
        roles={"R1": "objective"},
        rooms=rooms,
        connections=[],
    )
    assert result.endpoint_room_id == "R1"
    assert result.endpoint_role == "objective"
    assert result.is_emphasized is True


# ---------------------------------------------------------------------------
# Cycle 4 — exit-family rooms are detected as endpoints, is_emphasized=True
# ---------------------------------------------------------------------------

import pytest

@pytest.mark.parametrize("role", ["exit", "descent", "elevator", "stairs"])
def test_exit_family_detected_as_endpoint(role: str):
    rooms = {"R1": RoomRect(room_id="R1", x=0, y=0, w=120, h=80)}
    result = EndpointEmphasisDetector().detect(
        roles={"R1": role},  # type: ignore[dict-item]
        rooms=rooms,
        connections=[],
    )
    assert result.endpoint_room_id == "R1"
    assert result.endpoint_role == role
    assert result.is_emphasized is True


# ---------------------------------------------------------------------------
# Cycle 5 — endpoint with well-spaced neighbor → has_sufficient_spacing=True
# ---------------------------------------------------------------------------

from dungeon_daddy.data.models import Connection as DungeonConnection


def test_endpoint_with_sufficient_spacing():
    # Boss at x=200 (right edge=320), neighbor at x=0 (right edge=120) → gap=80
    rooms = {
        "R1": RoomRect(room_id="R1", x=0, y=0, w=120, h=80),
        "R2": RoomRect(room_id="R2", x=200, y=0, w=120, h=80),
    }
    conn = DungeonConnection(from_room="R1", to_room="R2", type="door")
    result = EndpointEmphasisDetector().detect(
        roles={"R1": "unknown", "R2": "boss"},
        rooms=rooms,
        connections=[conn],
    )
    assert result.endpoint_room_id == "R2"
    assert result.has_sufficient_spacing is True
    assert "ENDPOINT_NOT_EMPHASIZED" not in result.warnings


# ---------------------------------------------------------------------------
# Cycle 6 — endpoint with too-close neighbor → has_sufficient_spacing=False
# ---------------------------------------------------------------------------

def test_endpoint_too_close_to_neighbor():
    # Boss at x=125 (right of neighbor at x=0,w=120) → gap=5, below threshold 20
    rooms = {
        "R1": RoomRect(room_id="R1", x=0, y=0, w=120, h=80),
        "R2": RoomRect(room_id="R2", x=125, y=0, w=120, h=80),
    }
    conn = DungeonConnection(from_room="R1", to_room="R2", type="door")
    result = EndpointEmphasisDetector().detect(
        roles={"R1": "unknown", "R2": "boss"},
        rooms=rooms,
        connections=[conn],
    )
    assert result.endpoint_room_id == "R2"
    assert result.has_sufficient_spacing is False
    assert "ENDPOINT_NOT_EMPHASIZED" in result.warnings


# ---------------------------------------------------------------------------
# Cycle 7 — critical path final room used as endpoint when no role match
# ---------------------------------------------------------------------------

def test_critical_path_last_room_used_as_endpoint():
    rooms = {
        "R1": RoomRect(room_id="R1", x=0, y=0, w=120, h=80),
        "R2": RoomRect(room_id="R2", x=200, y=0, w=120, h=80),
    }
    result = EndpointEmphasisDetector().detect(
        roles={"R1": "unknown", "R2": "unknown"},
        rooms=rooms,
        connections=[],
        critical_path=["R1", "R2"],
    )
    assert result.endpoint_room_id == "R2"
    assert "AMBIGUOUS_ENDPOINT_ROLE" not in result.warnings


# ---------------------------------------------------------------------------
# Cycle 8 — boss wins over objective when both present
# ---------------------------------------------------------------------------

def test_boss_wins_over_objective_when_both_present():
    rooms = {
        "R1": RoomRect(room_id="R1", x=0, y=0, w=120, h=80),
        "R2": RoomRect(room_id="R2", x=200, y=0, w=120, h=80),
    }
    result = EndpointEmphasisDetector().detect(
        roles={"R1": "objective", "R2": "boss"},
        rooms=rooms,
        connections=[],
    )
    assert result.endpoint_role == "boss"
    assert result.endpoint_room_id == "R2"
