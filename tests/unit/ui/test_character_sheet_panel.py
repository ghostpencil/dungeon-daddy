"""Unit tests for CharacterSheetPanel — Phase 30 step 30-2."""
from __future__ import annotations

import pytest

from dungeon_daddy.rpg.models import ActorState, FalloutRecord, StressTrack


def _panel():
    from dungeon_daddy.ui.panels.character_sheet_panel import CharacterSheetPanel
    return CharacterSheetPanel()


def _actor(**kw) -> ActorState:
    defaults = dict(
        actor_id="a1",
        campaign_id="c1",
        actor_type="pc",
        slug="hero",
        display_name="Elara",
    )
    defaults.update(kw)
    return ActorState(**defaults)


def _fallout(**kw) -> FalloutRecord:
    defaults = dict(
        fallout_id="f1",
        campaign_id="c1",
        actor_id="a1",
        track_key="body",
        severity="minor",
        title="Bruised",
        summary="Took a hit.",
    )
    defaults.update(kw)
    return FalloutRecord(**defaults)


# ---------------------------------------------------------------------------
# Bullet 1 — no actor selected: placeholder state
# ---------------------------------------------------------------------------

def test_no_actor_on_init():
    panel = _panel()
    assert panel._actor is None


# ---------------------------------------------------------------------------
# Bullet 2 — set_actor stores display name and type
# ---------------------------------------------------------------------------

def test_set_actor_stores_actor():
    panel = _panel()
    actor = _actor(display_name="Elara", actor_type="pc")
    panel.set_actor(actor)
    assert panel._actor is actor
    assert panel._actor.display_name == "Elara"
    assert panel._actor.actor_type == "pc"


def test_set_actor_none_clears():
    panel = _panel()
    panel.set_actor(_actor())
    panel.set_actor(None)
    assert panel._actor is None


# ---------------------------------------------------------------------------
# Bullet 3 — action ratings accessible from actor
# ---------------------------------------------------------------------------

def test_action_ratings_from_actor():
    panel = _panel()
    actor = _actor(actions={"hunt": 2, "skirmish": 1})
    panel.set_actor(actor)
    assert panel._actor.actions["hunt"] == 2
    assert panel._actor.actions["skirmish"] == 1


# ---------------------------------------------------------------------------
# Bullet 4 — momentum field
# ---------------------------------------------------------------------------

def test_momentum_default_zero():
    panel = _panel()
    assert panel._momentum == 0


def test_set_momentum_stores_value():
    panel = _panel()
    panel.set_momentum(3)
    assert panel._momentum == 3


# ---------------------------------------------------------------------------
# Bullet 5 — stress tracks accessible
# ---------------------------------------------------------------------------

def test_stress_tracks_from_actor():
    panel = _panel()
    actor = _actor(stress={
        "body": StressTrack(track_key="body", capacity=6, filled=2),
        "composure": StressTrack(track_key="composure", capacity=6, filled=0),
    })
    panel.set_actor(actor)
    assert panel._actor.stress["body"].filled == 2
    assert panel._actor.stress["body"].capacity == 6


# ---------------------------------------------------------------------------
# Bullet 6 — active fallout entries
# ---------------------------------------------------------------------------

def test_fallout_default_empty():
    panel = _panel()
    assert panel._fallout == []


def test_set_fallout_stores_active_entries():
    panel = _panel()
    active = _fallout(status="active", severity="minor")
    resolved = _fallout(fallout_id="f2", status="resolved", severity="moderate")
    panel.set_fallout([active, resolved])
    active_only = [e for e in panel._fallout if e.status == "active"]
    assert len(active_only) == 1
    assert active_only[0].severity == "minor"


# ---------------------------------------------------------------------------
# Bullet 7 — abilities accessible
# ---------------------------------------------------------------------------

def test_abilities_from_actor():
    panel = _panel()
    actor = _actor(abilities=["Battleborn", "Ghost Veil"])
    panel.set_actor(actor)
    assert "Battleborn" in panel._actor.abilities
    assert "Ghost Veil" in panel._actor.abilities


# ---------------------------------------------------------------------------
# Bullet 8 — tags accessible
# ---------------------------------------------------------------------------

def test_tags_from_actor():
    panel = _panel()
    actor = _actor(tags=["scoundrel", "blade"])
    panel.set_actor(actor)
    assert "scoundrel" in panel._actor.tags
    assert "blade" in panel._actor.tags
