import pytest
from pydantic import ValidationError

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest


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
