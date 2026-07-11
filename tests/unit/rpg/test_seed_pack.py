import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import (
    CLOCK_CATEGORIES,
    is_known_clock_category,
    normalize_clock_category,
)
from dungeon_daddy.rpg.seed_pack import (
    ApplyResult,
    SeedActor,
    SeedClock,
    SeedFaction,
    SeedPack,
    apply_seed_pack,
    derive_actor_id,
    derive_clock_id,
    derive_faction_id,
    load_seed_pack,
    validate_seed_room_ids,
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
        assert "trait:pursuit" in actor.tags  # threat_tags folded to trait: (T5)

    def test_seed_actor_folds_threat_tags_into_trait_tags(self) -> None:
        # T5: threat_tags (boss/construct/undead) are descriptive actor traits;
        # they fold into the actor's tags as trait:<slug>, and the field is gone.
        actor = SeedActor.model_validate({
            "slug": "bone-warden",
            "display_name": "The Bone Warden",
            "actor_type": "monster",
            "tags": ["level:level-1"],
            "threat_tags": ["undead", "boss"],
        })
        assert "trait:undead" in actor.tags
        assert "trait:boss" in actor.tags
        assert "level:level-1" in actor.tags  # existing tags preserved
        assert not hasattr(actor, "threat_tags")

    def test_seed_actor_folds_threat_tags_without_duplicating(self) -> None:
        actor = SeedActor.model_validate({
            "slug": "x", "display_name": "X", "actor_type": "monster",
            "tags": ["trait:undead"],
            "threat_tags": ["undead"],
        })
        assert actor.tags.count("trait:undead") == 1

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


class TestSeedClockModel:
    def test_clock_level_defaults_to_dungeon(self) -> None:
        c = SeedClock(slug="trap", label="Trap", segments=4, category="danger")
        assert c.clock_level == "dungeon"

    def test_clock_level_accepted(self) -> None:
        c = SeedClock(slug="trap", label="Trap", segments=4, category="danger", clock_level="room")
        assert c.clock_level == "room"

    def test_optional_fields_default_to_none(self) -> None:
        c = SeedClock(slug="trap", label="Trap", segments=4, category="danger")
        assert c.scope_room_id is None
        assert c.action_tags == []
        assert c.level_id is None
        assert c.owner_actor_slug is None
        assert c.stakes is None
        assert c.completion_effect is None
        assert c.visible_to_player is True

    def test_parses_all_clock_level_fields(self) -> None:
        c = SeedClock(
            slug="mara-arc", label="Mara Arc", segments=6, category="relationship",
            clock_level="character", owner_actor_slug="mara",
            stakes="Mara begins to trust.", completion_effect="Mara gains a tag.",
            visible_to_player=False,
        )
        assert c.owner_actor_slug == "mara"
        assert c.stakes == "Mara begins to trust."
        assert c.completion_effect == "Mara gains a tag."
        assert c.visible_to_player is False

    def test_parses_scope_fields(self) -> None:
        c = SeedClock(
            slug="trap", label="Trap", segments=4, category="danger",
            scope_room_id="room_boiler", action_tags=["fight", "move"],
        )
        assert c.scope_room_id == "room_boiler"
        assert c.action_tags == ["fight", "move"]


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

    def test_apply_sets_clock_scope_from_room_threat(self, repo: MemoryRepository) -> None:
        data = {
            **_MINIMAL_PACK,
            "clocks": [
                {"slug": "trap-primed", "label": "Trap Primed", "segments": 4, "category": "danger"}
            ],
            "room_threats": [
                {
                    "location_slug": "room_boiler",
                    "trigger_tags": ["fight", "move"],
                    "related_clock_slugs": ["trap-primed"],
                }
            ],
        }
        pack = SeedPack.model_validate(data)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        clock_id = derive_clock_id("test-campaign", "trap-primed")
        clocks = {c["clock_id"]: c for c in repo.get_clocks("campaign-123")}
        assert clock_id in clocks
        assert clocks[clock_id]["scope_room_id"] == "room_boiler"
        # T5: trigger_tags route to clock tags as trait:, not action_tags.
        assert clocks[clock_id]["action_tags"] == []
        assert set(clocks[clock_id]["tags"]) == {"trait:fight", "trait:move"}

    def test_apply_routes_trigger_tags_to_clock_trait_tags(self, repo: MemoryRepository) -> None:
        # T5: room-threat trigger_tags become descriptive trait: tags ON THE CLOCK,
        # not action_tags (where they could never match a verb, so the clock never
        # advanced).
        data = {
            **_MINIMAL_PACK,
            "clocks": [
                {"slug": "trap-primed", "label": "Trap Primed", "segments": 4, "category": "danger"}
            ],
            "room_threats": [
                {
                    "location_slug": "room_boiler",
                    "trigger_tags": ["noise", "touch_artifact"],
                    "related_clock_slugs": ["trap-primed"],
                }
            ],
        }
        pack = SeedPack.model_validate(data)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        clock_id = derive_clock_id("test-campaign", "trap-primed")
        clock = {c["clock_id"]: c for c in repo.get_clocks("campaign-123")}[clock_id]
        assert clock["scope_room_id"] == "room_boiler"
        assert set(clock["tags"]) == {"trait:noise", "trait:touch_artifact"}
        assert clock["action_tags"] == []

    def test_apply_dedups_duplicate_trigger_tags(self, repo: MemoryRepository) -> None:
        # F2: duplicate trigger_tags collapse to a single trait: tag on the clock
        # (the SeedActor threat_tags fold already dedups; both share one helper).
        data = {
            **_MINIMAL_PACK,
            "clocks": [
                {"slug": "trap-primed", "label": "Trap Primed", "segments": 4, "category": "danger"}
            ],
            "room_threats": [
                {
                    "location_slug": "room_boiler",
                    "trigger_tags": ["noise", "noise", "combat"],
                    "related_clock_slugs": ["trap-primed"],
                }
            ],
        }
        pack = SeedPack.model_validate(data)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        clock_id = derive_clock_id("test-campaign", "trap-primed")
        clock = {c["clock_id"]: c for c in repo.get_clocks("campaign-123")}[clock_id]
        assert clock["tags"] == ["trait:noise", "trait:combat"]  # deduped, order kept

    def test_apply_empty_trigger_tags_does_not_blank_clock_tags(
        self, repo: MemoryRepository
    ) -> None:
        # A threat with an empty trigger list must only re-scope the clock, never
        # blank tags an earlier threat (or the clock definition) set.
        data = {
            **_MINIMAL_PACK,
            "clocks": [
                {"slug": "trap-primed", "label": "Trap Primed", "segments": 4, "category": "danger"}
            ],
            "room_threats": [
                {"location_slug": "room_a", "trigger_tags": ["noise"],
                 "related_clock_slugs": ["trap-primed"]},
                {"location_slug": "room_b", "trigger_tags": [],
                 "related_clock_slugs": ["trap-primed"]},
            ],
        }
        pack = SeedPack.model_validate(data)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        clock_id = derive_clock_id("test-campaign", "trap-primed")
        clock = {c["clock_id"]: c for c in repo.get_clocks("campaign-123")}[clock_id]
        assert clock["scope_room_id"] == "room_b"      # last threat re-scopes
        assert clock["tags"] == ["trait:noise"]         # first threat's tag survives

    def test_apply_room_threat_preserves_clock_action_tags(
        self, repo: MemoryRepository
    ) -> None:
        # F5: routing trigger_tags onto a co-referenced clock must not blank the
        # clock's own action_tags (its verb gate) — only scope + trait tags update.
        data = {
            **_MINIMAL_PACK,
            "clocks": [
                {"slug": "trap-primed", "label": "Trap Primed", "segments": 4,
                 "category": "danger", "action_tags": ["fight", "move"]}
            ],
            "room_threats": [
                {
                    "location_slug": "room_boiler",
                    "trigger_tags": ["noise"],
                    "related_clock_slugs": ["trap-primed"],
                }
            ],
        }
        pack = SeedPack.model_validate(data)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        clock_id = derive_clock_id("test-campaign", "trap-primed")
        clock = {c["clock_id"]: c for c in repo.get_clocks("campaign-123")}[clock_id]
        assert clock["scope_room_id"] == "room_boiler"
        assert clock["tags"] == ["trait:noise"]
        assert set(clock["action_tags"]) == {"fight", "move"}  # F5: preserved

    def test_apply_persists_clock_level_metadata(self, repo: MemoryRepository) -> None:
        data = {
            **_MINIMAL_PACK,
            "clocks": [
                {
                    "slug": "quest-clock",
                    "label": "Restore the Elevator",
                    "segments": 6,
                    "category": "objective",
                    "clock_level": "quest",
                    "stakes": "Elevator needed to descend.",
                    "completion_effect": "Elevator operational.",
                }
            ],
        }
        pack = SeedPack.model_validate(data)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        clock_id = derive_clock_id("test-campaign", "quest-clock")
        clocks = {c["clock_id"]: c for c in repo.get_clocks("campaign-123")}
        assert clocks[clock_id]["clock_level"] == "quest"
        assert clocks[clock_id]["category"] == "objective"
        assert clocks[clock_id]["stakes"] == "Elevator needed to descend."
        assert clocks[clock_id]["completion_effect"] == "Elevator operational."

    def test_apply_validates_room_ids_when_provided(self, repo: MemoryRepository) -> None:
        data = {
            **_MINIMAL_PACK,
            "clocks": [
                {"slug": "trap", "label": "Trap", "segments": 4, "category": "danger",
                 "clock_level": "room", "scope_room_id": "r1"}
            ],
        }
        pack = SeedPack.model_validate(data)
        with pytest.raises(ValueError, match="r1"):
            apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR, valid_room_ids={"R1"})

    def test_apply_skips_room_id_validation_by_default(self, repo: MemoryRepository) -> None:
        data = {
            **_MINIMAL_PACK,
            "clocks": [
                {"slug": "trap", "label": "Trap", "segments": 4, "category": "danger",
                 "clock_level": "room", "scope_room_id": "r1"}
            ],
        }
        pack = SeedPack.model_validate(data)
        # No valid_room_ids → no validation (back-compat for callers without a dungeon).
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        assert len(repo.get_clocks("campaign-123")) == 1

    def test_apply_persists_actor_tags(self, repo: MemoryRepository) -> None:
        data = {
            **_MINIMAL_PACK,
            "player_side": {
                "label": "The Party",
                "actors": [
                    {
                        "slug": "mara",
                        "display_name": "Mara",
                        "actor_type": "pc",
                        "tags": ["trait:veteran", "level:level-1"],
                    }
                ],
            },
        }
        pack = SeedPack.model_validate(data)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        actor = repo.get_actor(derive_actor_id("test-campaign", "mara"))
        assert actor is not None
        assert set(actor["tags"]) >= {"trait:veteran", "level:level-1"}

    def test_apply_derives_owner_actor_id_from_slug(self, repo: MemoryRepository) -> None:
        data = {
            **_MINIMAL_PACK,
            "player_side": {
                "label": "The Party",
                "actors": [
                    {
                        "slug": "mara",
                        "display_name": "Mara",
                        "actor_type": "pc",
                    }
                ],
            },
            "clocks": [
                {
                    "slug": "mara-arc",
                    "label": "Mara Begins to Trust",
                    "segments": 6,
                    "category": "relationship",
                    "clock_level": "character",
                    "owner_actor_slug": "mara",
                }
            ],
        }
        pack = SeedPack.model_validate(data)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        clock_id = derive_clock_id("test-campaign", "mara-arc")
        clocks = {c["clock_id"]: c for c in repo.get_clocks("campaign-123")}
        expected_actor_id = derive_actor_id("test-campaign", "mara")
        assert clocks[clock_id]["owner_actor_id"] == expected_actor_id


_SEED_DATA_DIR = (
    Path(__file__).parent.parent.parent.parent / "seed_data" / "campaigns"
)

_ROOT = Path(__file__).parent.parent.parent.parent

# Canonical dungeon model per shipped campaign — the source of truth for the
# room ids a seed may scope to (§4.3). The Crucible model lives as a test
# fixture; the tomb ships as a sample.
_DUNGEON_MODELS = {
    "the-crucible": _ROOT / "tests" / "fixtures" / "crucible.json",
    "tomb-of-the-forgotten-king": (
        _ROOT / "dungeon_daddy" / "data" / "samples" / "tomb_of_the_forgotten_king.json"
    ),
}


def _room_ids_from_model(path: Path) -> set[str]:
    from dungeon_daddy.data.models import Dungeon

    dungeon = Dungeon.model_validate_json(path.read_text(encoding="utf-8"))
    return {room.id for level in dungeon.levels for room in level.rooms}


class TestApplySeedPackFactions:
    @pytest.fixture
    def repo(self, tmp_path: Path) -> MemoryRepository:
        return MemoryRepository(tmp_path / "campaign.duckdb")

    def _pack_with_factions(self) -> dict:
        return {
            **_MINIMAL_PACK,
            "factions": [
                {
                    "slug": "ossuary-cult",
                    "display_name": "The Ossuary Cult",
                    "reputation": "cold",
                    "tier": 1,
                    "goal": "Seal the relic.",
                }
            ],
        }

    def test_apply_inserts_faction_row(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(self._pack_with_factions())
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        factions = repo.get_factions("campaign-123")
        assert len(factions) == 1
        assert factions[0]["slug"] == "ossuary-cult"
        assert factions[0]["reputation"] == "cold"

    def test_apply_result_includes_factions_applied(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(self._pack_with_factions())
        result = apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        assert result.factions_applied == 1

    def test_apply_faction_id_is_stable(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(self._pack_with_factions())
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        expected_id = derive_faction_id("test-campaign", "ossuary-cult")
        factions = repo.get_factions("campaign-123")
        assert factions[0]["faction_id"] == expected_id

    def test_apply_factions_is_idempotent(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(self._pack_with_factions())
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        assert len(repo.get_factions("campaign-123")) == 1

    def test_apply_does_not_reset_runtime_reputation(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(self._pack_with_factions())
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)
        faction_id = derive_faction_id("test-campaign", "ossuary-cult")
        repo.update_faction_reputation(faction_id, delta_steps=2)  # cold → warm
        apply_seed_pack(pack, "campaign-123", repo, MIGRATIONS_DIR)  # re-seed
        factions = repo.get_factions("campaign-123")
        assert factions[0]["reputation"] == "warm"  # not reset to "cold"


class TestCampaignSeedFilesValidate:
    @pytest.mark.parametrize("campaign_dir", list(_SEED_DATA_DIR.iterdir()) if _SEED_DATA_DIR.exists() else [])
    def test_campaign_rpg_seed_parses_against_schema(self, campaign_dir: Path) -> None:
        seed_file = campaign_dir / "rpg_seed.json"
        if not seed_file.exists():
            pytest.skip(f"No rpg_seed.json in {campaign_dir.name}")
        pack = load_seed_pack(seed_file)
        assert pack.campaign_slug == campaign_dir.name
        for clock in pack.clocks:
            assert clock.clock_level in ("room", "level", "dungeon", "quest", "character", "faction")
            assert clock.stakes is not None, f"Clock {clock.slug!r} missing stakes"
            assert clock.completion_effect is not None, f"Clock {clock.slug!r} missing completion_effect"

    @pytest.mark.parametrize("campaign_dir", list(_SEED_DATA_DIR.iterdir()) if _SEED_DATA_DIR.exists() else [])
    def test_campaign_has_required_clock_levels(self, campaign_dir: Path) -> None:
        seed_file = campaign_dir / "rpg_seed.json"
        if not seed_file.exists():
            pytest.skip(f"No rpg_seed.json in {campaign_dir.name}")
        pack = load_seed_pack(seed_file)
        levels = {c.clock_level for c in pack.clocks}
        assert "room" in levels, f"{campaign_dir.name}: missing room clock"
        assert "dungeon" in levels, f"{campaign_dir.name}: missing dungeon clock"
        assert "quest" in levels, f"{campaign_dir.name}: missing quest clock"

    @pytest.mark.parametrize("campaign_dir", list(_SEED_DATA_DIR.iterdir()) if _SEED_DATA_DIR.exists() else [])
    def test_campaign_clock_categories_normalize_to_the_enum(self, campaign_dir: Path) -> None:
        # Phase 51.6 Slice 2: every shipped clock category must be recognized
        # (a canonical member or a known synonym) and normalize onto a valid
        # ClockCategory. An unmapped category here is the "not silent" signal —
        # this test fails so the author adds an enum member or a synonym rather
        # than letting it fall back invisibly.
        seed_file = campaign_dir / "rpg_seed.json"
        if not seed_file.exists():
            pytest.skip(f"No rpg_seed.json in {campaign_dir.name}")
        pack = load_seed_pack(seed_file)
        for clock in pack.clocks:
            assert is_known_clock_category(clock.category), (
                f"{campaign_dir.name}: clock {clock.slug!r} has unrecognized "
                f"category {clock.category!r} (add an enum member or a synonym)"
            )
            normalized = normalize_clock_category(clock.category)
            assert normalized is None or normalized in CLOCK_CATEGORIES

    @pytest.mark.parametrize("campaign_dir", list(_SEED_DATA_DIR.iterdir()) if _SEED_DATA_DIR.exists() else [])
    def test_campaign_room_clocks_have_scope_room_id(self, campaign_dir: Path) -> None:
        seed_file = campaign_dir / "rpg_seed.json"
        if not seed_file.exists():
            pytest.skip(f"No rpg_seed.json in {campaign_dir.name}")
        pack = load_seed_pack(seed_file)
        for clock in pack.clocks:
            if clock.clock_level == "room":
                assert clock.scope_room_id is not None, (
                    f"{campaign_dir.name}: room clock {clock.slug!r} missing scope_room_id"
                )

    @pytest.mark.parametrize("campaign_dir", list(_SEED_DATA_DIR.iterdir()) if _SEED_DATA_DIR.exists() else [])
    def test_campaign_seed_tags_are_canonical(self, campaign_dir: Path) -> None:
        # §4.2: every descriptive tag in a shipped seed is namespaced (T1-T3);
        # the legacy threat_tags key is gone; memory tags carry no actor:protagonist
        # (T6 folds them to actor:pc). Read paths stay permissive, but the shipped
        # seeds must be canonical.
        from dungeon_daddy.memory.tags import validate_tag

        seed_file = campaign_dir / "rpg_seed.json"
        if not seed_file.exists():
            pytest.skip(f"No rpg_seed.json in {campaign_dir.name}")
        pack = load_seed_pack(seed_file)
        for actor in pack.player_side.actors + pack.dungeon_side.actors:
            for tag in actor.tags:
                validate_tag(tag)  # raises on a bare / malformed tag
        for faction in pack.factions:
            for tag in faction.tags:
                validate_tag(tag)
        for memory in pack.memories:
            for tag in memory.tags:
                validate_tag(tag)
                assert not tag.startswith("actor:protagonist:"), (
                    f"{campaign_dir.name}: memory tag {tag!r} still uses the legacy "
                    "actor:protagonist namespace (T6 folds it to actor:pc)"
                )
        raw = json.loads(seed_file.read_text(encoding="utf-8"))
        for side in ("player_side", "dungeon_side"):
            for actor in raw.get(side, {}).get("actors", []):
                assert "threat_tags" not in actor, (
                    f"{campaign_dir.name}: actor {actor.get('slug')!r} still carries a "
                    "threat_tags key (T5: fold into trait: tags and drop it)"
                )

    @pytest.mark.parametrize("campaign_dir", list(_SEED_DATA_DIR.iterdir()) if _SEED_DATA_DIR.exists() else [])
    def test_campaign_seed_memory_location_tags_are_room_ids(
        self, campaign_dir: Path
    ) -> None:
        # BUG 1 / owner ruling 2026-07-10: a memory's location:<slug> tag uses
        # the room's grid id (like scope_room_id / threat location_slug), so
        # current-room retrieval (location_slug=current_room_id) matches. The
        # dungeon (campaign) slug is allowed for dungeon-wide lore.
        seed_file = campaign_dir / "rpg_seed.json"
        if not seed_file.exists():
            pytest.skip(f"No rpg_seed.json in {campaign_dir.name}")
        model = _DUNGEON_MODELS.get(campaign_dir.name)
        if model is None or not model.exists():
            pytest.skip(f"No canonical dungeon model for {campaign_dir.name}")
        valid = _room_ids_from_model(model) | {campaign_dir.name}
        raw = json.loads(seed_file.read_text(encoding="utf-8"))
        for memory in raw.get("memories", []):
            for tag in memory.get("tags", []):
                if tag.startswith("location:"):
                    slug = tag.split(":", 1)[1]
                    assert slug in valid, (
                        f"{campaign_dir.name}: memory location tag {tag!r} is not "
                        f"a room id in the dungeon model (nor the dungeon slug)"
                    )

    @pytest.mark.parametrize("campaign_dir", list(_SEED_DATA_DIR.iterdir()) if _SEED_DATA_DIR.exists() else [])
    def test_campaign_seed_actor_memory_tags_match_actor_type(
        self, campaign_dir: Path
    ) -> None:
        # Slice A5 (owner ruling 2026-07-10): a memory's actor:<subtype>:<slug>
        # tag must use the subtype canonical to that actor's record (monster/npc
        # -> npc; the dungeon persona -> dungeon), so present-actor retrieval
        # filters actually match. actor:dungeon: is reserved for the persona.
        from dungeon_daddy.memory.tags import actor_tag

        seed_file = campaign_dir / "rpg_seed.json"
        if not seed_file.exists():
            pytest.skip(f"No rpg_seed.json in {campaign_dir.name}")
        raw = json.loads(seed_file.read_text(encoding="utf-8"))
        type_by_slug = {
            a["slug"]: a["actor_type"]
            for side in ("player_side", "dungeon_side")
            for a in raw.get(side, {}).get("actors", [])
        }
        for memory in raw.get("memories", []):
            for tag in memory.get("tags", []):
                namespace, _, rest = tag.partition(":")
                if namespace != "actor":
                    continue
                _subtype, _, slug = rest.partition(":")
                if slug in type_by_slug:
                    expected = actor_tag(type_by_slug[slug], slug)
                    assert tag == expected, (
                        f"{campaign_dir.name}: memory tag {tag!r} should be "
                        f"{expected!r} for actor_type {type_by_slug[slug]!r}"
                    )

    @pytest.mark.parametrize("campaign_dir", list(_SEED_DATA_DIR.iterdir()) if _SEED_DATA_DIR.exists() else [])
    def test_campaign_seed_room_ids_match_dungeon_model(self, campaign_dir: Path) -> None:
        # §4.3 guard: every scope_room_id / room-threat location_slug in a shipped
        # seed must exactly match a Room.id in that campaign's canonical dungeon
        # model (union across all levels). Fails loudly on future r1-vs-R1 drift.
        seed_file = campaign_dir / "rpg_seed.json"
        if not seed_file.exists():
            pytest.skip(f"No rpg_seed.json in {campaign_dir.name}")
        model_path = _DUNGEON_MODELS.get(campaign_dir.name)
        if model_path is None or not model_path.exists():
            pytest.skip(f"No canonical dungeon model registered for {campaign_dir.name}")
        pack = load_seed_pack(seed_file)
        validate_seed_room_ids(pack, _room_ids_from_model(model_path))  # raises on drift


class TestValidateSeedRoomIds:
    def _pack(self, *, clock_scope: str | None = None, threat_loc: str | None = None) -> SeedPack:
        data: dict = {**_MINIMAL_PACK}
        if clock_scope is not None:
            data["clocks"] = [{
                "slug": "trap", "label": "Trap", "segments": 4, "category": "danger",
                "clock_level": "room", "scope_room_id": clock_scope,
            }]
        if threat_loc is not None:
            data["room_threats"] = [{"location_slug": threat_loc, "related_clock_slugs": []}]
        return SeedPack.model_validate(data)

    def test_passes_when_all_room_ids_match(self) -> None:
        pack = self._pack(clock_scope="R1", threat_loc="R2")
        validate_seed_room_ids(pack, {"R1", "R2", "R3"})  # no raise

    def test_none_scope_is_skipped(self) -> None:
        pack = self._pack()  # no room references
        validate_seed_room_ids(pack, {"R1"})  # no raise

    def test_raises_on_clock_scope_mismatch(self) -> None:
        pack = self._pack(clock_scope="r1")  # lowercase, not in the model
        with pytest.raises(ValueError, match="r1"):
            validate_seed_room_ids(pack, {"R1"})

    def test_raises_on_threat_location_mismatch(self) -> None:
        pack = self._pack(threat_loc="r04")
        with pytest.raises(ValueError, match="r04"):
            validate_seed_room_ids(pack, {"R4"})


class TestDeriveFactionId:
    def test_derive_faction_id_is_deterministic(self) -> None:
        id1 = derive_faction_id("my-campaign", "ossuary-cult")
        id2 = derive_faction_id("my-campaign", "ossuary-cult")
        assert id1 == id2

    def test_derive_faction_id_differs_for_different_slugs(self) -> None:
        assert derive_faction_id("camp", "cult") != derive_faction_id("camp", "guild")

    def test_faction_namespace_isolated_from_actor_and_clock(self) -> None:
        slug = "same-slug"
        assert derive_faction_id("camp", slug) != derive_actor_id("camp", slug)
        assert derive_faction_id("camp", slug) != derive_clock_id("camp", slug)


class TestSeedFactionModel:
    def test_seed_faction_parses_from_dict(self) -> None:
        data = {
            "slug": "ossuary-cult",
            "display_name": "The Ossuary Cult",
            "concept": "Scattered remnants loyal to the Warden's rite.",
            "goal": "Seal the relic before the party can retrieve it.",
            "reputation": "cold",
            "tier": 1,
            "tags": ["antagonist"],
        }
        faction = SeedFaction.model_validate(data)
        assert faction.slug == "ossuary-cult"
        assert faction.display_name == "The Ossuary Cult"
        assert faction.reputation == "cold"
        assert faction.tier == 1
        assert "antagonist" in faction.tags

    def test_seed_faction_defaults(self) -> None:
        faction = SeedFaction(slug="guild", display_name="Merchants Guild")
        assert faction.reputation == "neutral"
        assert faction.tier == 0
        assert faction.status == "active"
        assert faction.tags == []
        assert faction.concept is None
        assert faction.goal is None

    def test_seed_pack_accepts_factions_key(self) -> None:
        data = {
            **_MINIMAL_PACK,
            "factions": [
                {"slug": "ossuary-cult", "display_name": "The Ossuary Cult", "reputation": "cold", "tier": 1}
            ],
        }
        pack = SeedPack.model_validate(data)
        assert len(pack.factions) == 1
        assert pack.factions[0].slug == "ossuary-cult"

    def test_seed_pack_factions_defaults_to_empty(self) -> None:
        pack = SeedPack.model_validate(_MINIMAL_PACK)
        assert pack.factions == []
