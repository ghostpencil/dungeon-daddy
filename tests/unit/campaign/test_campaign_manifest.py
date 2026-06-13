import pytest
from pydantic import ValidationError

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest, FactionManifest


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
