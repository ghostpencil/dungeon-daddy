"""Unit tests for FalloutPanel — Phase 30 step 30-4."""
from __future__ import annotations

from dungeon_daddy.rpg.models import FalloutRecord


def _panel():
    from dungeon_daddy.ui.panels.fallout_panel import FalloutPanel
    return FalloutPanel()


def _fallout(**kw) -> FalloutRecord:
    defaults = dict(
        fallout_id="f1",
        campaign_id="c1",
        actor_id="a1",
        track_key="body",
        severity="minor",
        title="Bruised",
        summary="Took a hit.",
        status="active",
    )
    defaults.update(kw)
    return FalloutRecord(**defaults)


# ---------------------------------------------------------------------------
# Bullet 1 — empty state when no active fallout
# ---------------------------------------------------------------------------

def test_fallout_default_empty():
    panel = _panel()
    assert panel._entries == []


# ---------------------------------------------------------------------------
# Bullet 2 — active entries render track, severity, status
# ---------------------------------------------------------------------------

def test_set_entries_stores_active_fallout():
    panel = _panel()
    f = _fallout(track_key="body", severity="moderate", status="active")
    panel.set_entries([f])
    assert len(panel._entries) == 1
    assert panel._entries[0].track_key == "body"
    assert panel._entries[0].severity == "moderate"
    assert panel._entries[0].status == "active"


# ---------------------------------------------------------------------------
# Bullet 3 — mechanical hooks shown alongside entries
# ---------------------------------------------------------------------------

def test_mechanical_hooks_accessible():
    panel = _panel()
    f = _fallout(mechanical_hooks={"penalty": "-1d to skirmish"})
    panel.set_entries([f])
    assert panel._entries[0].mechanical_hooks["penalty"] == "-1d to skirmish"


# ---------------------------------------------------------------------------
# Bullet 4 — linked memory path displayed or absent
# ---------------------------------------------------------------------------

def test_markdown_path_present():
    panel = _panel()
    f = _fallout(markdown_path="rpg-memory/fallout/bruised.md")
    panel.set_entries([f])
    assert panel._entries[0].markdown_path == "rpg-memory/fallout/bruised.md"


def test_markdown_path_absent_is_none():
    panel = _panel()
    f = _fallout(markdown_path=None)
    panel.set_entries([f])
    assert panel._entries[0].markdown_path is None


# ---------------------------------------------------------------------------
# Bullet 5 — panel updates when fallout list changes
# ---------------------------------------------------------------------------

def test_set_entries_replaces_previous():
    panel = _panel()
    panel.set_entries([_fallout(fallout_id="f1")])
    panel.set_entries([_fallout(fallout_id="f2"), _fallout(fallout_id="f3", track_key="composure")])
    assert len(panel._entries) == 2
    ids = [e.fallout_id for e in panel._entries]
    assert "f2" in ids
    assert "f3" in ids
