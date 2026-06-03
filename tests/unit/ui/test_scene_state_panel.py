"""Unit tests for SceneStatePanel — Phase 30 step 30-3."""
from __future__ import annotations

from dungeon_daddy.rpg.models import ActionResolution, ActorState, ClockState


def _panel():
    from dungeon_daddy.ui.panels.scene_state_panel import SceneStatePanel
    return SceneStatePanel()


def _clock(**kw) -> ClockState:
    defaults = dict(
        clock_id="ck1",
        campaign_id="c1",
        label="Patrol Arrives",
        segments=6,
        filled=2,
        status="active",
    )
    defaults.update(kw)
    return ClockState(**defaults)


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


def _resolution(**kw) -> ActionResolution:
    defaults = dict(
        resolution_id="r1",
        campaign_id="c1",
        actor_id="a1",
        action_key="hunt",
        dice_rolled=[4, 5],
        outcome="full",
    )
    defaults.update(kw)
    return ActionResolution(**defaults)


# ---------------------------------------------------------------------------
# Bullet 1 — no scene: placeholder state
# ---------------------------------------------------------------------------

def test_no_scene_on_init():
    panel = _panel()
    assert panel._scene_title is None
    assert panel._location_slug is None


# ---------------------------------------------------------------------------
# Bullet 2 — scene title and location slug
# ---------------------------------------------------------------------------

def test_set_scene_stores_title_and_slug():
    panel = _panel()
    panel.set_scene(title="The Ossuary", location_slug="ossuary-lvl2")
    assert panel._scene_title == "The Ossuary"
    assert panel._location_slug == "ossuary-lvl2"


def test_set_scene_none_clears():
    panel = _panel()
    panel.set_scene(title="X", location_slug="y")
    panel.set_scene(None, None)
    assert panel._scene_title is None
    assert panel._location_slug is None


# ---------------------------------------------------------------------------
# Bullet 3 — open clocks with label, filled/segments, status
# ---------------------------------------------------------------------------

def test_clocks_default_empty():
    panel = _panel()
    assert panel._clocks == []


def test_set_clocks_stores_open_clocks():
    panel = _panel()
    active = _clock(label="Patrol Arrives", filled=2, segments=6, status="active")
    done = _clock(clock_id="ck2", label="Heist Done", filled=4, segments=4, status="completed")
    panel.set_clocks([active, done])
    open_clocks = [c for c in panel._clocks if c.status == "active"]
    assert len(open_clocks) == 1
    assert open_clocks[0].label == "Patrol Arrives"
    assert open_clocks[0].filled == 2
    assert open_clocks[0].segments == 6


# ---------------------------------------------------------------------------
# Bullet 4 — active actors list
# ---------------------------------------------------------------------------

def test_actors_default_empty():
    panel = _panel()
    assert panel._actors == []


def test_set_actors_stores_display_names():
    panel = _panel()
    a1 = _actor(display_name="Elara")
    a2 = _actor(actor_id="a2", display_name="Korrak")
    panel.set_actors([a1, a2])
    names = [a.display_name for a in panel._actors]
    assert "Elara" in names
    assert "Korrak" in names


# ---------------------------------------------------------------------------
# Bullet 5 — recent action resolutions
# ---------------------------------------------------------------------------

def test_resolutions_default_empty():
    panel = _panel()
    assert panel._recent_resolutions == []


def test_set_recent_resolutions_stores_entries():
    panel = _panel()
    r1 = _resolution(outcome="full", actor_id="a1", action_key="hunt")
    r2 = _resolution(resolution_id="r2", outcome="partial", actor_id="a2", action_key="skirmish")
    panel.set_recent_resolutions([r1, r2])
    assert len(panel._recent_resolutions) == 2
    assert panel._recent_resolutions[0].outcome == "full"
    assert panel._recent_resolutions[1].action_key == "skirmish"


# ---------------------------------------------------------------------------
# Bullet 6 — risk/effect selector
# ---------------------------------------------------------------------------

def test_risk_effect_defaults():
    panel = _panel()
    assert panel._risk == "moderate"
    assert panel._effect == "standard"


def test_set_risk_stores_value():
    panel = _panel()
    panel.set_risk("high")
    assert panel._risk == "high"


def test_set_effect_stores_value():
    panel = _panel()
    panel.set_effect("limited")
    assert panel._effect == "limited"
