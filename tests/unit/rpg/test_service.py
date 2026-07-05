from dungeon_daddy.rpg.service import RpgService, compute_effective_ratings, mark_level_items_inert, refresh_kits
from dungeon_daddy.rpg.models import ActorState, ActionRequest, ActionResolution, ClockState, Item, ItemFeature, StressTrack, WorldReaction
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


def test_react_to_resolution_returns_world_reaction_and_event() -> None:
    # Phase 51.6: a non-object action falls to the ambient rule — one +1 tick on
    # the nearest local adverse clock, and no stress (stress is scripted-only).
    svc = RpgService()
    req = ActionRequest(campaign_id="c1", actor_id="a1", action_key="fight", dice_pool=1)
    resolution, _ = svc.resolve_action(req, fixed=[2])
    assert resolution.outcome == "miss"
    clock = ClockState(
        clock_id="ck1", campaign_id="c1", label="Heat", segments=6, filled=1,
        clock_level="room", scope_room_id="room_a", category="danger",
    )
    actor = ActorState(
        actor_id="a1", campaign_id="c1", actor_type="pc",
        slug="hero", display_name="Hero",
    )
    tracks = {
        "body": StressTrack(track_key="body", capacity=4, filled=0),
    }
    reaction, event = svc.react_to_resolution(
        resolution, [clock], [(actor, tracks)], current_room_id="room_a"
    )
    assert isinstance(reaction, WorldReaction)
    assert reaction.outcome == "miss"
    assert len(reaction.clock_lines) == 1
    assert reaction.clock_lines[0].ticks == 1
    assert reaction.stress_lines == []
    assert isinstance(event, DomainEvent)
    assert event.event_type == "world.reacted"


def test_react_to_resolution_respects_current_room_id() -> None:
    svc = RpgService()
    req = ActionRequest(campaign_id="c1", actor_id="a1", action_key="fight", dice_pool=1)
    resolution, _ = svc.resolve_action(req, fixed=[2])
    assert resolution.outcome == "miss"
    clock = ClockState(
        clock_id="ck_scoped", campaign_id="c1", label="Scoped",
        segments=4, filled=0, clock_level="room", scope_room_id="room_a", category="danger",
    )
    actor = ActorState(actor_id="a1", campaign_id="c1", actor_type="pc", slug="h", display_name="H")
    tracks = {"body": StressTrack(track_key="body", capacity=4, filled=0)}
    reaction_wrong_room, _ = svc.react_to_resolution(
        resolution, [clock], [(actor, tracks)], current_room_id="room_b"
    )
    assert len(reaction_wrong_room.clock_lines) == 0
    reaction_right_room, _ = svc.react_to_resolution(
        resolution, [clock], [(actor, tracks)], current_room_id="room_a"
    )
    assert len(reaction_right_room.clock_lines) == 1


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


def test_refresh_kits_restores_all_active_kits(repo) -> None:
    kit1 = Item(
        item_id="item:c1:kit1",
        campaign_id="c1",
        slug="lockpick-kit",
        display_name="Lockpick Kit",
        item_type="class_kit",
        description="Picks.",
        charges_max=3,
        charges_current=1,
        owner_actor_id="actor:c1:hero",
    )
    kit2 = Item(
        item_id="item:c1:kit2",
        campaign_id="c1",
        slug="healing-kit",
        display_name="Healing Kit",
        item_type="class_kit",
        description="Heals.",
        charges_max=2,
        charges_current=0,
        owner_actor_id="actor:c1:hero",
    )
    repo.save_item(kit1)
    repo.save_item(kit2)

    refreshed = refresh_kits(repo, "actor:c1:hero")

    assert set(refreshed) == {"item:c1:kit1", "item:c1:kit2"}
    items = {i["item_id"]: i for i in repo.get_items_by_actor("actor:c1:hero")}
    assert items["item:c1:kit1"]["charges_current"] == 3
    assert items["item:c1:kit2"]["charges_current"] == 2


def test_refresh_kits_skips_inactive_kits(repo) -> None:
    kit = Item(
        item_id="item:c1:kit1",
        campaign_id="c1",
        slug="lockpick-kit",
        display_name="Lockpick Kit",
        item_type="class_kit",
        description="Picks.",
        charges_max=3,
        charges_current=1,
        owner_actor_id="actor:c1:hero",
    )
    repo.save_item(kit)
    repo.update_item_status("item:c1:kit1", "consumed")

    refreshed = refresh_kits(repo, "actor:c1:hero")

    assert refreshed == []
    items = repo.get_items_by_actor("actor:c1:hero")
    assert items[0]["charges_current"] == 1


CAMPAIGN = "campaign:c1"
ACTOR = "actor:c1:hero"


def _gear_with_modifier(item_id: str, action_key: str, modifier: int) -> Item:
    feature = ItemFeature(
        feature_id=f"feat:{item_id}",
        item_id=item_id,
        feature_type="rating_modifier",
        action_key=action_key,
        modifier=modifier,
    )
    return Item(
        item_id=item_id,
        campaign_id=CAMPAIGN,
        slug=item_id.split(":")[-1],
        display_name="Gear",
        item_type="equipped_gear",
        description="A piece of gear.",
        owner_actor_id=ACTOR,
        is_equipped=True,
        features=[feature],
    )


def test_compute_effective_ratings_no_gear_returns_base(repo) -> None:
    base = {"fight": 2, "sneak": 1}
    result = compute_effective_ratings(ACTOR, base, repo)
    assert result == {"fight": 2, "sneak": 1}


def test_compute_effective_ratings_adds_equipped_modifier(repo) -> None:
    repo.save_item(_gear_with_modifier("item:c1:sword", "fight", 1))
    base = {"fight": 2, "sneak": 1}
    result = compute_effective_ratings(ACTOR, base, repo)
    assert result["fight"] == 3
    assert result["sneak"] == 1


def test_compute_effective_ratings_sums_multiple_modifiers(repo) -> None:
    repo.save_item(_gear_with_modifier("item:c1:sword", "fight", 1))
    repo.save_item(_gear_with_modifier("item:c1:gloves", "fight", 1))
    base = {"fight": 1}
    result = compute_effective_ratings(ACTOR, base, repo)
    assert result["fight"] == 3


def _level_bound_item(item_id: str, level_id: str, status: str = "active") -> Item:
    item = Item(
        item_id=item_id,
        campaign_id=CAMPAIGN,
        slug=item_id.split(":")[-1],
        display_name="Key",
        item_type="dungeon_item",
        description="A level-bound item.",
        owner_actor_id=ACTOR,
        level_id=level_id,
        status=status,
    )
    return item


def test_mark_level_items_inert_marks_active_matching_items(repo) -> None:
    repo.save_item(_level_bound_item("item:c1:key1", "level:c1:floor1"))
    repo.save_item(_level_bound_item("item:c1:key2", "level:c1:floor1"))

    result = mark_level_items_inert(repo, CAMPAIGN, "level:c1:floor1")

    assert set(result) == {"item:c1:key1", "item:c1:key2"}
    items = {i["item_id"]: i for i in repo.get_items(CAMPAIGN)}
    assert items["item:c1:key1"]["status"] == "inert"
    assert items["item:c1:key2"]["status"] == "inert"


def test_mark_level_items_inert_skips_other_level_and_inactive(repo) -> None:
    repo.save_item(_level_bound_item("item:c1:key-other", "level:c1:floor2"))
    repo.save_item(_level_bound_item("item:c1:key-consumed", "level:c1:floor1", status="consumed"))

    result = mark_level_items_inert(repo, CAMPAIGN, "level:c1:floor1")

    assert result == []
    items = {i["item_id"]: i for i in repo.get_items(CAMPAIGN)}
    assert items["item:c1:key-other"]["status"] == "active"
    assert items["item:c1:key-consumed"]["status"] == "consumed"
