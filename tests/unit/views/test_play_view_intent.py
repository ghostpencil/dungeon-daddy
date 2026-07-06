"""Phase 37.1.2 — Regression tests for intent preservation through PlayView.

Verifies that the intent typed in PlayerActionPanel flows through
_on_resolve_action into the ActionResolution without being dropped.
Uses real PlayerActionPanel + real RpgService to exercise the full chain.
"""
from __future__ import annotations

from dungeon_daddy.rpg.models import ActorState
from dungeon_daddy.rpg.service import RpgService
from dungeon_daddy.ui.panels.player_action_panel import PlayerActionPanel
from dungeon_daddy.views.play_view import PlayView


def _make_view() -> PlayView:
    view = PlayView.__new__(PlayView)
    view._rpg_action = PlayerActionPanel()
    view._session.set_actors([
        ActorState(
            actor_id="a1", campaign_id="c1", actor_type="pc",
            slug="hero", display_name="Hero",
        )
    ])
    view._rpg_service = RpgService()
    view._rpg_campaign_id = "c1"
    # No DM, no proposal pipeline, no dungeon — keeps the test focused
    view._dm_agent = None
    view._mem_repo = None
    view._rpg_debug = None
    view._dungeon = None
    view._state = None
    return view


def test_on_resolve_action_threads_intent_to_resolution():
    view = _make_view()
    captured: dict = {}

    def _capture(resolution):
        captured["resolution"] = resolution

    view._apply_world_reaction = _capture  # type: ignore[method-assign]

    view._on_resolve_action(
        campaign_id="c1",
        actor_id="a1",
        intent="I study the mural to resist the dungeon's seductive memory.",
        action_key="study",
        push_yourself=False,
        momentum_spend=0,
        dice_pool=2,
    )

    assert "resolution" in captured, "_apply_world_reaction was not called"
    assert captured["resolution"].intent == (
        "I study the mural to resist the dungeon's seductive memory."
    )


def test_on_resolve_action_threads_empty_intent():
    view = _make_view()
    captured: dict = {}

    def _capture(resolution):
        captured["resolution"] = resolution

    view._apply_world_reaction = _capture  # type: ignore[method-assign]

    view._on_resolve_action(
        campaign_id="c1",
        actor_id="a1",
        intent="",
        action_key="fight",
        push_yourself=False,
        momentum_spend=0,
        dice_pool=1,
    )

    assert "resolution" in captured
    assert captured["resolution"].intent == ""
