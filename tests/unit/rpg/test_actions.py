from dungeon_daddy.rpg.actions import resolve_action
from dungeon_daddy.rpg.models import ActionRequest, ActionResolution


def _request(**kwargs) -> ActionRequest:  # type: ignore[no-untyped-def]
    defaults = dict(
        campaign_id="c1",
        actor_id="a1",
        action_key="study",
        dice_pool=2,
    )
    defaults.update(kwargs)
    return ActionRequest(**defaults)


def test_resolve_action_returns_resolution() -> None:
    req = _request()
    result = resolve_action(req, fixed=[5, 2])
    assert isinstance(result, ActionResolution)
    assert result.outcome == "partial"
    assert result.action_key == "study"
    assert result.campaign_id == "c1"
    assert result.actor_id == "a1"


def test_push_yourself_adds_one_die_and_costs_stress() -> None:
    req = _request(dice_pool=1, push_yourself=True)
    result = resolve_action(req, fixed=[4, 5])  # 2 dice = 1 base + 1 push
    assert len(result.dice_rolled) == 2
    assert result.stress_cost == 1


def test_momentum_spend_adds_dice() -> None:
    req = _request(dice_pool=1, momentum_spend=2)
    result = resolve_action(req, fixed=[6, 3, 4])  # 3 dice = 1 base + 2 momentum
    assert len(result.dice_rolled) == 3
    assert result.outcome == "full"


def test_intent_passes_through_to_resolution() -> None:
    req = _request(intent="convince the warden to stand down")
    result = resolve_action(req, fixed=[4])
    assert result.intent == "convince the warden to stand down"


def test_none_intent_passes_through() -> None:
    req = _request()
    result = resolve_action(req, fixed=[4])
    assert result.intent is None
