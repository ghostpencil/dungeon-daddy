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
        status="active",
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
    e = _entry(title="Elara", summary="A fighter.", status="active", importance=8)
    panel.set_entries([e])
    panel.set_search_query("")
    result = panel.get_results()[0]
    assert result.title == "Elara"
    assert result.summary == "A fighter."
    assert result.status == "active"
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
