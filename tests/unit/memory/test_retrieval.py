from __future__ import annotations

from datetime import UTC

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.retrieval import (
    MemoryRetrieval,
    MemoryRetriever,
    present_actor_ids,
    scene_memory_tags,
)


class TestMemoryRetriever:
    def test_constructor_stores_campaign_id(self, repo: MemoryRepository) -> None:
        retriever = MemoryRetriever(repo, "camp_abc")
        assert retriever._campaign_id == "camp_abc"

    def test_query_ranked_by_importance_desc_then_recency(self, repo: MemoryRepository) -> None:
        from datetime import datetime, timedelta
        base = datetime(2026, 1, 1, tzinfo=UTC)
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

    def test_query_actor_ids_resolve_to_canonical_actor_tags(
        self, repo: MemoryRepository
    ) -> None:
        """§5.1: an actor_id resolves through the record to its canonical
        `actor:<subtype>:<slug>` tag — an npc/monster maps to `actor:npc:`,
        never the old two-segment `actor:<id>`."""
        repo.save_actor("act_ws", "camp_001", "npc", "wraith-steward", "Wraith Steward")
        repo.save_memory_entry(
            "mem_canon", "camp_001", "event", "The steward bargains",
            importance=6, status="approved",
        )
        repo.add_memory_tag("mem_canon", "actor:npc:wraith-steward")
        # decoy tagged with the old broken two-segment form the fix must drop
        repo.save_memory_entry(
            "mem_old", "camp_001", "event", "Old form", importance=6, status="approved",
        )
        repo.add_memory_tag("mem_old", "actor:act_ws")

        results = MemoryRetriever(repo, "camp_001").query(actor_ids=["act_ws"])

        ids = {r.memory_id for r in results}
        assert ids == {"mem_canon"}

    def test_query_actor_ids_unknown_actor_is_skipped(
        self, repo: MemoryRepository
    ) -> None:
        """An actor_id with no record contributes no filter (no crash)."""
        repo.save_memory_entry(
            "mem_x", "camp_001", "event", "X", importance=5, status="approved",
        )
        repo.add_memory_tag("mem_x", "theme:guilt")

        results = MemoryRetriever(repo, "camp_001").query(actor_ids=["ghost"])

        assert results == []

    def test_query_actor_ids_ignores_cross_campaign_actor(
        self, repo: MemoryRepository
    ) -> None:
        """BUG 4: an actor_id belonging to another campaign contributes no
        filter (get_actor is not campaign-scoped) — a same-slug memory in this
        campaign must not leak in."""
        repo.save_actor("act_other", "camp_999", "npc", "wraith-steward", "WS")
        repo.save_memory_entry(
            "mem_here", "camp_001", "event", "Here", importance=5, status="approved",
        )
        repo.add_memory_tag("mem_here", "actor:npc:wraith-steward")

        results = MemoryRetriever(repo, "camp_001").query(actor_ids=["act_other"])

        assert results == []


class TestPresentActorIds:
    def test_party_plus_room_npcs_and_monsters(self, repo: MemoryRepository) -> None:
        repo.save_actor("npc-1", "camp_001", "npc", "goblin", "Goblin", room_id="R1")
        repo.save_actor("mon-1", "camp_001", "monster", "ogre", "Ogre", room_id="R1")
        # a PC standing in the room is not double-added via the room query
        repo.save_actor("pc-1", "camp_001", "pc", "hero", "Hero", room_id="R1")

        ids = present_actor_ids(repo, "camp_001", "R1", ["pc-1"])

        assert ids[0] == "pc-1"  # party first, order preserved
        assert set(ids) == {"pc-1", "npc-1", "mon-1"}
        assert ids.count("pc-1") == 1

    def test_empty_or_none_room_is_party_only(self, repo: MemoryRepository) -> None:
        repo.save_actor("npc-1", "camp_001", "npc", "goblin", "Goblin", room_id="R1")
        assert present_actor_ids(repo, "camp_001", "", ["pc-1"]) == ["pc-1"]
        assert present_actor_ids(repo, "camp_001", None, ["pc-1"]) == ["pc-1"]


class TestSceneMemoryTags:
    """A5b write-side twin of present_actor_ids: the canonical scene-anchor tags
    to stamp on an engine memory write, symmetric with the reader's filters."""

    def test_location_and_present_actor_tags(self, repo: MemoryRepository) -> None:
        repo.save_actor("pc-1", "camp_001", "pc", "mara", "Mara", room_id="R1")
        repo.save_actor("npc-1", "camp_001", "npc", "goblin", "Goblin", room_id="R1")
        # a co-located monster maps to the actor:npc subtype (T2 / owner ruling)
        repo.save_actor("mon-1", "camp_001", "monster", "ogre", "Ogre", room_id="R1")

        tags = scene_memory_tags(repo, "camp_001", "R1", ["pc-1"])

        assert tags[0] == "location:R1"  # grid room id, location tag first
        assert set(tags) == {
            "location:R1",
            "actor:pc:mara",
            "actor:npc:goblin",
            "actor:npc:ogre",
        }

    def test_no_room_is_actor_tags_only(self, repo: MemoryRepository) -> None:
        repo.save_actor("pc-1", "camp_001", "pc", "mara", "Mara", room_id="R1")
        # no room -> no location tag and no room-NPC expansion; party only
        assert scene_memory_tags(repo, "camp_001", None, ["pc-1"]) == ["actor:pc:mara"]

    def test_unknown_or_cross_campaign_actor_contributes_no_tag(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_actor("other", "camp_999", "pc", "mara", "Mara", room_id="R1")
        # unknown id + a cross-campaign id both resolve to nothing; empty room
        assert scene_memory_tags(repo, "camp_001", None, ["ghost", "other"]) == []


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
