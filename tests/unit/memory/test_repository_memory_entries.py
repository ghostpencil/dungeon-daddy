from __future__ import annotations

from dungeon_daddy.memory.repository import MemoryRepository


# ---------------------------------------------------------------------------
# Campaign persistence
# ---------------------------------------------------------------------------


class TestCampaignPersistence:
    def test_save_and_get_campaign(self, repo: MemoryRepository) -> None:
        repo.save_campaign(
            campaign_id="camp_001",
            slug="dungeon-run",
            title="The Dungeon Run",
            status="active",
        )
        row = repo.get_campaign("camp_001")
        assert row is not None
        assert row["campaign_id"] == "camp_001"
        assert row["title"] == "The Dungeon Run"
        assert row["slug"] == "dungeon-run"

    def test_save_campaign_upserts_on_conflict(self, repo: MemoryRepository) -> None:
        repo.save_campaign("camp_001", "slug-a", "Title A")
        repo.save_campaign("camp_001", "slug-b", "Title B")
        row = repo.get_campaign("camp_001")
        assert row["title"] == "Title B"

    def test_get_campaign_returns_none_for_missing(self, repo: MemoryRepository) -> None:
        assert repo.get_campaign("nonexistent") is None

    def test_save_campaign_persists_dungeon_slug(self, repo: MemoryRepository) -> None:
        repo.save_campaign(
            campaign_id="camp_001",
            slug="dungeon-run",
            title="The Dungeon Run",
            dungeon_slug="the-tomb-of-ash",
        )
        row = repo.get_campaign("camp_001")
        assert row is not None
        assert row["dungeon_slug"] == "the-tomb-of-ash"

    def test_save_campaign_dungeon_slug_defaults_to_none(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_campaign(campaign_id="camp_002", slug="plain-run", title="Plain Run")
        row = repo.get_campaign("camp_002")
        assert row is not None
        assert row["dungeon_slug"] is None


# ---------------------------------------------------------------------------
# Actor persistence
# ---------------------------------------------------------------------------


class TestActorPersistence:
    def test_save_and_get_actor(self, repo: MemoryRepository) -> None:
        repo.save_actor(
            actor_id="pc_mara",
            campaign_id="camp_001",
            actor_type="pc",
            slug="mara",
            display_name="Mara",
        )
        row = repo.get_actor("pc_mara")
        assert row is not None
        assert row["actor_id"] == "pc_mara"
        assert row["display_name"] == "Mara"
        assert row["status"] == "active"

    def test_save_and_get_stress_tracks(self, repo: MemoryRepository) -> None:
        repo.save_actor("pc_mara", "camp_001", "pc", "mara", "Mara")
        repo.save_actor_stress_track("pc_mara", "body", capacity=6, filled=2)
        repo.save_actor_stress_track("pc_mara", "weird", capacity=4, filled=0)
        tracks = repo.get_actor_stress_tracks("pc_mara")
        keys = {t["track_key"] for t in tracks}
        assert keys == {"body", "weird"}
        body = next(t for t in tracks if t["track_key"] == "body")
        assert body["filled"] == 2

    def test_stress_track_upsert_updates_filled(self, repo: MemoryRepository) -> None:
        repo.save_actor("pc_mara", "camp_001", "pc", "mara", "Mara")
        repo.save_actor_stress_track("pc_mara", "body", 6, 1)
        repo.save_actor_stress_track("pc_mara", "body", 6, 3)
        tracks = repo.get_actor_stress_tracks("pc_mara")
        assert tracks[0]["filled"] == 3

    def test_save_and_get_action_ratings(self, repo: MemoryRepository) -> None:
        repo.save_actor("pc_mara", "camp_001", "pc", "mara", "Mara")
        repo.save_actor_action_rating("pc_mara", "fight", 2)
        repo.save_actor_action_rating("pc_mara", "sway", 1)
        ratings = repo.get_actor_action_ratings("pc_mara")
        keys = {r["action_key"] for r in ratings}
        assert keys == {"fight", "sway"}
        fight = next(r for r in ratings if r["action_key"] == "fight")
        assert fight["rating"] == 2


# ---------------------------------------------------------------------------
# Clock persistence
# ---------------------------------------------------------------------------


class TestClockPersistence:
    def test_save_and_get_clocks(self, repo: MemoryRepository) -> None:
        repo.save_clock(
            clock_id="clk_001",
            campaign_id="camp_001",
            label="The ritual advances",
            segments=8,
            filled=3,
            status="active",
        )
        clocks = repo.get_clocks("camp_001")
        assert len(clocks) == 1
        assert clocks[0]["clock_id"] == "clk_001"
        assert clocks[0]["filled"] == 3

    def test_save_clock_upserts(self, repo: MemoryRepository) -> None:
        repo.save_clock("clk_001", "camp_001", "Ritual", 8, 3)
        repo.save_clock("clk_001", "camp_001", "Ritual", 8, 6, status="completed")
        clocks = repo.get_clocks("camp_001")
        assert clocks[0]["filled"] == 6
        assert clocks[0]["status"] == "completed"

    def test_get_clocks_filters_by_campaign(self, repo: MemoryRepository) -> None:
        repo.save_clock("clk_a", "camp_a", "A", 4, 0)
        repo.save_clock("clk_b", "camp_b", "B", 4, 0)
        assert len(repo.get_clocks("camp_a")) == 1
        assert repo.get_clocks("camp_a")[0]["clock_id"] == "clk_a"


# ---------------------------------------------------------------------------
# Action resolution persistence
# ---------------------------------------------------------------------------


class TestActionResolutionPersistence:
    def test_save_action_resolution(self, repo: MemoryRepository) -> None:
        repo.save_action_resolution(
            resolution_id="res_001",
            campaign_id="camp_001",
            actor_id="pc_mara",
            action_key="sway",
            outcome="full",
            scene_id="scn_001",
        )
        rows = repo.get_action_resolutions("camp_001")
        assert len(rows) == 1
        assert rows[0]["resolution_id"] == "res_001"
        assert rows[0]["outcome"] == "full"

    def test_get_action_resolutions_filters_by_campaign(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_action_resolution("res_a", "camp_a", "pc_x", "fight", "miss")
        repo.save_action_resolution("res_b", "camp_b", "pc_y", "move", "partial")
        assert len(repo.get_action_resolutions("camp_a")) == 1


# ---------------------------------------------------------------------------
# Memory entry CRUD
# ---------------------------------------------------------------------------


class TestMemoryEntryCRUD:
    def test_save_and_get_memory_entry(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry(
            memory_id="mem_001",
            campaign_id="camp_001",
            entry_type="event",
            title="The altar awakens",
            summary="The party disturbed the altar.",
            importance=8,
        )
        entry = repo.get_memory_entry("mem_001")
        assert entry is not None
        assert entry["memory_id"] == "mem_001"
        assert entry["title"] == "The altar awakens"
        assert entry["importance"] == 8

    def test_save_memory_entry_upserts(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_001", "camp_001", "event", "Old title", importance=5)
        repo.save_memory_entry("mem_001", "camp_001", "event", "New title", importance=9)
        entry = repo.get_memory_entry("mem_001")
        assert entry["title"] == "New title"
        assert entry["importance"] == 9

    def test_get_memory_entry_returns_none_for_missing(
        self, repo: MemoryRepository
    ) -> None:
        assert repo.get_memory_entry("nonexistent") is None

    def test_add_and_get_memory_tags(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_001", "camp_001", "event", "Title")
        repo.add_memory_tag("mem_001", "actor:pc:mara")
        repo.add_memory_tag("mem_001", "theme:guilt")
        tags = repo.get_memory_tags("mem_001")
        assert set(tags) == {"actor:pc:mara", "theme:guilt"}

    def test_add_memory_tag_is_idempotent(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_001", "camp_001", "event", "Title")
        repo.add_memory_tag("mem_001", "actor:pc:mara")
        repo.add_memory_tag("mem_001", "actor:pc:mara")
        assert len(repo.get_memory_tags("mem_001")) == 1

    def test_add_and_get_memory_links(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_001", "camp_001", "event", "A")
        repo.save_memory_entry("mem_002", "camp_001", "actor", "B")
        repo.add_memory_link("mem_001", "mem_002", "involves")
        links = repo.get_memory_links("mem_001")
        assert len(links) == 1
        assert links[0]["to_id"] == "mem_002"
        assert links[0]["link_type"] == "involves"

    def test_update_memory_checksum(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_001", "camp_001", "event", "Title")
        repo.update_memory_checksum("mem_001", "abc123", "memory/camp/mem_001.md")
        entry = repo.get_memory_entry("mem_001")
        assert entry["checksum"] == "abc123"
        assert entry["markdown_path"] == "memory/camp/mem_001.md"
