import json
import pytest
from pathlib import Path
from pydantic import ValidationError

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.seed_pack import (
    ApplyResult,
    SeedActor,
    SeedPack,
    apply_seed_pack,
    derive_actor_id,
    derive_clock_id,
    load_seed_pack,
)

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


_MINIMAL_PACK = {
    "campaign_slug": "test-campaign",
    "player_side": {
        "label": "The Party",
        "actors": [],
    },
    "dungeon_side": {
        "actors": [],
    },
    "clocks": [],
    "memories": [],
    "room_threats": [],
}


class TestSeedPackParse:
    def test_parses_from_minimal_dict(self) -> None:
        pack = SeedPack.model_validate(_MINIMAL_PACK)
        assert pack.campaign_slug == "test-campaign"
        assert pack.player_side.label == "The Party"
        assert pack.player_side.actors == []
        assert pack.dungeon_side.actors == []

    def test_load_seed_pack_reads_json_file(self, tmp_path: Path) -> None:
        f = tmp_path / "rpg_seed.json"
        f.write_text(json.dumps(_MINIMAL_PACK), encoding="utf-8")
        pack = load_seed_pack(f)
        assert pack.campaign_slug == "test-campaign"

    def test_player_actor_fields(self) -> None:
        data = {
            **_MINIMAL_PACK,
            "player_side": {
                "label": "The Party",
                "actors": [
                    {
                        "slug": "mara",
                        "display_name": "Mara",
                        "actor_type": "pc",
                        "concept": "Former soldier turned relic hunter",
                        "actions": {"fight": 2, "move": 1, "sense": 1},
                        "stress_tracks": ["body", "composure"],
                        "tags": ["veteran", "scarred"],
                    }
                ],
            },
        }
        pack = SeedPack.model_validate(data)
        actor = pack.player_side.actors[0]
        assert actor.slug == "mara"
        assert actor.actor_type == "pc"
        assert actor.actions["fight"] == 2
        assert "veteran" in actor.tags

    def test_dungeon_actor_fields(self) -> None:
        data = {
            **_MINIMAL_PACK,
            "dungeon_side": {
                "actors": [
                    {
                        "slug": "bone-warden",
                        "display_name": "The Bone Warden",
                        "actor_type": "monster",
                        "concept": "Ancient guardian of the ossuary",
                        "instinct": "Pursue those who disturb the dead",
                        "threat_tags": ["undead", "pursuit", "overwhelming"],
                    }
                ]
            },
        }
        pack = SeedPack.model_validate(data)
        actor = pack.dungeon_side.actors[0]
        assert actor.slug == "bone-warden"
        assert actor.instinct == "Pursue those who disturb the dead"
        assert "pursuit" in actor.threat_tags

    def test_clocks_parsed(self) -> None:
        data = {
            **_MINIMAL_PACK,
            "clocks": [
                {
                    "slug": "bone-warden-stirs",
                    "label": "The Bone Warden Stirs",
                    "segments": 6,
                    "category": "danger",
                    "notes": "Advances on noise or forced entry",
                }
            ],
        }
        pack = SeedPack.model_validate(data)
        clock = pack.clocks[0]
        assert clock.slug == "bone-warden-stirs"
        assert clock.segments == 6
        assert clock.category == "danger"

    def test_room_threat_parsed(self) -> None:
        data = {
            **_MINIMAL_PACK,
            "room_threats": [
                {
                    "location_slug": "ossuary-gate",
                    "trigger_tags": ["noise", "forced_entry"],
                    "related_actor_slugs": ["bone-warden"],
                    "related_clock_slugs": ["bone-warden-stirs"],
                    "possible_reactions": ["advance_clock", "reveal_threat"],
                    "notes": "The gate is sealed with bone-resin.",
                }
            ],
        }
        pack = SeedPack.model_validate(data)
        threat = pack.room_threats[0]
        assert threat.location_slug == "ossuary-gate"
        assert "noise" in threat.trigger_tags
        assert "bone-warden" in threat.related_actor_slugs
        assert "advance_clock" in threat.possible_reactions

    def test_memories_parsed(self) -> None:
        data = {
            **_MINIMAL_PACK,
            "memories": [
                {
                    "title": "The Expedition's Purpose",
                    "summary": "The party entered the dungeon seeking the Shattered Seal.",
                    "type": "campaign_premise",
                    "importance": 8,
                    "tags": ["thread:main-quest", "theme:ruin"],
                }
            ],
        }
        pack = SeedPack.model_validate(data)
        mem = pack.memories[0]
        assert mem.title == "The Expedition's Purpose"
        assert mem.type == "campaign_premise"
        assert mem.importance == 8
        assert "thread:main-quest" in mem.tags

    def test_invalid_actor_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            SeedActor(slug="x", display_name="X", actor_type="dragon")


class TestStableIdDerivation:
    def test_derive_actor_id_is_deterministic(self) -> None:
        id1 = derive_actor_id("my-campaign", "mara")
        id2 = derive_actor_id("my-campaign", "mara")
        assert id1 == id2

    def test_derive_actor_id_differs_for_different_slugs(self) -> None:
        assert derive_actor_id("my-campaign", "mara") != derive_actor_id("my-campaign", "gorrak")

    def test_derive_actor_id_differs_across_campaigns(self) -> None:
        assert derive_actor_id("campaign-a", "mara") != derive_actor_id("campaign-b", "mara")

    def test_derive_clock_id_is_deterministic(self) -> None:
        id1 = derive_clock_id("my-campaign", "bone-warden-stirs")
        id2 = derive_clock_id("my-campaign", "bone-warden-stirs")
        assert id1 == id2

    def test_actor_and_clock_namespaces_are_isolated(self) -> None:
        assert derive_actor_id("my-campaign", "same-slug") != derive_clock_id("my-campaign", "same-slug")


_RICH_PACK = {
    "campaign_slug": "test-campaign",
    "player_side": {
        "label": "The Party",
        "actors": [
            {
                "slug": "mara",
                "display_name": "Mara",
                "actor_type": "pc",
                "concept": "Former soldier",
                "actions": {"fight": 2, "move": 1},
                "stress_tracks": ["body", "composure"],
            }
        ],
    },
    "dungeon_side": {
        "actors": [
            {
                "slug": "bone-warden",
                "display_name": "The Bone Warden",
                "actor_type": "monster",
                "instinct": "Pursue the living",
            }
        ]
    },
    "clocks": [
        {
            "slug": "bone-warden-stirs",
            "label": "The Bone Warden Stirs",
            "segments": 6,
            "category": "danger",
        }
    ],
    "memories": [
        {
            "title": "The Expedition's Purpose",
            "summary": "The party seeks the Shattered Seal.",
            "type": "campaign_premise",
            "importance": 8,
            "tags": ["thread:main-quest", "theme:ruin"],
        }
    ],
    "room_threats": [],
}


class TestApplySeedPack:
    @pytest.fixture
    def repo(self, tmp_path: Path) -> MemoryRepository:
        return MemoryRepository(tmp_path / "campaign.duckdb")

    def test_apply_returns_result(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(_RICH_PACK)
        result = apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        assert isinstance(result, ApplyResult)
        assert result.actors_applied == 2
        assert result.clocks_applied == 1
        assert result.memories_applied == 1

    def test_apply_inserts_player_actor(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(_RICH_PACK)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        actor_id = derive_actor_id("test-campaign", "mara")
        actor = repo.get_actor(actor_id)
        assert actor is not None
        assert actor["display_name"] == "Mara"
        assert actor["actor_type"] == "pc"
        assert actor["slug"] == "mara"

    def test_apply_inserts_dungeon_actor(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(_RICH_PACK)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        actor_id = derive_actor_id("test-campaign", "bone-warden")
        actor = repo.get_actor(actor_id)
        assert actor is not None
        assert actor["actor_type"] == "monster"

    def test_apply_saves_action_ratings(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(_RICH_PACK)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        actor_id = derive_actor_id("test-campaign", "mara")
        ratings = {r["action_key"]: r["rating"] for r in repo.get_actor_action_ratings(actor_id)}
        assert ratings["fight"] == 2
        assert ratings["move"] == 1

    def test_apply_saves_stress_tracks(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(_RICH_PACK)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        actor_id = derive_actor_id("test-campaign", "mara")
        tracks = {t["track_key"] for t in repo.get_actor_stress_tracks(actor_id)}
        assert "body" in tracks
        assert "composure" in tracks

    def test_apply_inserts_clock(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(_RICH_PACK)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        clock_id = derive_clock_id("test-campaign", "bone-warden-stirs")
        clocks = {c["clock_id"]: c for c in repo.get_clocks("campaign-123")}
        assert clock_id in clocks
        assert clocks[clock_id]["label"] == "The Bone Warden Stirs"
        assert clocks[clock_id]["segments"] == 6

    def test_apply_inserts_memory_with_tags(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(_RICH_PACK)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        entries = repo.get_memory_entries_by_campaign("campaign-123")
        assert len(entries) == 1
        mem = entries[0]
        assert mem["title"] == "The Expedition's Purpose"
        assert mem["importance"] == 8
        tags = set(repo.get_memory_tags(mem["memory_id"]))
        assert "thread:main-quest" in tags
        assert "theme:ruin" in tags

    def test_apply_is_idempotent(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(_RICH_PACK)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        assert len(repo.get_actors_by_campaign("campaign-123")) == 2
        assert len(repo.get_clocks("campaign-123")) == 1
        assert len(repo.get_memory_entries_by_campaign("campaign-123")) == 1
