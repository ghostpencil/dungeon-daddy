import pytest
from pydantic import ValidationError

from dungeon_daddy.campaign.manifest import (
    ActorManifest,
    CampaignManifest,
    ClockManifest,
    FactionManifest,
    ItemFeatureManifest,
    ItemManifest,
    ObjectiveCompletionManifest,
    ObjectiveManifest,
    ObjectTransitionManifest,
    RoomExitSeed,
    RoomObjectManifest,
)


def test_actor_manifest_parses_required_fields():
    data = {
        "slug": "valeria",
        "display_name": "Valeria Crane",
        "actor_type": "pc",
    }
    actor = ActorManifest(**data)
    assert actor.slug == "valeria"
    assert actor.display_name == "Valeria Crane"
    assert actor.actor_type == "pc"


def test_actor_manifest_rejects_invalid_actor_type():
    with pytest.raises(ValidationError):
        ActorManifest(slug="x", display_name="X", actor_type="dragon")


def test_clock_manifest_parses_required_fields():
    data = {
        "slug": "doom-clock",
        "label": "Doom Clock",
        "segments": 6,
    }
    clock = ClockManifest(**data)
    assert clock.slug == "doom-clock"
    assert clock.label == "Doom Clock"
    assert clock.segments == 6
    assert clock.filled == 0


def test_clock_manifest_rejects_filled_exceeding_segments():
    with pytest.raises(ValidationError):
        ClockManifest(slug="x", label="X", segments=4, filled=5)


def test_campaign_manifest_parses_with_nested_actors_and_clocks():
    data = {
        "slug": "bone-cathedral",
        "title": "The Bone Cathedral",
        "dungeon_slug": "bone-cathedral",
        "player_side": ["valeria"],
        "world_actors": [
            {"slug": "valeria", "display_name": "Valeria Crane", "actor_type": "pc"},
            {"slug": "the-warden", "display_name": "The Warden", "actor_type": "dungeon"},
        ],
        "clocks": [
            {"slug": "doom-clock", "label": "Doom Clock", "segments": 6},
        ],
    }
    campaign = CampaignManifest(**data)
    assert campaign.slug == "bone-cathedral"
    assert len(campaign.world_actors) == 2
    assert campaign.world_actors[0].slug == "valeria"
    assert len(campaign.clocks) == 1
    assert campaign.clocks[0].segments == 6


def test_faction_manifest_parses_with_defaults():
    faction = FactionManifest(slug="ossuary-cult", display_name="The Ossuary Cult")
    assert faction.slug == "ossuary-cult"
    assert faction.display_name == "The Ossuary Cult"
    assert faction.reputation == "neutral"
    assert faction.tier == 0
    assert faction.concept is None
    assert faction.goal is None
    assert faction.status == "active"
    assert faction.tags == []


def test_faction_manifest_rejects_unknown_reputation():
    with pytest.raises(ValidationError):
        FactionManifest(slug="x", display_name="X", reputation="friendly")


def test_faction_manifest_rejects_tier_out_of_range():
    with pytest.raises(ValidationError):
        FactionManifest(slug="x", display_name="X", tier=5)
    with pytest.raises(ValidationError):
        FactionManifest(slug="x", display_name="X", tier=-1)


def test_campaign_manifest_accepts_faction_manifest_list():
    campaign = CampaignManifest(
        slug="test",
        title="Test",
        dungeon_slug="test",
        factions=[
            FactionManifest(
                slug="ossuary-cult",
                display_name="The Ossuary Cult",
                reputation="cold",
                tier=1,
            )
        ],
    )
    assert len(campaign.factions) == 1
    assert isinstance(campaign.factions[0], FactionManifest)
    assert campaign.factions[0].reputation == "cold"


def test_bone_cathedral_json_parses_with_faction_manifest(tmp_path):
    import json
    from pathlib import Path

    json_path = Path("examples/campaign_manifests/bone-cathedral.json")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    campaign = CampaignManifest.model_validate(data)
    assert len(campaign.factions) == 1
    faction = campaign.factions[0]
    assert isinstance(faction, FactionManifest)
    assert faction.slug == "ossuary-cult"
    assert faction.reputation == "cold"
    assert faction.tier == 1


def test_campaign_manifest_round_trips_to_json():
    original = CampaignManifest(
        slug="bone-cathedral",
        title="The Bone Cathedral",
        dungeon_slug="bone-cathedral",
        player_side=["valeria"],
        world_actors=[
            ActorManifest(slug="valeria", display_name="Valeria Crane", actor_type="pc"),
        ],
        clocks=[
            ClockManifest(slug="doom-clock", label="Doom Clock", segments=6),
        ],
    )
    json_str = original.model_dump_json()
    restored = CampaignManifest.model_validate_json(json_str)
    assert restored.slug == original.slug
    assert restored.world_actors[0].slug == "valeria"
    assert restored.clocks[0].slug == "doom-clock"


def test_campaign_manifest_dungeon_voice_fields_default():
    campaign = CampaignManifest(slug="x", title="X", dungeon_slug="x")
    assert campaign.dungeon_voice is None
    assert campaign.dungeon_knowledge == []
    assert campaign.dungeon_corruption_clock is False


def test_campaign_manifest_dungeon_voice_fields_round_trip():
    original = CampaignManifest(
        slug="x",
        title="X",
        dungeon_slug="x",
        dungeon_voice="cold, industrial, analytical — speaks in diagnostics",
        dungeon_knowledge=["the warden was once human", "the lift hides a vault"],
        dungeon_corruption_clock=True,
    )
    restored = CampaignManifest.model_validate_json(original.model_dump_json())
    assert restored.dungeon_voice == "cold, industrial, analytical — speaks in diagnostics"
    assert restored.dungeon_knowledge == [
        "the warden was once human",
        "the lift hides a vault",
    ]
    assert restored.dungeon_corruption_clock is True


def test_campaign_manifest_dungeon_objectives_default_empty():
    campaign = CampaignManifest(slug="x", title="X", dungeon_slug="x")
    assert campaign.dungeon_objectives == []


def test_objective_manifest_round_trip_through_campaign():
    original = CampaignManifest(
        slug="x",
        title="X",
        dungeon_slug="x",
        dungeon_objectives=[
            ObjectiveManifest(
                slug="restore-coolant",
                title="Restore the Coolant Loop",
                description="The Crucible wants its coolant loop online again.",
                tier_index=0,
                completion=ObjectiveCompletionManifest(
                    kind="object_state",
                    target_slug="coolant-loop",
                    required_state="restored",
                ),
                reveals_knowledge=["The coolant loop hides a sealed conduit."],
            ),
        ],
    )
    restored = CampaignManifest.model_validate_json(original.model_dump_json())
    assert isinstance(restored.dungeon_objectives[0], ObjectiveManifest)
    obj = restored.dungeon_objectives[0]
    assert obj.slug == "restore-coolant"
    assert obj.tier_index == 0
    assert obj.completion.target_slug == "coolant-loop"
    assert obj.completion.required_state == "restored"
    assert obj.reveals_knowledge == ["The coolant loop hides a sealed conduit."]


def test_objective_manifest_object_state_requires_required_state():
    with pytest.raises(ValidationError):
        ObjectiveManifest(
            slug="restore-coolant",
            title="Restore the Coolant Loop",
            description="...",
            tier_index=0,
            completion=ObjectiveCompletionManifest(
                kind="object_state", target_slug="coolant-loop"
            ),
        )


def test_item_manifest_parses_minimal_fields():
    item = ItemManifest(
        slug="lockpick-kit",
        display_name="Lockpick Kit",
        item_type="class_kit",
        description="A well-used set of picks.",
        charges_max=3,
    )
    assert item.slug == "lockpick-kit"
    assert item.item_type == "class_kit"
    assert item.description == "A well-used set of picks."
    assert item.owner_slug is None
    assert item.features == []


def test_item_manifest_parses_with_feature():
    item = ItemManifest(
        slug="shadow-blade",
        display_name="Shadow Blade",
        item_type="equipped_gear",
        description="A blade that hides in shadow.",
        features=[
            ItemFeatureManifest(feature_type="rating_modifier", action_key="fight", modifier=1),
            ItemFeatureManifest(feature_type="new_action", action_key="vanish"),
        ],
    )
    assert len(item.features) == 2
    assert item.features[0].feature_type == "rating_modifier"
    assert item.features[0].modifier == 1
    assert item.features[1].feature_type == "new_action"
    assert item.features[1].modifier is None


def test_campaign_manifest_accepts_items_list():
    campaign = CampaignManifest(
        slug="bone-cathedral",
        title="The Bone Cathedral",
        dungeon_slug="bone-cathedral",
        items=[
            ItemManifest(
                slug="lockpick-kit",
                display_name="Lockpick Kit",
                item_type="class_kit",
                description="A well-used set of picks.",
                charges_max=3,
                owner_slug="valeria",
            )
        ],
    )
    assert len(campaign.items) == 1
    assert isinstance(campaign.items[0], ItemManifest)
    assert campaign.items[0].slug == "lockpick-kit"
    assert campaign.items[0].owner_slug == "valeria"


def test_item_manifest_room_id_defaults_to_none():
    item = ItemManifest(
        slug="gold-coin", display_name="Gold Coin",
        item_type="dungeon_item", description="A shiny coin.",
    )
    assert item.room_id is None


def test_item_manifest_accepts_room_id():
    item = ItemManifest(
        slug="gold-coin", display_name="Gold Coin",
        item_type="dungeon_item", description="A shiny coin.",
        room_id="room:cathedral:nave",
    )
    assert item.room_id == "room:cathedral:nave"


def test_room_object_manifest_parses_required_fields():
    obj = RoomObjectManifest(
        slug="iron-chest",
        display_name="Iron Chest",
        room_id="room:cathedral:nave",
        level_id="level:cathedral:ground",
        archetype="container",
        description="A heavy iron chest.",
        initial_state="sealed",
    )
    assert obj.slug == "iron-chest"
    assert obj.initial_state == "sealed"
    assert obj.transitions == []


def test_room_object_manifest_accepts_transitions():
    obj = RoomObjectManifest(
        slug="iron-chest",
        display_name="Iron Chest",
        room_id="room:cathedral:nave",
        level_id="level:cathedral:ground",
        archetype="container",
        description="A chest.",
        initial_state="sealed",
        transitions=[
            ObjectTransitionManifest(
                from_state="sealed", to_state="opened", trigger="open",
                spawns_item_slug="gold-coin",
            )
        ],
    )
    assert len(obj.transitions) == 1
    assert obj.transitions[0].spawns_item_slug == "gold-coin"
    assert obj.transitions[0].requires_item_slug is None


def test_room_object_manifest_accepts_resonance_point_archetype():
    # Phase 51: a resonance_point object marks the room where the dungeon channel
    # may open. The manifest archetype Literal must accept it (Deferred item 2).
    obj = RoomObjectManifest(
        slug="forge-heart",
        display_name="Forge Heart",
        room_id="r04",
        level_id="level:2",
        archetype="resonance_point",
        description="A node where the citadel's mind is close enough to hear.",
        initial_state="dormant",
    )
    assert obj.archetype == "resonance_point"


def test_campaign_manifest_room_objects_defaults_to_empty():
    campaign = CampaignManifest(slug="x", title="X", dungeon_slug="x")
    assert campaign.room_objects == []


def test_campaign_manifest_accepts_room_objects():
    campaign = CampaignManifest(
        slug="bone-cathedral",
        title="The Bone Cathedral",
        dungeon_slug="bone-cathedral",
        room_objects=[
            RoomObjectManifest(
                slug="iron-chest",
                display_name="Iron Chest",
                room_id="room:cathedral:nave",
                level_id="level:cathedral:ground",
                archetype="container",
                description="A chest.",
                initial_state="sealed",
            )
        ],
    )
    assert len(campaign.room_objects) == 1
    assert isinstance(campaign.room_objects[0], RoomObjectManifest)
    assert campaign.room_objects[0].slug == "iron-chest"


def test_room_exit_seed_parses_required_fields():
    seed = RoomExitSeed(
        from_room_id="room:entrance",
        to_room_id="room:corridor",
        label="North Door",
    )
    assert seed.from_room_id == "room:entrance"
    assert seed.to_room_id == "room:corridor"
    assert seed.label == "North Door"
    assert seed.exit_type == "door"
    assert seed.connector_type is None
    assert seed.status == "open"
    assert seed.requires_item_slug is None


def test_campaign_manifest_room_exits_defaults_to_empty():
    campaign = CampaignManifest(slug="x", title="X", dungeon_slug="x")
    assert campaign.room_exits == []


def test_campaign_manifest_accepts_room_exits():
    campaign = CampaignManifest(
        slug="bone-cathedral",
        title="The Bone Cathedral",
        dungeon_slug="bone-cathedral",
        room_exits=[
            RoomExitSeed(
                from_room_id="room:entrance",
                to_room_id="room:corridor",
                label="North Door",
                status="locked",
                requires_item_slug="iron-key",
            )
        ],
    )
    assert len(campaign.room_exits) == 1
    assert isinstance(campaign.room_exits[0], RoomExitSeed)
    assert campaign.room_exits[0].label == "North Door"
    assert campaign.room_exits[0].requires_item_slug == "iron-key"
