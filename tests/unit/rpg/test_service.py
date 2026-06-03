from dungeon_daddy.rpg.service import RpgService
from dungeon_daddy.rpg.models import ActorState, ActionRequest, ActionResolution, ClockState, StressTrack
from dungeon_daddy.memory.models import DomainEvent


def test_resolve_action_emits_domain_event() -> None:
    svc = RpgService()
    req = ActionRequest(campaign_id="c1", actor_id="a1", action_key="study", dice_pool=2)
    resolution, event = svc.resolve_action(req, fixed=[5, 2])
    assert isinstance(resolution, ActionResolution)
    assert resolution.outcome == "partial"
    assert isinstance(event, DomainEvent)
    assert event.event_type == "action.resolved"
    assert event.campaign_id == "c1"


def test_advance_clock_emits_domain_event() -> None:
    svc = RpgService()
    clock = ClockState(clock_id="ck1", campaign_id="c1", label="Threat", segments=4, filled=0)
    updated, event = svc.advance_clock(clock, ticks=2)
    assert updated.filled == 2
    assert event.event_type == "clock.advanced"
    assert event.campaign_id == "c1"


def test_apply_stress_emits_domain_event() -> None:
    svc = RpgService()
    track = StressTrack(track_key="weird", capacity=4, filled=0)
    updated, event = svc.apply_stress(actor_id="a1", campaign_id="c1", track=track, amount=1)
    assert updated.filled == 1
    assert event.event_type == "stress.marked"
    assert event.campaign_id == "c1"


def test_create_actor_returns_actor_state_with_default_stress() -> None:
    svc = RpgService()
    actor = svc.create_actor(
        campaign_id="c1",
        actor_type="pc",
        slug="elara",
        display_name="Elara",
    )
    assert isinstance(actor, ActorState)
    assert actor.status == "active"
    assert set(actor.stress.keys()) == {"body", "composure", "bonds", "weird"}
