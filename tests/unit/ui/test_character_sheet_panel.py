"""Unit tests for CharacterSheetPanel — Phase 30 step 30-2."""
from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Slice 9 — inventory: set_inventory / state storage
# ---------------------------------------------------------------------------

def test_inventory_defaults_empty():
    panel = _panel()
    assert panel._kits == []
    assert panel._dungeon_items == []
    assert panel._equipped == []


def test_set_inventory_stores_kits():
    panel = _panel()
    kits = [{"slug": "healer-kit", "display_name": "Healer Kit", "charges_current": 2, "charges_max": 3}]
    panel.set_inventory(kits=kits, dungeon_items=[], equipped=[])
    assert len(panel._kits) == 1
    assert panel._kits[0]["slug"] == "healer-kit"
    assert panel._kits[0]["charges_current"] == 2
    assert panel._kits[0]["charges_max"] == 3


def test_set_inventory_stores_dungeon_items():
    panel = _panel()
    items = [
        {"slug": "amulet", "display_name": "Amulet of Truth", "status": "active", "level_bound": True},
        {"slug": "coin", "display_name": "Strange Coin", "status": "active", "level_bound": False},
    ]
    panel.set_inventory(kits=[], dungeon_items=items, equipped=[])
    assert len(panel._dungeon_items) == 2
    assert panel._dungeon_items[0]["level_bound"] is True
    assert panel._dungeon_items[1]["level_bound"] is False


def test_set_inventory_replaces_previous():
    panel = _panel()
    panel.set_inventory(
        kits=[{"slug": "k1", "display_name": "K1", "charges_current": 1, "charges_max": 2}],
        dungeon_items=[{"slug": "d1", "display_name": "D1", "status": "active", "level_bound": False}],
        equipped=[],
    )
    panel.set_inventory(kits=[], dungeon_items=[], equipped=[])
    assert panel._kits == []
    assert panel._dungeon_items == []


def test_set_inventory_stores_equipped_with_features():
    panel = _panel()
    gear = [
        {
            "slug": "iron-sword",
            "display_name": "Iron Sword",
            "features": [{"feature_type": "rating_modifier", "action_key": "fight", "modifier": 1}],
        },
        {
            "slug": "shadow-cloak",
            "display_name": "Shadow Cloak",
            "features": [{"feature_type": "new_action", "action_key": "vanish", "modifier": None}],
        },
    ]
    panel.set_inventory(kits=[], dungeon_items=[], equipped=gear)
    assert len(panel._equipped) == 2
    assert panel._equipped[0]["features"][0]["action_key"] == "fight"
    assert panel._equipped[0]["features"][0]["modifier"] == 1
    assert panel._equipped[1]["features"][0]["feature_type"] == "new_action"
