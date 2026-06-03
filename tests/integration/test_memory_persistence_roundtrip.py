"""Integration: RPG state and memory survive a repository restart."""
from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.markdown_store import compute_checksum, read_memory, write_memory
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.retrieval import MemoryRetrieval
from dungeon_daddy.memory.sync import SyncReporter

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "campaign.duckdb"


@pytest.fixture
def memory_root(tmp_path: Path) -> Path:
    root = tmp_path / "memory"
    root.mkdir()
    return root


class TestRPGStateRoundtrip:
    def test_campaign_actor_clock_survive_restart(
        self, db_path: Path
    ) -> None:
        # Write session
        repo = MemoryRepository(db_path)
        repo.initialize_schema(MIGRATIONS_DIR)
        repo.save_campaign("camp_001", "dungeon-run", "The Dungeon Run")
        repo.save_actor("pc_mara", "camp_001", "pc", "mara", "Mara")
        repo.save_actor_stress_track("pc_mara", "weird", 4, 2)
        repo.save_actor_action_rating("pc_mara", "sway", 3)
        repo.save_clock("clk_ritual", "camp_001", "Ritual advances", 8, 4)
        repo.close()

        # Restart
        repo2 = MemoryRepository(db_path)
        camp = repo2.get_campaign("camp_001")
        assert camp is not None
        assert camp["title"] == "The Dungeon Run"

        actor = repo2.get_actor("pc_mara")
        assert actor is not None
        assert actor["display_name"] == "Mara"

        tracks = repo2.get_actor_stress_tracks("pc_mara")
        weird = next(t for t in tracks if t["track_key"] == "weird")
        assert weird["filled"] == 2

        ratings = repo2.get_actor_action_ratings("pc_mara")
        sway = next(r for r in ratings if r["action_key"] == "sway")
        assert sway["rating"] == 3

        clocks = repo2.get_clocks("camp_001")
        assert clocks[0]["filled"] == 4
        repo2.close()


class TestMemoryEntryRoundtrip:
    def test_memory_entry_writes_db_and_markdown(
        self, db_path: Path, memory_root: Path
    ) -> None:
        repo = MemoryRepository(db_path)
        repo.initialize_schema(MIGRATIONS_DIR)

        # Write entry to DB
        repo.save_memory_entry(
            "mem_001", "camp_001", "event", "The altar awakens",
            summary="The party disturbed the altar.", importance=8,
        )
        repo.add_memory_tag("mem_001", "actor:pc:mara")
        repo.add_memory_tag("mem_001", "location:moonlit-cathedral")

        # Write Markdown file
        md_path = memory_root / "mem_001.md"
        write_memory(
            md_path,
            {
                "id": "mem_001",
                "type": "event",
                "campaign_id": "camp_001",
                "updated_at": "2026-06-02T00:00:00Z",
                "tags": ["actor:pc:mara", "location:moonlit-cathedral"],
            },
            "# The altar awakens\n\nThe party disturbed the altar.",
        )
        checksum = compute_checksum(md_path)
        repo.update_memory_checksum("mem_001", checksum, str(md_path))
        repo.close()

        # Restart and verify
        repo2 = MemoryRepository(db_path)
        entry = repo2.get_memory_entry("mem_001")
        assert entry["checksum"] == checksum
        assert entry["markdown_path"] == str(md_path)

        # Parse Markdown and validate
        fm, body = read_memory(md_path)
        assert fm["id"] == "mem_001"
        assert "altar" in body
        repo2.close()

    def test_sync_report_passes_for_clean_campaign(
        self, db_path: Path, memory_root: Path
    ) -> None:
        repo = MemoryRepository(db_path)
        repo.initialize_schema(MIGRATIONS_DIR)

        md_path = memory_root / "mem_001.md"
        write_memory(
            md_path,
            {
                "id": "mem_001",
                "type": "event",
                "campaign_id": "camp_001",
                "updated_at": "2026-06-02T00:00:00Z",
            },
            "# Clean memory",
        )
        checksum = compute_checksum(md_path)
        repo.save_memory_entry(
            "mem_001", "camp_001", "event", "Clean memory",
            markdown_path=str(md_path), checksum=checksum,
        )

        reporter = SyncReporter(repo, memory_root)
        issues = reporter.check()
        assert issues == []
        repo.close()

    def test_retrieval_by_actor_works_after_restart(
        self, db_path: Path
    ) -> None:
        repo = MemoryRepository(db_path)
        repo.initialize_schema(MIGRATIONS_DIR)
        repo.save_memory_entry("mem_001", "camp_001", "event", "Mara's action", importance=7)
        repo.add_memory_tag("mem_001", "actor:pc:mara")
        repo.save_memory_entry("mem_002", "camp_001", "lore", "Dungeon history", importance=4)
        repo.close()

        repo2 = MemoryRepository(db_path)
        retrieval = MemoryRetrieval(repo2)
        results = retrieval.by_actor("actor:pc:mara")
        assert len(results) == 1
        assert results[0]["memory_id"] == "mem_001"
        repo2.close()
