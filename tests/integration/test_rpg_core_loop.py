"""
Full headless RPG loop: PC studies a strange altar.
- study rating 2, risk moderate, effect standard
- fixed dice [5, 2] → partial
- ticks "Open the Choir Door" clock by 2
- marks 1 Weird stress
- emits action.resolved, clock.advanced, stress.marked
"""

from dungeon_daddy.rpg.clocks import create_clock
from dungeon_daddy.rpg.models import ActionRequest
from dungeon_daddy.rpg.service import RpgService


def test_altar_headless_scenario() -> None:
    svc = RpgService()

    # Create PC with default stress tracks
    actor = svc.create_actor(
        campaign_id="c1",
        actor_type="pc",
        slug="elara",
        display_name="Elara",
    )

    # Create investigation clock
    clock = create_clock(campaign_id="c1", label="Open the Choir Door", segments=6)

    # Resolve action: study rating 2, fixed dice [5, 2]
    req = ActionRequest(
        campaign_id="c1",
        actor_id=actor.actor_id,
        action_key="study",
        dice_pool=2,
    )
    resolution, action_event = svc.resolve_action(req, fixed=[5, 2])

    assert resolution.outcome == "partial"
    assert action_event.event_type == "action.resolved"

    # Advance clock by 2 ticks
    clock, clock_event = svc.advance_clock(clock, ticks=2)

    assert clock.filled == 2
    assert clock.status == "active"
    assert clock_event.event_type == "clock.advanced"

    # Mark 1 Weird stress
    weird_track = actor.stress["weird"]
    weird_track, stress_event = svc.apply_stress(
        actor_id=actor.actor_id,
        campaign_id="c1",
        track=weird_track,
        amount=1,
    )

    assert weird_track.filled == 1
    assert stress_event.event_type == "stress.marked"
    assert stress_event.payload["needs_fallout"] is False

    # All three domain events have the same campaign_id
    for event in (action_event, clock_event, stress_event):
        assert event.campaign_id == "c1"


def test_stress_needs_fallout_when_track_fills() -> None:
    svc = RpgService()
    actor = svc.create_actor(
        campaign_id="c1",
        actor_type="pc",
        slug="brogan",
        display_name="Brogan",
    )
    body_track = actor.stress["body"]
    # Fill the track completely
    updated, event = svc.apply_stress(
        actor_id=actor.actor_id,
        campaign_id="c1",
        track=body_track,
        amount=4,
    )
    assert updated.filled == 4
    assert event.payload["needs_fallout"] is True


def test_clock_completes_and_emits_event() -> None:
    svc = RpgService()
    clock = create_clock(campaign_id="c1", label="Boss Phase", segments=4)
    clock, event = svc.advance_clock(clock, ticks=4)
    assert clock.status == "completed"
    assert event.event_type == "clock.advanced"


def test_momentum_spend_resolves_higher_pool() -> None:
    svc = RpgService()
    req = ActionRequest(
        campaign_id="c1",
        actor_id="a1",
        action_key="fight",
        dice_pool=1,
        momentum_spend=2,
    )
    resolution, event = svc.resolve_action(req, fixed=[6, 3, 4])
    assert len(resolution.dice_rolled) == 3
    assert resolution.outcome == "full"
