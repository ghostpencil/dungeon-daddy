"""Unit tests for MemoryInspectorPanel — Phase 30 step 30-5."""
from __future__ import annotations

from dungeon_daddy.memory.models import MemoryEntry


def _panel():
    from dungeon_daddy.ui.panels.memory_inspector_panel import MemoryInspectorPanel
    return MemoryInspectorPanel()


def _entry(**kw) -> MemoryEntry:
    defaults = dict(
        memory_id="m1",
        campaign_id="c1",
        type="npc",
        title="Elara the Blade",
        summary="A skilled fighter.",
        status="approved",
        importance=7,
    )
    defaults.update(kw)
    return MemoryEntry(**defaults)


# ---------------------------------------------------------------------------
# Bullet 1 — panel has a search query input state
# ---------------------------------------------------------------------------

def test_search_query_default_empty():
    panel = _panel()
    assert panel._search_query == ""


def test_set_search_query_stores_value():
    panel = _panel()
    panel.set_search_query("elara")
    assert panel._search_query == "elara"


# ---------------------------------------------------------------------------
# Bullet 2 — search returns filtered entries
# ---------------------------------------------------------------------------

def test_search_filters_by_title():
    panel = _panel()
    e1 = _entry(memory_id="m1", title="Elara the Blade", tags=["npc"])
    e2 = _entry(memory_id="m2", title="The Ossuary", tags=["location"])
    panel.set_entries([e1, e2])
    panel.set_search_query("elara")
    results = panel.get_results()
    assert len(results) == 1
    assert results[0].title == "Elara the Blade"


def test_search_filters_by_tag():
    panel = _panel()
    e1 = _entry(memory_id="m1", title="Elara", tags=["npc", "ally"])
    e2 = _entry(memory_id="m2", title="Crypt Door", tags=["location"])
    panel.set_entries([e1, e2])
    panel.set_search_query("ally")
    results = panel.get_results()
    assert len(results) == 1
    assert results[0].memory_id == "m1"


def test_search_empty_query_returns_all():
    panel = _panel()
    panel.set_entries([_entry(memory_id="m1"), _entry(memory_id="m2", title="Other")])
    panel.set_search_query("")
    assert len(panel.get_results()) == 2


def test_result_fields_accessible():
    panel = _panel()
    e = _entry(title="Elara", summary="A fighter.", status="approved", importance=8)
    panel.set_entries([e])
    panel.set_search_query("")
    result = panel.get_results()[0]
    assert result.title == "Elara"
    assert result.summary == "A fighter."
    assert result.status == "approved"
    assert result.importance == 8


# ---------------------------------------------------------------------------
# Bullet 3 — selecting an entry stores it for detail view
# ---------------------------------------------------------------------------

def test_selected_default_none():
    panel = _panel()
    assert panel._selected is None


def test_select_entry_stores_entry():
    panel = _panel()
    e = _entry()
    panel.select_entry(e)
    assert panel._selected is e


def test_select_none_clears():
    panel = _panel()
    panel.select_entry(_entry())
    panel.select_entry(None)
    assert panel._selected is None


# ---------------------------------------------------------------------------
# Bullet 4 — sync warnings tracked by memory_id
# ---------------------------------------------------------------------------

def test_sync_warnings_default_empty():
    panel = _panel()
    assert panel._sync_warnings == set()


def test_set_sync_warnings_stores_ids():
    panel = _panel()
    panel.set_sync_warnings({"m1", "m3"})
    assert "m1" in panel._sync_warnings
    assert "m3" in panel._sync_warnings


def test_entry_has_sync_warning():
    panel = _panel()
    panel.set_sync_warnings({"m1"})
    assert panel.has_sync_warning("m1") is True
    assert panel.has_sync_warning("m2") is False


# ---------------------------------------------------------------------------
# Bullet 5 — empty results
# ---------------------------------------------------------------------------

def test_empty_results_when_no_match():
    panel = _panel()
    panel.set_entries([_entry(title="Elara")])
    panel.set_search_query("zzznomatch")
    assert panel.get_results() == []


# ---------------------------------------------------------------------------
# Bullet 6 — approve/reject/edit actions on selected entry
# ---------------------------------------------------------------------------

def test_approve_selected_updates_status_in_results():
    panel = _panel()
    e = _entry(memory_id="m1", status="draft")
    panel.set_entries([e])
    panel.select_entry(e)
    panel.approve_selected()
    results = panel.get_results()
    assert results[0].status == "approved"


def test_approve_selected_sets_pending_commit():
    panel = _panel()
    e = _entry(memory_id="m1", status="draft")
    panel.set_entries([e])
    panel.select_entry(e)
    panel.approve_selected()
    commit = panel.pop_pending_commit()
    assert commit is not None
    assert commit.memory_id == "m1"
    assert commit.status == "approved"


def test_reject_selected_updates_status_in_results():
    panel = _panel()
    e = _entry(memory_id="m1", status="draft")
    panel.set_entries([e])
    panel.select_entry(e)
    panel.reject_selected()
    assert panel.get_results()[0].status == "rejected"


def test_reject_selected_sets_pending_commit():
    panel = _panel()
    e = _entry(memory_id="m1", status="draft")
    panel.set_entries([e])
    panel.select_entry(e)
    panel.reject_selected()
    commit = panel.pop_pending_commit()
    assert commit is not None
    assert commit.status == "rejected"


def test_edit_selected_summary_updates_in_results():
    panel = _panel()
    e = _entry(memory_id="m1", summary="Old summary.")
    panel.set_entries([e])
    panel.select_entry(e)
    panel.edit_selected_summary("New summary.")
    assert panel.get_results()[0].summary == "New summary."


def test_edit_selected_summary_sets_pending_commit():
    panel = _panel()
    e = _entry(memory_id="m1", summary="Old.")
    panel.set_entries([e])
    panel.select_entry(e)
    panel.edit_selected_summary("Updated.")
    commit = panel.pop_pending_commit()
    assert commit is not None
    assert commit.summary == "Updated."


def test_pop_pending_commit_clears_after_pop():
    panel = _panel()
    e = _entry(memory_id="m1", status="draft")
    panel.set_entries([e])
    panel.select_entry(e)
    panel.approve_selected()
    panel.pop_pending_commit()
    assert panel.pop_pending_commit() is None


def test_pop_pending_commit_returns_none_when_nothing_pending():
    panel = _panel()
    assert panel.pop_pending_commit() is None


def test_approve_noop_when_no_selection():
    panel = _panel()
    panel.approve_selected()
    assert panel.pop_pending_commit() is None


def test_reject_noop_when_no_selection():
    panel = _panel()
    panel.reject_selected()
    assert panel.pop_pending_commit() is None


def test_edit_summary_noop_when_no_selection():
    panel = _panel()
    panel.edit_selected_summary("anything")
    assert panel.pop_pending_commit() is None


# ---------------------------------------------------------------------------
# Bullet 7 — hit-testable layout: entry rects
# ---------------------------------------------------------------------------

def test_update_layout_computes_entry_rects():
    panel = _panel()
    e1 = _entry(memory_id="m1", title="Entry One")
    e2 = _entry(memory_id="m2", title="Entry Two")
    panel._update_layout(0.0, 0.0, 300.0, 800.0, [e1, e2])
    assert len(panel._entry_rects) == 2
    x1, y1, x2, y2, entry = panel._entry_rects[0]
    assert entry is e1
    assert x1 == 0.0
    assert x2 == 300.0
    assert y2 > y1


def test_hit_entry_returns_entry_at_coords():
    panel = _panel()
    e1 = _entry(memory_id="m1", title="Entry One")
    e2 = _entry(memory_id="m2", title="Entry Two")
    panel._update_layout(0.0, 0.0, 300.0, 800.0, [e1, e2])
    # click centre of first entry rect
    _, y1, _, y2, _ = panel._entry_rects[0]
    hit = panel.hit_entry(150.0, (y1 + y2) / 2)
    assert hit is e1


def test_hit_entry_returns_none_outside_all_rects():
    panel = _panel()
    e1 = _entry(memory_id="m1")
    panel._update_layout(0.0, 0.0, 300.0, 800.0, [e1])
    # click well above all entries (y=700 is above list_top ~750)
    assert panel.hit_entry(150.0, 795.0) is None


def test_hit_button_none_when_no_selection():
    panel = _panel()
    e = _entry(memory_id="m1")
    panel._update_layout(0.0, 0.0, 300.0, 800.0, [e])
    bx1, by1, bx2, by2 = panel._button_rects["approve"]
    assert panel.hit_button((bx1 + bx2) / 2, (by1 + by2) / 2) is None


def test_hit_button_approve():
    panel = _panel()
    e = _entry(memory_id="m1")
    panel._update_layout(0.0, 0.0, 300.0, 800.0, [e])
    panel.select_entry(e)
    bx1, by1, bx2, by2 = panel._button_rects["approve"]
    assert panel.hit_button((bx1 + bx2) / 2, (by1 + by2) / 2) == "approve"


def test_hit_button_reject():
    panel = _panel()
    e = _entry(memory_id="m1")
    panel._update_layout(0.0, 0.0, 300.0, 800.0, [e])
    panel.select_entry(e)
    bx1, by1, bx2, by2 = panel._button_rects["reject"]
    assert panel.hit_button((bx1 + bx2) / 2, (by1 + by2) / 2) == "reject"


def test_hit_button_none_when_click_misses():
    panel = _panel()
    e = _entry(memory_id="m1")
    panel._update_layout(0.0, 0.0, 300.0, 800.0, [e])
    panel.select_entry(e)
    # Click in middle of panel, not in button zone
    assert panel.hit_button(150.0, 400.0) is None
