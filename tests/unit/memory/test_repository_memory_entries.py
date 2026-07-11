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

    def test_update_clock_progress_changes_only_filled_and_status(self, repo: MemoryRepository) -> None:
        repo.save_clock(
            "clk_sc", "camp_sc", "Scoped", 6, 1,
            scope_room_id="room_boiler", action_tags=["fight", "move"],
        )
        repo.update_clock_progress("clk_sc", filled=3, status="active")
        clocks = repo.get_clocks("camp_sc")
        assert clocks[0]["filled"] == 3
        assert clocks[0]["scope_room_id"] == "room_boiler"
        assert clocks[0]["action_tags"] == ["fight", "move"]

    def test_update_clock_progress_can_complete_a_clock(self, repo: MemoryRepository) -> None:
        repo.save_clock("clk_sc2", "camp_sc2", "Trap", 4, 3, scope_room_id="room_x")
        repo.update_clock_progress("clk_sc2", filled=4, status="completed")
        clocks = repo.get_clocks("camp_sc2")
        assert clocks[0]["status"] == "completed"
        assert clocks[0]["scope_room_id"] == "room_x"

    def test_save_clock_persists_level_metadata(self, repo: MemoryRepository) -> None:
        repo.save_clock(
            "clk_lv", "camp_lv", "Boiler Trap", 4, 0,
            clock_level="room", category="danger",
            owner_actor_id="actor_xyz", stakes="Room floods.",
            completion_effect="Harder rolls.", visible_to_player=False,
        )
        clocks = repo.get_clocks("camp_lv")
        c = clocks[0]
        assert c["clock_level"] == "room"
        assert c["category"] == "danger"
        assert c["owner_actor_id"] == "actor_xyz"
        assert c["stakes"] == "Room floods."
        assert c["completion_effect"] == "Harder rolls."
        assert c["visible_to_player"] is False

    def test_monotonic_defaults_true_on_round_trip(self, repo: MemoryRepository) -> None:
        repo.save_clock("clk_mono", "camp_mono", "Ritual", 8, 0)
        assert repo.get_clocks("camp_mono")[0]["monotonic"] is True

    def test_non_monotonic_survives_round_trip(self, repo: MemoryRepository) -> None:
        repo.save_clock(
            "clk_intim", "camp_intim", "Dungeon Intimacy", 6, 3,
            category="dungeon_intimacy", monotonic=False,
        )
        assert repo.get_clocks("camp_intim")[0]["monotonic"] is False

    def test_save_clock_persists_level_id(self, repo: MemoryRepository) -> None:
        repo.save_clock(
            "clk_li", "camp_li", "Factory Alert", 8, 0,
            clock_level="level", level_id="level_2",
        )
        clocks = repo.get_clocks("camp_li")
        assert clocks[0]["level_id"] == "level_2"
        assert clocks[0]["clock_level"] == "level"

    def test_update_clock_progress_preserves_level_metadata(self, repo: MemoryRepository) -> None:
        repo.save_clock(
            "clk_meta", "camp_meta", "Quest", 6, 1,
            clock_level="quest", category="objective",
            stakes="Find the key.", completion_effect="Gate opens.",
        )
        repo.update_clock_progress("clk_meta", filled=3, status="active")
        clocks = repo.get_clocks("camp_meta")
        assert clocks[0]["clock_level"] == "quest"
        assert clocks[0]["category"] == "objective"
        assert clocks[0]["stakes"] == "Find the key."
        assert clocks[0]["completion_effect"] == "Gate opens."

    def test_update_clock_scope_does_not_erase_level_metadata(self, repo: MemoryRepository) -> None:
        repo.save_clock(
            "clk_scope", "camp_scope", "Level Alert", 8, 0,
            clock_level="level", level_id="level_2",
            stakes="Factory activates.", completion_effect="Golems patrol.",
        )
        repo.update_clock_scope("clk_scope", scope_room_id="room_control", action_tags=["tinker"])
        clocks = repo.get_clocks("camp_scope")
        assert clocks[0]["clock_level"] == "level"
        assert clocks[0]["stakes"] == "Factory activates."
        assert clocks[0]["scope_room_id"] == "room_control"

    def test_save_clock_persists_tags(self, repo: MemoryRepository) -> None:
        repo.save_clock(
            "clk_tags", "camp_tags", "Trap", 4, 0,
            tags=["trait:noise", "trait:combat"],
        )
        clocks = repo.get_clocks("camp_tags")
        assert clocks[0]["tags"] == ["trait:noise", "trait:combat"]

    def test_save_clock_tags_default_to_empty(self, repo: MemoryRepository) -> None:
        repo.save_clock("clk_notags", "camp_notags", "Trap", 4, 0)
        assert repo.get_clocks("camp_notags")[0]["tags"] == []

    def test_update_clock_scope_can_set_tags(self, repo: MemoryRepository) -> None:
        repo.save_clock("clk_st", "camp_st", "Trap", 4, 0)
        repo.update_clock_scope(
            "clk_st", scope_room_id="room_x", action_tags=[], tags=["trait:noise"]
        )
        clocks = repo.get_clocks("camp_st")
        assert clocks[0]["scope_room_id"] == "room_x"
        assert clocks[0]["action_tags"] == []
        assert clocks[0]["tags"] == ["trait:noise"]

    def test_update_clock_scope_omitting_action_tags_preserves_them(
        self, repo: MemoryRepository
    ) -> None:
        # F5: a co-referenced clock keeps its own action_tags when a scope/tags
        # update omits them (action_tags now defaults to None = "don't touch").
        repo.save_clock("clk_keep", "camp_keep", "Trap", 4, 0, action_tags=["fight"])
        repo.update_clock_scope(
            "clk_keep", scope_room_id="room_y", tags=["trait:noise"]
        )
        clocks = repo.get_clocks("camp_keep")
        assert clocks[0]["scope_room_id"] == "room_y"
        assert clocks[0]["tags"] == ["trait:noise"]
        assert clocks[0]["action_tags"] == ["fight"]  # untouched


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

    def test_update_memory_status_persists_change(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_001", "camp_001", "event", "Title")
        assert repo.get_memory_entry("mem_001")["status"] == "draft"
        repo.update_memory_status("mem_001", "approved")
        assert repo.get_memory_entry("mem_001")["status"] == "approved"

    def test_update_memory_status_all_valid_values(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_001", "camp_001", "event", "Title")
        for status in ("approved", "rejected", "archived", "draft"):
            repo.update_memory_status("mem_001", status)
            assert repo.get_memory_entry("mem_001")["status"] == status
