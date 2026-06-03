from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.retrieval import MemoryRetrieval

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(db_path=tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


class TestRetrievalByActor:
    def test_by_actor_returns_tagged_entries(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_001", "camp_001", "event", "Mara acts", importance=7)
        repo.add_memory_tag("mem_001", "actor:pc:mara")
        repo.save_memory_entry("mem_002", "camp_001", "event", "Unrelated", importance=5)

        results = MemoryRetrieval(repo).by_actor("actor:pc:mara")
        ids = [r["memory_id"] for r in results]
        assert "mem_001" in ids
        assert "mem_002" not in ids

    def test_by_actor_returns_empty_when_no_match(self, repo: MemoryRepository) -> None:
        results = MemoryRetrieval(repo).by_actor("actor:pc:nobody")
        assert results == []


class TestRetrievalByLocation:
    def test_by_location_returns_tagged_entries(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_001", "camp_001", "location", "Cathedral", importance=6)
        repo.add_memory_tag("mem_001", "location:moonlit-cathedral")
        repo.save_memory_entry("mem_002", "camp_001", "event", "Other", importance=3)

        results = MemoryRetrieval(repo).by_location("location:moonlit-cathedral")
        ids = [r["memory_id"] for r in results]
        assert "mem_001" in ids
        assert "mem_002" not in ids


class TestRetrievalByTag:
    def test_by_tag_returns_entries_with_tag(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_001", "camp_001", "event", "A", importance=5)
        repo.add_memory_tag("mem_001", "theme:guilt")
        repo.save_memory_entry("mem_002", "camp_001", "event", "B", importance=5)
        repo.add_memory_tag("mem_002", "theme:redemption")

        results = MemoryRetrieval(repo).by_tag("theme:guilt")
        ids = [r["memory_id"] for r in results]
        assert "mem_001" in ids
        assert "mem_002" not in ids

    def test_by_tag_active_fallout_type(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry(
            "mem_001", "camp_001", "fallout", "Mara's fallout",
            status="active", importance=9,
        )
        repo.add_memory_tag("mem_001", "fallout:active")
        repo.save_memory_entry(
            "mem_002", "camp_001", "fallout", "Old fallout",
            status="resolved", importance=4,
        )
        repo.add_memory_tag("mem_002", "fallout:resolved")

        results = MemoryRetrieval(repo).by_tag("fallout:active")
        ids = [r["memory_id"] for r in results]
        assert "mem_001" in ids
        assert "mem_002" not in ids


class TestRetrievalRanking:
    def test_results_ranked_by_importance_descending(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_memory_entry("mem_lo", "camp_001", "event", "Low", importance=2)
        repo.add_memory_tag("mem_lo", "theme:guilt")
        repo.save_memory_entry("mem_hi", "camp_001", "event", "High", importance=9)
        repo.add_memory_tag("mem_hi", "theme:guilt")
        repo.save_memory_entry("mem_mid", "camp_001", "event", "Mid", importance=5)
        repo.add_memory_tag("mem_mid", "theme:guilt")

        results = MemoryRetrieval(repo).by_tag("theme:guilt")
        importances = [r["importance"] for r in results]
        assert importances == sorted(importances, reverse=True)
