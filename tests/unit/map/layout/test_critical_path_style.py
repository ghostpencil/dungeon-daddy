"""Tests for dungeon_layout.critical_path_style — CriticalPathPresenter."""
from dungeon_daddy.map.dungeon_layout.critical_path_style import (
    CriticalPathPresenter,
    CriticalPathPresentationResult,
)


# ---------------------------------------------------------------------------
# Cycle 1 — config disabled → empty sets, not visually distinguished
# ---------------------------------------------------------------------------

def test_disabled_config_returns_empty_result():
    result = CriticalPathPresenter().present(
        critical_path=["R1", "R2", "R3"],
        emphasize_critical_path=False,
    )
    assert result.is_visually_distinguished is False
    assert result.critical_path_room_ids == set()
    assert result.critical_path_connection_ids == set()
    assert result.warnings == []


# ---------------------------------------------------------------------------
# Cycle 2 — config enabled + path → rooms flagged, is_visually_distinguished=True
# ---------------------------------------------------------------------------

def test_enabled_config_with_path_flags_rooms():
    result = CriticalPathPresenter().present(
        critical_path=["R1", "R2", "R3"],
        emphasize_critical_path=True,
    )
    assert result.is_visually_distinguished is True
    assert result.critical_path_room_ids == {"R1", "R2", "R3"}
    assert result.warnings == []


# ---------------------------------------------------------------------------
# Cycle 3 — config enabled + no path → CRITICAL_PATH_NOT_DISTINGUISHED warning
# ---------------------------------------------------------------------------

def test_enabled_config_no_path_emits_warning():
    result = CriticalPathPresenter().present(
        critical_path=None,
        emphasize_critical_path=True,
    )
    assert result.is_visually_distinguished is False
    assert result.critical_path_room_ids == set()
    assert "CRITICAL_PATH_NOT_DISTINGUISHED" in result.warnings


# ---------------------------------------------------------------------------
# Cycle 4 — consecutive path rooms produce flagged connection IDs
# ---------------------------------------------------------------------------

def test_connections_between_path_rooms_are_flagged():
    result = CriticalPathPresenter().present(
        critical_path=["R1", "R2", "R3"],
        emphasize_critical_path=True,
    )
    assert "R1→R2" in result.critical_path_connection_ids
    assert "R2→R3" in result.critical_path_connection_ids


# ---------------------------------------------------------------------------
# Cycle 5 — non-critical-path rooms absent from flagged sets
# ---------------------------------------------------------------------------

def test_non_path_rooms_not_in_flagged_set():
    result = CriticalPathPresenter().present(
        critical_path=["R1", "R2"],
        emphasize_critical_path=True,
    )
    assert "R3" not in result.critical_path_room_ids
    assert "R2→R3" not in result.critical_path_connection_ids
