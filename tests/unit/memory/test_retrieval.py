from __future__ import annotations

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.retrieval import MemoryRetrieval, MemoryRetriever


class TestMemoryRetriever:
    def test_constructor_stores_campaign_id(self, repo: MemoryRepository) -> None:
        retriever = MemoryRetriever(repo, "camp_abc")
        assert retriever._campaign_id == "camp_abc"

    def test_query_ranked_by_importance_desc_then_recency(self, repo: MemoryRepository) -> None:
        from datetime import datetime, timezone, timedelta
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        repo.save_memory_entry("mem_lo", "camp_001", "event", "Low", importance=2, status="approved")
        repo.add_memory_tag("mem_lo", "theme:guilt")
        repo.save_memory_entry("mem_hi", "camp_001", "event", "High", importance=9, status="approved")
        repo.add_memory_tag("mem_hi", "theme:guilt")
        repo.save_memory_entry("mem_mid_old", "camp_001", "event", "MidOld", importance=5, status="approved")
        repo.add_memory_tag("mem_mid_old", "theme:guilt")
        repo.save_memory_entry("mem_mid_new", "camp_001", "event", "MidNew", importance=5, status="approved")
        repo.add_memory_tag("mem_mid_new", "theme:guilt")
        # Set created_at manually so recency is deterministic
        conn = repo._conn
        conn.execute("UPDATE memory_entries SET created_at = ? WHERE memory_id = 'mem_mid_old'", [base])
        conn.execute("UPDATE memory_entries SET created_at = ? WHERE memory_id = 'mem_mid_new'", [base + timedelta(hours=1)])

        results = MemoryRetriever(repo, "camp_001").query(tags=["theme:guilt"])
        ids = [r.memory_id for r in results]
        # importance 9 first, then mid importance sorted newest-first, then importance 2
        assert ids.index("mem_hi") < ids.index("mem_mid_new")
        assert ids.index("mem_mid_new") < ids.index("mem_mid_old")
        assert ids.index("mem_mid_old") < ids.index("mem_lo")

    def test_query_no_filters_returns_only_approved_for_campaign(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_a", "camp_001", "event", "A", importance=5, status="approved")
        repo.save_memory_entry("mem_b", "camp_001", "event", "B", importance=3, status="draft")
        repo.save_memory_entry("mem_other", "camp_999", "event", "Other", importance=7, status="approved")

        results = MemoryRetriever(repo, "camp_001").query()

        ids = {r.memory_id for r in results}
        assert ids == {"mem_a"}

    def test_query_returns_only_approved_by_default(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_approved", "camp_001", "event", "Approved", status="approved")
        repo.save_memory_entry("mem_draft", "camp_001", "event", "Draft", status="draft")
        repo.save_memory_entry("mem_rejected", "camp_001", "event", "Rejected", status="rejected")
        repo.save_memory_entry("mem_archived", "camp_001", "event", "Archived", status="archived")

        results = MemoryRetriever(repo, "camp_001").query()

        ids = {r.memory_id for r in results}
        assert ids == {"mem_approved"}

    def test_query_include_archived_returns_all_statuses(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_approved", "camp_001", "event", "Approved", status="approved")
        repo.save_memory_entry("mem_draft", "camp_001", "event", "Draft", status="draft")
        repo.save_memory_entry("mem_archived", "camp_001", "event", "Archived", status="archived")

        results = MemoryRetriever(repo, "camp_001").query(include_archived=True)

        ids = {r.memory_id for r in results}
        assert "mem_approved" in ids
        assert "mem_draft" in ids
        assert "mem_archived" in ids

    def test_trim_to_budget_returns_prefix_within_tokens(self, repo: MemoryRepository) -> None:
        from dungeon_daddy.memory.models import MemoryEntry
        entries = [
            MemoryEntry(memory_id=f"m{i}", campaign_id="c", type="event",
                        title="x" * 40, summary="y" * 40, importance=5)
            for i in range(5)
        ]
        # Each entry: (40+40) chars = 80 chars → ~20 tokens. Budget of 50 fits 2.
        kept, omitted = MemoryRetriever(repo, "camp_001").trim_to_budget(entries, max_tokens=50)
        assert len(kept) == 2
        assert omitted == 3

    def test_trim_to_budget_budget_larger_than_all_returns_all(self, repo: MemoryRepository) -> None:
        from dungeon_daddy.memory.models import MemoryEntry
        entries = [
            MemoryEntry(memory_id=f"m{i}", campaign_id="c", type="event",
                        title="short", summary="entry", importance=5)
            for i in range(3)
        ]
        kept, omitted = MemoryRetriever(repo, "camp_001").trim_to_budget(entries, max_tokens=10000)
        assert len(kept) == 3
        assert omitted == 0

    def test_query_by_tag_returns_memory_entries(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("mem_001", "camp_001", "event", "Mara fights", importance=7, status="approved")
        repo.add_memory_tag("mem_001", "actor:pc:mara")
        repo.save_memory_entry("mem_002", "camp_001", "event", "Unrelated", importance=5, status="approved")

        results = MemoryRetriever(repo, "camp_001").query(tags=["actor:pc:mara"])

        assert len(results) == 1
        assert results[0].memory_id == "mem_001"
        assert results[0].title == "Mara fights"


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
            status="approved", importance=9,
        )
        repo.add_memory_tag("mem_001", "fallout:active")
        repo.save_memory_entry(
            "mem_002", "camp_001", "fallout", "Old fallout",
            status="archived", importance=4,
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
