from __future__ import annotations

from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.seed_pack import (
    SeedPack,
    apply_seed_pack,
    derive_clock_id,
    derive_memory_id,
)
from tests.unit.memory.conftest import MIGRATIONS_DIR


class TestContextBundleBuilder:
    def test_constructor_stores_params(self) -> None:
        builder = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id="scene_001",
            mode="run_scene",
            focus_actor_ids=["actor_001"],
            token_budget=500,
        )
        assert builder._campaign_id == "camp_001"
        assert builder._scene_id == "scene_001"
        assert builder._mode == "run_scene"
        assert builder._focus_actor_ids == ["actor_001"]
        assert builder._token_budget == 500

    def test_build_with_no_data_returns_empty_collections(
        self, repo: MemoryRepository
    ) -> None:
        builder = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        )
        bundle = builder.build(repo)
        assert bundle.memory_cards == []
        assert bundle.active_fallout == []
        assert bundle.open_clocks == []
        assert bundle.mechanical_state == {}
        assert bundle.must_remember == []

    def test_build_with_unknown_actor_returns_empty_actor_state(
        self, repo: MemoryRepository
    ) -> None:
        builder = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=["actor_does_not_exist"],
            token_budget=500,
        )
        bundle = builder.build(repo)
        actor_state = bundle.mechanical_state.get("actor_does_not_exist")
        assert actor_state is not None
        assert actor_state["action_ratings"] == []
        assert actor_state["stress_tracks"] == []

    def test_build_returns_context_bundle_with_core_fields(
        self, repo: MemoryRepository
    ) -> None:
        from dungeon_daddy.memory.models import ContextBundle

        builder = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id="scene_001",
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        )
        bundle = builder.build(repo)

        assert isinstance(bundle, ContextBundle)
        assert bundle.campaign_id == "camp_001"
        assert bundle.scene_id == "scene_001"
        assert bundle.mode == "run_scene"
        assert bundle.bundle_id  # non-empty

    def test_build_populates_scene_brief_from_scenes_table(
        self, repo: MemoryRepository
    ) -> None:
        repo._conn.execute(
            "INSERT INTO scenes (scene_id, campaign_id, location_slug, status)"
            " VALUES (?, ?, ?, ?)",
            ["scene_001", "camp_001", "moonlit-cathedral", "active"],
        )
        builder = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id="scene_001",
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        )
        bundle = builder.build(repo)

        assert bundle.scene_brief["location_slug"] == "moonlit-cathedral"
        assert bundle.scene_brief["status"] == "active"

    def test_build_mechanical_state_includes_focus_actor_data(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_actor("actor_001", "camp_001", "pc", "mara", "Mara")
        repo.save_actor_action_rating("actor_001", "prowl", 2)
        repo.save_actor_stress_track("actor_001", "body", 6, 3)

        builder = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=["actor_001"],
            token_budget=500,
        )
        bundle = builder.build(repo)

        actor_data = bundle.mechanical_state.get("actor_001")
        assert actor_data is not None
        assert {"action_key": "prowl", "rating": 2} in actor_data["action_ratings"]
        assert {"track_key": "body", "capacity": 6, "filled": 3} in actor_data["stress_tracks"]

    def test_build_active_fallout_excludes_resolved(
        self, repo: MemoryRepository
    ) -> None:
        from dungeon_daddy.rpg.models import FalloutRecord

        repo.save_fallout_record(
            FalloutRecord(
                fallout_id="fall_001",
                campaign_id="camp_001",
                actor_id="actor_001",
                track_key="body",
                severity="minor",
                title="Bruised",
                summary="Light hit",
                status="active",
            )
        )
        repo.save_fallout_record(
            FalloutRecord(
                fallout_id="fall_002",
                campaign_id="camp_001",
                actor_id="actor_001",
                track_key="body",
                severity="minor",
                title="Healed",
                summary="Recovered",
                status="resolved",
            )
        )

        builder = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=["actor_001"],
            token_budget=500,
        )
        bundle = builder.build(repo)

        fallout_ids = {f["fallout_id"] for f in bundle.active_fallout}
        assert "fall_001" in fallout_ids
        assert "fall_002" not in fallout_ids

    def test_build_open_clocks_excludes_completed(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_clock("clk_001", "camp_001", "Dungeon Awakens", 8, 3, "active")
        repo.save_clock("clk_002", "camp_001", "Old Quest", 4, 4, "completed")

        builder = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        )
        bundle = builder.build(repo)

        clock_ids = {c["clock_id"] for c in bundle.open_clocks}
        assert "clk_001" in clock_ids
        assert "clk_002" not in clock_ids

    def test_build_open_clocks_includes_all_metadata_fields(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_clock(
            "clk_meta", "camp_001", "Boiler Trap Primes", 4, 1, "active",
            scope_room_id="boiler_room",
            action_tags=["move", "tinker"],
            clock_level="room",
            category="danger",
            level_id=None,
            owner_actor_id=None,
            stakes="Room becomes dangerous.",
            completion_effect="Steam erupts.",
            visible_to_player=True,
        )
        builder = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        )
        bundle = builder.build(repo)

        clock = next(c for c in bundle.open_clocks if c["clock_id"] == "clk_meta")
        assert clock["clock_level"] == "room"
        assert clock["category"] == "danger"
        assert clock["scope_room_id"] == "boiler_room"
        assert clock["action_tags"] == ["move", "tinker"]
        assert clock["stakes"] == "Room becomes dangerous."
        assert clock["completion_effect"] == "Steam erupts."

    def test_build_memory_cards_trimmed_to_token_budget(
        self, repo: MemoryRepository
    ) -> None:
        # Each entry title+summary = 80 chars → ~20 tokens. Budget 50 fits 2.
        for i in range(5):
            repo.save_memory_entry(
                f"mem_{i:03d}", "camp_001", "event", "x" * 40,
                summary="y" * 40, importance=5, status="approved",
            )

        builder = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=50,
        )
        bundle = builder.build(repo)

        assert len(bundle.memory_cards) == 2

    def test_build_provenance_records_counts_and_criteria(
        self, repo: MemoryRepository
    ) -> None:
        # Slice A5: retrieval is scene-scoped, so the focus actor must exist and
        # the memories must be tagged to it to be in scene.
        repo.save_actor("actor_001", "camp_001", "pc", "mara", "Mara")
        for i in range(5):
            repo.save_memory_entry(
                f"mem_{i:03d}", "camp_001", "event", "x" * 40,
                summary="y" * 40, importance=5, status="approved",
            )
            repo.add_memory_tag(f"mem_{i:03d}", "actor:pc:mara")

        builder = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=["actor_001"],
            token_budget=50,
        )
        bundle = builder.build(repo)

        assert bundle.provenance["retrieved"] == 5
        assert bundle.provenance["omitted"] == 3
        assert bundle.provenance["focus_actor_ids"] == ["actor_001"]

    def test_build_must_remember_included_when_budget_exhausted(
        self, repo: MemoryRepository
    ) -> None:
        # Three normal-importance entries that fill the budget
        for i in range(3):
            repo.save_memory_entry(
                f"mem_{i:03d}", "camp_001", "event", "x" * 40,
                summary="y" * 40, importance=5, status="approved",
            )
        # A must-remember entry with importance >= 9
        repo.save_memory_entry(
            "mem_must", "camp_001", "event", "Critical Fact",
            summary="Must know this", importance=9, status="approved",
        )

        builder = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=1,  # budget too small for anything
        )
        bundle = builder.build(repo)

        # must_remember lists the pinned entry ID
        assert "mem_must" in bundle.must_remember
        # the card still appears in memory_cards
        card_ids = {c["memory_id"] for c in bundle.memory_cards}
        assert "mem_must" in card_ids


_SEED_PACK_DATA = {
    "campaign_slug": "test-campaign",
    "player_side": {"label": "The Party", "actors": []},
    "dungeon_side": {"actors": []},
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
            "tags": ["thread:main-quest"],
        }
    ],
    "room_threats": [],
}


class TestSeededDataInContextBundle:
    def test_seeded_clock_appears_in_open_clocks(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(_SEED_PACK_DATA)
        apply_seed_pack(pack, "camp_001", repo, MIGRATIONS_DIR)

        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        ).build(repo)

        expected_clock_id = derive_clock_id("test-campaign", "bone-warden-stirs")
        clock_ids = {c["clock_id"] for c in bundle.open_clocks}
        assert expected_clock_id in clock_ids

    def test_seeded_memory_appears_in_memory_cards(self, repo: MemoryRepository) -> None:
        pack = SeedPack.model_validate(_SEED_PACK_DATA)
        apply_seed_pack(pack, "camp_001", repo, MIGRATIONS_DIR)

        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        ).build(repo)

        expected_memory_id = derive_memory_id("test-campaign", "The Expedition's Purpose")
        card_ids = {c["memory_id"] for c in bundle.memory_cards}
        assert expected_memory_id in card_ids


class TestOpenClocksOwnerDisplayName:
    def test_character_clock_owner_display_name_resolved(
        self, repo: MemoryRepository
    ) -> None:
        actor_id = "actor:camp:mara"
        repo.save_actor(actor_id, "camp_001", "pc", "mara", "Mara Coldwell")
        repo.save_clock(
            "clk_char", "camp_001", "Mara Trusts", 6, 0, "active",
            clock_level="character",
            owner_actor_id=actor_id,
        )
        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        ).build(repo)
        clock = next(c for c in bundle.open_clocks if c["clock_id"] == "clk_char")
        assert clock.get("owner_display_name") == "Mara Coldwell"

    def test_clock_without_owner_has_no_display_name(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_clock("clk_no_owner", "camp_001", "Dungeon Stirs", 8, 0, "active")
        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        ).build(repo)
        clock = next(c for c in bundle.open_clocks if c["clock_id"] == "clk_no_owner")
        assert clock.get("owner_display_name") is None
