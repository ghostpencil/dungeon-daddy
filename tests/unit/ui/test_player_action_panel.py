from __future__ import annotations

from dungeon_daddy.rpg.models import ActionRequest, ActionResolution, ActorState

# ---------------------------------------------------------------------------
# Slice 5 — store_result persists formatted summary
# ---------------------------------------------------------------------------

class TestStoreResult:
    def test_store_result_saves_to_last_result(self):
        panel = _panel()
        summary = {"outcome": "full", "dice": [5, 6], "stress_cost": 0, "notes": None}
        panel.store_result(summary)
        assert panel._last_result == summary

    def test_store_result_overwrites_previous(self):
        panel = _panel()
        panel.store_result({"outcome": "miss"})
        panel.store_result({"outcome": "full"})
        assert panel._last_result["outcome"] == "full"


# ---------------------------------------------------------------------------
# Slice 6 — set_resolve_callback stores callable
# ---------------------------------------------------------------------------

class TestResolveCallback:
    def test_callback_none_on_init(self):
        panel = _panel()
        assert panel._on_resolve is None

    def test_set_resolve_callback_stores_fn(self):
        panel = _panel()
        def fn(**kw):
            return None
        panel.set_resolve_callback(fn)
        assert panel._on_resolve is fn


def _panel():
    from dungeon_daddy.ui.panels.player_action_panel import PlayerActionPanel
    return PlayerActionPanel()


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
        action_key="fight",
        dice_rolled=[4, 5, 6],
        outcome="full",
        stress_cost=0,
    )
    defaults.update(kw)
    return ActionResolution(**defaults)


# ---------------------------------------------------------------------------
# Slice 3 — _build_request constructs a valid ActionRequest
# ---------------------------------------------------------------------------

class TestBuildRequest:
    def test_basic_request(self):
        panel = _panel()
        req = panel._build_request(
            campaign_id="c1",
            actor_id="a1",
            intent="Attack the goblin",
            action_key="fight",
            push_yourself=False,
            momentum_spend=0,
            dice_pool=2,
        )
        assert isinstance(req, ActionRequest)
        assert req.actor_id == "a1"
        assert req.campaign_id == "c1"
        assert req.action_key == "fight"
        assert req.dice_pool == 2
        assert req.push_yourself is False
        assert req.momentum_spend == 0

    def test_push_yourself_flag(self):
        panel = _panel()
        req = panel._build_request(
            campaign_id="c1",
            actor_id="a1",
            intent="Push through",
            action_key="endure",
            push_yourself=True,
            momentum_spend=0,
            dice_pool=1,
        )
        assert req.push_yourself is True

    def test_momentum_spend(self):
        panel = _panel()
        req = panel._build_request(
            campaign_id="c1",
            actor_id="a1",
            intent="Careful aim",
            action_key="study",
            push_yourself=False,
            momentum_spend=2,
            dice_pool=1,
        )
        assert req.momentum_spend == 2

    def test_intent_preserved_in_request(self):
        panel = _panel()
        req = panel._build_request(
            campaign_id="c1",
            actor_id="a1",
            intent="I study the mural to resist the dungeon's seductive memory.",
            action_key="study",
            push_yourself=False,
            momentum_spend=0,
            dice_pool=1,
        )
        assert req.intent == "I study the mural to resist the dungeon's seductive memory."

    def test_empty_intent_preserved(self):
        panel = _panel()
        req = panel._build_request(
            campaign_id="c1",
            actor_id="a1",
            intent="",
            action_key="fight",
            push_yourself=False,
            momentum_spend=0,
            dice_pool=1,
        )
        assert req.intent == ""


# ---------------------------------------------------------------------------
# Slice 4 — _format_result summarises ActionResolution for display
# ---------------------------------------------------------------------------

class TestFormatResult:
    def test_outcome_key_present(self):
        panel = _panel()
        summary = panel._format_result(_resolution(outcome="full"))
        assert summary["outcome"] == "full"

    def test_dice_key_present(self):
        panel = _panel()
        summary = panel._format_result(_resolution(dice_rolled=[3, 5]))
        assert summary["dice"] == [3, 5]

    def test_stress_cost_key_present(self):
        panel = _panel()
        summary = panel._format_result(_resolution(stress_cost=1))
        assert summary["stress_cost"] == 1

    def test_miss_outcome(self):
        panel = _panel()
        summary = panel._format_result(_resolution(outcome="miss", dice_rolled=[1, 2]))
        assert summary["outcome"] == "miss"
        assert summary["dice"] == [1, 2]


# ---------------------------------------------------------------------------
# Panel state — actor list stored
# ---------------------------------------------------------------------------

class TestPanelState:
    def test_no_actors_on_init(self):
        panel = _panel()
        assert panel._actors == []

    def test_set_actors_stores_list(self):
        panel = _panel()
        actors = [_actor(actor_id="a1"), _actor(actor_id="a2", slug="rogue")]
        panel.set_actors(actors)
        assert panel._actors == actors

    def test_last_result_none_on_init(self):
        panel = _panel()
        assert panel._last_result is None
