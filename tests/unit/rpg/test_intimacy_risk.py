from dungeon_daddy.rpg.fallout import apply_intimacy_risk
from dungeon_daddy.rpg.models import ActorState, StressTrack


def _pc(weird_filled: int = 0) -> ActorState:
    return ActorState(
        actor_id="pc_1",
        campaign_id="camp_1",
        actor_type="pc",
        slug="hero",
        display_name="Hero",
        stress={
            "body": StressTrack(track_key="body", capacity=4, filled=0),
            "composure": StressTrack(track_key="composure", capacity=4, filled=0),
            "bonds": StressTrack(track_key="bonds", capacity=4, filled=0),
            "weird": StressTrack(track_key="weird", capacity=4, filled=weird_filled),
        },
    )


def test_apply_intimacy_risk_adds_one_weird_stress() -> None:
    actor = _pc(weird_filled=1)
    updated_weird, _ = apply_intimacy_risk(actor, "comfort", "camp_1")
    assert updated_weird.filled == 2


def test_apply_intimacy_risk_returns_at_least_one_cost_tag() -> None:
    actor = _pc()
    _, cost_tags = apply_intimacy_risk(actor, "comfort", "camp_1")
    assert len(cost_tags) >= 1


def test_comfort_benefit_includes_vulnerability_solace_tag() -> None:
    actor = _pc()
    _, cost_tags = apply_intimacy_risk(actor, "comfort", "camp_1")
    assert "vulnerability:solace" in cost_tags
