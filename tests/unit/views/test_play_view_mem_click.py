"""Tests for Phase 37 — MEM tab click routing in PlayView."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dungeon_daddy.memory.models import MemoryEntry
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.ui.panels.memory_inspector_panel import MemoryInspectorPanel

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


def _entry(**kw) -> MemoryEntry:
    defaults = dict(
        memory_id="m1",
        campaign_id="camp-1",
        type="event",
        title="Draft Memory",
        summary="Something happened.",
        status="draft",
        importance=5,
    )
    defaults.update(kw)
    return MemoryEntry(**defaults)


def _make_view(tmp_path: Path):
    from dungeon_daddy.views.play_view import PlayView

    mem_repo = MemoryRepository(tmp_path / "test.duckdb")
    mem_repo.initialize_schema(MIGRATIONS_DIR)
    mem_repo.save_campaign("camp-1", "test-campaign", "Test Campaign")

    view = PlayView.__new__(PlayView)
    view._mem_repo = mem_repo
    view._rpg_campaign_id = "camp-1"
    view._rpg_memory = MemoryInspectorPanel()
    return view


# ---------------------------------------------------------------------------
# _persist_pending_memory_commit
# ---------------------------------------------------------------------------

def test_persist_commit_updates_status_in_db(tmp_path):
    view = _make_view(tmp_path)
    view._mem_repo.save_memory_entry("m1", "camp-1", "event", "Title", "Summary", status="draft")

    e = _entry(memory_id="m1", status="approved")
    view._rpg_memory._pending_commit = e

    view._persist_pending_memory_commit()

    rows = view._mem_repo.get_memory_entries_by_campaign("camp-1")
    assert rows[0]["status"] == "approved"


def test_persist_commit_clears_pending(tmp_path):
    view = _make_view(tmp_path)
    view._mem_repo.save_memory_entry("m1", "camp-1", "event", "T", "S", status="draft")
    e = _entry(memory_id="m1", status="approved")
    view._rpg_memory._pending_commit = e

    view._persist_pending_memory_commit()

    assert view._rpg_memory._pending_commit is None


def test_persist_commit_noop_when_nothing_pending(tmp_path):
    view = _make_view(tmp_path)
    view._persist_pending_memory_commit()  # must not raise


def test_persist_commit_noop_when_no_repo(tmp_path):
    view = _make_view(tmp_path)
    view._mem_repo = None
    e = _entry(memory_id="m1", status="approved")
    view._rpg_memory._pending_commit = e
    view._persist_pending_memory_commit()  # must not raise


# ---------------------------------------------------------------------------
# _handle_mem_click — button hits
# ---------------------------------------------------------------------------

def test_handle_mem_click_approve_button(tmp_path):
    view = _make_view(tmp_path)
    view._mem_repo.save_memory_entry("m1", "camp-1", "event", "T", "S", status="draft")

    e = _entry(memory_id="m1", status="draft")
    view._rpg_memory.set_entries([e])
    view._rpg_memory.select_entry(e)
    view._rpg_memory._update_layout(0.0, 0.0, 300.0, 800.0, [e])

    bx1, by1, bx2, by2 = view._rpg_memory._button_rects["approve"]
    view._handle_mem_click((bx1 + bx2) / 2, (by1 + by2) / 2)

    rows = view._mem_repo.get_memory_entries_by_campaign("camp-1")
    assert rows[0]["status"] == "approved"


def test_handle_mem_click_reject_button(tmp_path):
    view = _make_view(tmp_path)
    view._mem_repo.save_memory_entry("m1", "camp-1", "event", "T", "S", status="draft")

    e = _entry(memory_id="m1", status="draft")
    view._rpg_memory.set_entries([e])
    view._rpg_memory.select_entry(e)
    view._rpg_memory._update_layout(0.0, 0.0, 300.0, 800.0, [e])

    bx1, by1, bx2, by2 = view._rpg_memory._button_rects["reject"]
    view._handle_mem_click((bx1 + bx2) / 2, (by1 + by2) / 2)

    rows = view._mem_repo.get_memory_entries_by_campaign("camp-1")
    assert rows[0]["status"] == "rejected"


# ---------------------------------------------------------------------------
# _handle_mem_click — entry selection
# ---------------------------------------------------------------------------

def test_handle_mem_click_selects_entry(tmp_path):
    view = _make_view(tmp_path)
    e = _entry(memory_id="m1")
    view._rpg_memory.set_entries([e])
    view._rpg_memory._update_layout(0.0, 0.0, 300.0, 800.0, [e])

    _, y1, _, y2, _ = view._rpg_memory._entry_rects[0]
    view._handle_mem_click(150.0, (y1 + y2) / 2)

    assert view._rpg_memory._selected is e


def test_handle_mem_click_miss_does_nothing(tmp_path):
    view = _make_view(tmp_path)
    e = _entry(memory_id="m1")
    view._rpg_memory.set_entries([e])
    view._rpg_memory._update_layout(0.0, 0.0, 300.0, 800.0, [e])

    view._handle_mem_click(150.0, 795.0)  # above list

    assert view._rpg_memory._selected is None
