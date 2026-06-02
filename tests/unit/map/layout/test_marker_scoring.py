"""Tests for dungeon_layout.marker_scoring — compute_marker_feedback."""
from __future__ import annotations

import json
from pathlib import Path

from dungeon_daddy.data.models import Dungeon, Level, Room
from dungeon_daddy.map.dungeon_layout.marker_scoring import compute_marker_feedback

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _load_level(dungeon_name: str, level_idx: int) -> Level:
    path = Path(__file__).parent.parent.parent.parent / "fixtures" / f"{dungeon_name}.json"
    dungeon = Dungeon.model_validate(json.loads(path.read_text(encoding="utf-8")))
    return dungeon.levels[level_idx]


def _minimal_level() -> Level:
    """Level with no connections and one plain room (no special role)."""
    return Level(
        id=99,
        name="Test Level",
        summary="",
        ecology="",
        loop="",
        width=100,
        height=100,
        entries=[],
        rooms=[
            Room(id="R1", num=1, name="Room", x=0, y=0, w=10, h=10, type="room", note=""),
        ],
        connections=[],
    )


# ---------------------------------------------------------------------------
# Cycle 1 — returns dict with required keys for minimal level
# ---------------------------------------------------------------------------

def test_compute_marker_feedback_returns_dict_with_required_keys():
    level = _minimal_level()
    result = compute_marker_feedback(level)
    assert isinstance(result, dict)
    assert "role_markers_applied" in result
    assert "connection_markers_applied" in result
    assert "marker_worthy_connections_detected" in result
    assert "marker_worthy_connections_rendered" in result
    assert "warnings" in result


# ---------------------------------------------------------------------------
# Cycle 2 — Crucible L2: marker_worthy_connections_detected == 0
# ---------------------------------------------------------------------------

def test_crucible_l2_has_no_marker_worthy_connections():
    level = _load_level("crucible", 1)  # Factory Floor = L2
    result = compute_marker_feedback(level)
    assert result["marker_worthy_connections_detected"] == 0
    assert result["connection_markers_applied"] is False


# ---------------------------------------------------------------------------
# Cycle 3 — Crucible L2: not_penalized_reason is present
# ---------------------------------------------------------------------------

def test_crucible_l2_not_penalized_reason_is_present():
    level = _load_level("crucible", 1)
    result = compute_marker_feedback(level)
    assert "not_penalized_reason" in result
    assert result["not_penalized_reason"]  # non-empty string


# ---------------------------------------------------------------------------
# Cycle 4 — Crucible L1: marker_worthy_connections_detected == 1 (locked R2→R4)
# ---------------------------------------------------------------------------

def test_crucible_l1_detects_one_marker_worthy_connection():
    level = _load_level("crucible", 0)  # The Crucible = L1
    result = compute_marker_feedback(level)
    assert result["marker_worthy_connections_detected"] == 1


# ---------------------------------------------------------------------------
# Cycle 5 — Crucible L1: connection_markers_applied True, no not_penalized_reason
# ---------------------------------------------------------------------------

def test_crucible_l1_connection_markers_applied_and_no_not_penalized_reason():
    level = _load_level("crucible", 0)
    result = compute_marker_feedback(level)
    assert result["connection_markers_applied"] is True
    assert "not_penalized_reason" not in result


# ---------------------------------------------------------------------------
# Cycle 6 — role_markers_applied True when rooms have marker-producing roles
# ---------------------------------------------------------------------------

def test_role_markers_applied_when_rooms_have_marker_roles():
    level = Level(
        id=99,
        name="Test",
        summary="",
        ecology="",
        loop="",
        width=100,
        height=100,
        entries=[],
        rooms=[
            Room(id="R1", num=1, name="Entry", x=0, y=0, w=10, h=10,
                 type="room", note="", layout_role="entrance"),
        ],
        connections=[],
    )
    result = compute_marker_feedback(level)
    assert result["role_markers_applied"] is True
