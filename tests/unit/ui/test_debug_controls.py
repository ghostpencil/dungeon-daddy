"""Unit tests for DebugControls — Phase 30 step 30-6."""
from __future__ import annotations

from unittest.mock import MagicMock

from dungeon_daddy.rpg.models import ActionRequest, ActorState, ClockState, StressTrack
from dungeon_daddy.rpg.service import RpgService


def _controls(sync_reporter=None):
    from dungeon_daddy.ui.panels.debug_controls import DebugControls
    return DebugControls(rpg_service=RpgService(), sync_reporter=sync_reporter)


def _request() -> ActionRequest:
    return ActionRequest(
        campaign_id="c1",
        actor_id="a1",
        action_key="hunt",
        dice_pool=2,
    )


def _track() -> StressTrack:
    return StressTrack(track_key="body", capacity=6, filled=0)


def _clock() -> ClockState:
    return ClockState(
        clock_id="ck1",
        campaign_id="c1",
        label="Patrol",
        segments=6,
        filled=1,
    )


# ---------------------------------------------------------------------------
# Bullet 1 — resolve_sample_action calls rpg_service and stores outcome
# ---------------------------------------------------------------------------

def test_resolve_sample_action_returns_resolution():
    ctrl = _controls()
    resolution = ctrl.resolve_sample_action(_request(), fixed=[5, 5])
    assert resolution.outcome in {"critical", "full", "partial", "miss"}


def test_resolve_sample_action_stores_last_resolution():
    ctrl = _controls()
    ctrl.resolve_sample_action(_request(), fixed=[5, 5])
    assert ctrl._last_resolution is not None
    assert ctrl._last_resolution.action_key == "hunt"


# ---------------------------------------------------------------------------
# Bullet 2 — apply_stress calls rpg_service and stores result
# ---------------------------------------------------------------------------

def test_apply_stress_updates_track():
    ctrl = _controls()
    updated = ctrl.apply_stress(actor_id="a1", campaign_id="c1", track=_track(), amount=2)
    assert updated.filled == 2


def test_apply_stress_stores_last_track():
    ctrl = _controls()
    ctrl.apply_stress(actor_id="a1", campaign_id="c1", track=_track(), amount=1)
    assert ctrl._last_stress_track is not None
    assert ctrl._last_stress_track.filled == 1


# ---------------------------------------------------------------------------
# Bullet 3 — advance_clock calls rpg_service and stores result
# ---------------------------------------------------------------------------

def test_advance_clock_increments_filled():
    ctrl = _controls()
    updated = ctrl.advance_clock(clock=_clock(), ticks=2)
    assert updated.filled == 3


def test_advance_clock_stores_last_clock():
    ctrl = _controls()
    ctrl.advance_clock(clock=_clock(), ticks=1)
    assert ctrl._last_clock is not None
    assert ctrl._last_clock.filled == 2


# ---------------------------------------------------------------------------
# Bullet 4 — generate_sync_report calls sync_reporter.check()
# ---------------------------------------------------------------------------

def test_generate_sync_report_calls_check():
    mock_reporter = MagicMock()
    mock_reporter.check.return_value = []
    ctrl = _controls(sync_reporter=mock_reporter)
    issues = ctrl.generate_sync_report()
    mock_reporter.check.assert_called_once()
    assert issues == []


def test_generate_sync_report_stores_issues():
    from dungeon_daddy.memory.sync import SyncIssue
    mock_reporter = MagicMock()
    issue = SyncIssue(kind="missing_file", memory_id="m1", path="rpg-memory/npc/x.md")
    mock_reporter.check.return_value = [issue]
    ctrl = _controls(sync_reporter=mock_reporter)
    ctrl.generate_sync_report()
    assert ctrl._last_sync_issues is not None
    assert len(ctrl._last_sync_issues) == 1
    assert ctrl._last_sync_issues[0].kind == "missing_file"


def test_generate_sync_report_no_reporter_returns_empty():
    ctrl = _controls(sync_reporter=None)
    issues = ctrl.generate_sync_report()
    assert issues == []


# ---------------------------------------------------------------------------
# Bullet 5 — create_test_memory_note creates a MemoryEntry
# ---------------------------------------------------------------------------

def test_create_test_memory_note_returns_entry():
    from dungeon_daddy.memory.models import MemoryEntry
    ctrl = _controls()
    entry = ctrl.create_test_memory_note(campaign_id="c1", title="Test Note")
    assert isinstance(entry, MemoryEntry)
    assert entry.title == "Test Note"
    assert entry.campaign_id == "c1"


def test_create_test_memory_note_stores_entry():
    ctrl = _controls()
    ctrl.create_test_memory_note(campaign_id="c1", title="Test Note")
    assert ctrl._last_memory_note is not None
    assert ctrl._last_memory_note.title == "Test Note"
