"""Integration: ContextBundleBuilder builds from real DuckDB; retriever filters and trims."""
from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.retrieval import MemoryRetriever
from dungeon_daddy.rpg.models import FalloutRecord, RoomObject

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


@pytest.fixture
def repo(tmp_path: Path):
    db = MemoryRepository(tmp_path / "campaign.duckdb")
    db.initialize_schema(MIGRATIONS_DIR)
    _seed(db)
    yield db
    db.close()


def _seed(repo: MemoryRepository) -> None:
    repo.save_campaign("camp-1", "slug-1", "Test Campaign")
    repo._conn.execute(
        "INSERT INTO scenes (scene_id, campaign_id, location_slug, status) VALUES (?, ?, ?, ?)",
        ["scene-1", "camp-1", "crypt", "active"],
    )
    repo.save_actor("actor-1", "camp-1", "pc", "mara", "Mara")
    repo.save_actor_action_rating("actor-1", "skirmish", 2)
    repo.save_actor_stress_track("actor-1", "body", 6, 1)
    repo.save_clock("clk-1", "camp-1", "Ritual", 6, 3, "active")
    repo.save_fallout_record(FalloutRecord(
        fallout_id="fall-1", campaign_id="camp-1", actor_id="actor-1",
        track_key="body", severity="minor", title="Bruised", summary="Took a hit.",
    ))
    repo.save_memory_entry("mem-1", "camp-1", "event", "The Pact",
                           summary="Party made a deal.", importance=9, status="approved")
    repo.add_memory_tag("mem-1", "actor:pc:mara")
    repo.save_memory_entry("mem-2", "camp-1", "lore", "Crypt Legend",
                           summary="Ancient tales.", importance=5, status="approved")
    repo.add_memory_tag("mem-2", "location:crypt")
    repo.save_memory_entry("mem-3", "camp-1", "event", "Side Note",
                           summary="Unrelated.", importance=3, status="approved")
    repo.save_memory_entry("mem-4", "camp-1", "event", "Old Secret",
                           summary="Archived.", importance=8, status="archived")


# ---------------------------------------------------------------------------
# Bullet 1: build() populates all bundle fields from seeded data
# ---------------------------------------------------------------------------

class TestContextBundleBuilderIntegration:
    def test_build_populates_scene_brief(self, repo):
        bundle = ContextBundleBuilder("camp-1", "scene-1", "run_scene", ["actor-1"], 1000).build(repo)
        assert bundle.scene_brief["location_slug"] == "crypt"
        assert bundle.scene_brief["status"] == "active"

    def test_build_populates_mechanical_state(self, repo):
        bundle = ContextBundleBuilder("camp-1", "scene-1", "run_scene", ["actor-1"], 1000).build(repo)
        state = bundle.mechanical_state["actor-1"]
        assert any(r["action_key"] == "skirmish" for r in state["action_ratings"])
        assert any(t["track_key"] == "body" for t in state["stress_tracks"])

    def test_build_populates_open_clocks(self, repo):
        bundle = ContextBundleBuilder("camp-1", "scene-1", "run_scene", ["actor-1"], 1000).build(repo)
        assert len(bundle.open_clocks) == 1
        assert bundle.open_clocks[0]["label"] == "Ritual"

    def test_build_populates_active_fallout(self, repo):
        bundle = ContextBundleBuilder("camp-1", "scene-1", "run_scene", ["actor-1"], 1000).build(repo)
        assert len(bundle.active_fallout) == 1
        assert bundle.active_fallout[0]["actor_id"] == "actor-1"

    def test_build_excludes_archived_memory(self, repo):
        bundle = ContextBundleBuilder("camp-1", "scene-1", "run_scene", ["actor-1"], 1000).build(repo)
        ids = [c["memory_id"] for c in bundle.memory_cards]
        assert "mem-4" not in ids

    def test_build_must_remember_pins_importance_nine_entries(self, repo):
        bundle = ContextBundleBuilder("camp-1", "scene-1", "run_scene", ["actor-1"], 1000).build(repo)
        assert "mem-1" in bundle.must_remember


# ---------------------------------------------------------------------------
# Bullet 2: retriever query filters by tag, actor, and location
# ---------------------------------------------------------------------------

class TestMemoryRetrieverFilters:
    def test_query_by_tag_returns_matching_entry(self, repo):
        retriever = MemoryRetriever(repo, "camp-1")
        results = retriever.query(tags=["actor:pc:mara"])
        assert len(results) == 1
        assert results[0].memory_id == "mem-1"

    def test_query_actor_ids_build_canonical_tag_from_record(self, repo):
        # actor-1 is a pc named "mara" -> actor:pc:mara matches mem-1
        retriever = MemoryRetriever(repo, "camp-1")
        results = retriever.query(actor_ids=["actor-1"])
        assert [r.memory_id for r in results] == ["mem-1"]

    def test_query_by_location_slug_returns_matching_entry(self, repo):
        retriever = MemoryRetriever(repo, "camp-1")
        results = retriever.query(location_slug="crypt")
        assert len(results) == 1
        assert results[0].memory_id == "mem-2"

    def test_query_no_filters_returns_all_active_entries(self, repo):
        retriever = MemoryRetriever(repo, "camp-1")
        results = retriever.query()
        ids = {r.memory_id for r in results}
        assert "mem-4" not in ids  # archived excluded
        assert ids == {"mem-1", "mem-2", "mem-3"}


# ---------------------------------------------------------------------------
# Slice A5: bundle memories are scene-filtered by current room + present actors
# ---------------------------------------------------------------------------

class TestSceneFilteredMemories:
    def test_bundle_memories_filtered_to_current_room_and_present_actors(self, repo):
        # Scene = room "crypt" with present PC actor-1 (mara).
        bundle = ContextBundleBuilder(
            "camp-1", "scene-1", "run_scene", ["actor-1"], 1000,
            current_room_id="crypt",
        ).build(repo)
        ids = {c["memory_id"] for c in bundle.memory_cards}
        assert "mem-2" in ids       # location:crypt — the current room
        assert "mem-1" in ids       # actor:pc:mara — a present actor
        assert "mem-3" not in ids   # untagged — out of scene

    def test_no_scene_context_returns_all_active(self, repo):
        # No room, no focus actors -> unscoped, importance-only (back-compat).
        bundle = ContextBundleBuilder(
            "camp-1", "scene-1", "run_scene", [], 1000
        ).build(repo)
        ids = {c["memory_id"] for c in bundle.memory_cards}
        assert ids == {"mem-1", "mem-2", "mem-3"}

    def test_high_importance_pin_survives_out_of_scene(self, repo):
        # BUG 2: importance>=9 "must-remember" pins are never gated by scene
        # scope — a critical campaign memory tagged to neither the room nor a
        # present actor still lands in must_remember + memory_cards.
        repo.save_memory_entry("mem-pin", "camp-1", "lore", "The Prophecy",
                               summary="Foretold.", importance=9, status="approved")
        repo.add_memory_tag("mem-pin", "thread:offscreen")  # not room/actor

        bundle = ContextBundleBuilder(
            "camp-1", "scene-1", "run_scene", ["actor-1"], 1000,
            current_room_id="crypt",
        ).build(repo)

        assert "mem-pin" in bundle.must_remember
        assert "mem-pin" in {c["memory_id"] for c in bundle.memory_cards}


# ---------------------------------------------------------------------------
# Slice A6 (T7): query_by_tag_relevance ranks by tag-hit count, then importance,
# then recency — the related-lore retrieval primitive.
# ---------------------------------------------------------------------------

class TestQueryByTagRelevance:
    def test_more_tag_hits_outrank_higher_importance(self, repo):
        # mem-two shares BOTH anchor tags (2 hits, importance 4); mem-one shares
        # only one (1 hit, importance 8). Hit count dominates importance.
        repo.save_memory_entry("mem-two", "camp-1", "lore", "Two Hits",
                               summary="s", importance=4, status="approved")
        repo.add_memory_tag("mem-two", "thread:pact")
        repo.add_memory_tag("mem-two", "theme:betrayal")
        repo.save_memory_entry("mem-one", "camp-1", "lore", "One Hit",
                               summary="s", importance=8, status="approved")
        repo.add_memory_tag("mem-one", "thread:pact")

        retriever = MemoryRetriever(repo, "camp-1")
        results = retriever.query_by_tag_relevance(["thread:pact", "theme:betrayal"])
        assert [r.memory_id for r in results] == ["mem-two", "mem-one"]

    def test_equal_hits_break_by_importance(self, repo):
        repo.save_memory_entry("mem-lo", "camp-1", "lore", "Lo",
                               summary="s", importance=3, status="approved")
        repo.add_memory_tag("mem-lo", "thread:pact")
        repo.save_memory_entry("mem-hi", "camp-1", "lore", "Hi",
                               summary="s", importance=7, status="approved")
        repo.add_memory_tag("mem-hi", "thread:pact")

        retriever = MemoryRetriever(repo, "camp-1")
        results = retriever.query_by_tag_relevance(["thread:pact"])
        assert [r.memory_id for r in results] == ["mem-hi", "mem-lo"]

    def test_empty_tags_returns_nothing(self, repo):
        retriever = MemoryRetriever(repo, "camp-1")
        assert retriever.query_by_tag_relevance([]) == []

    def test_excludes_non_approved(self, repo):
        repo.save_memory_entry("mem-arch", "camp-1", "lore", "Archived",
                               summary="s", importance=5, status="archived")
        repo.add_memory_tag("mem-arch", "thread:pact")
        retriever = MemoryRetriever(repo, "camp-1")
        assert retriever.query_by_tag_relevance(["thread:pact"]) == []


# ---------------------------------------------------------------------------
# Slice A6 (T7): the `# Related Lore` pre-fetch section on the bundle.
# ---------------------------------------------------------------------------

def _crucible_object(room_id: str, *tags: str) -> RoomObject:
    return RoomObject(
        object_id=f"obj:{room_id}:altar",
        campaign_id="camp-1",
        room_id=room_id,
        level_id="level-1",
        slug="altar",
        display_name="Blood Altar",
        archetype="lore_fixture",
        description="A slab crusted with old sacrifice.",
        current_state="idle",
        tags=list(tags),
        transitions=[],
    )


class TestRelatedLorePrefetch:
    def test_object_tag_surfaces_related_lore_scoped_query_misses(self, repo):
        # A room object carries a thematic tag; a memory shares that tag but is
        # tagged to NEITHER the room nor a present actor — so A5's scoped
        # memory_cards misses it, and T7 pre-fetch is exactly what surfaces it.
        repo.save_room_object(_crucible_object("crypt", "object:altar", "thread:pact"))
        repo.save_memory_entry("mem-lore", "camp-1", "lore", "The Old Pact",
                               summary="A bargain struck in blood.",
                               importance=5, status="approved")
        repo.add_memory_tag("mem-lore", "thread:pact")

        bundle = ContextBundleBuilder(
            "camp-1", "scene-1", "run_scene", ["actor-1"], 1000,
            current_room_id="crypt",
        ).build(repo)

        lore_ids = {c["memory_id"] for c in bundle.related_lore}
        card_ids = {c["memory_id"] for c in bundle.memory_cards}
        assert "mem-lore" in lore_ids       # T7 surfaced it via the object tag
        assert "mem-lore" not in card_ids   # A5 scoped query never had it
        assert "thread:pact" in bundle.provenance["related_lore_anchor_tags"]
        assert bundle.provenance["related_lore_retrieved"] == 1

    def test_present_npc_tag_surfaces_related_lore(self, repo):
        # A monster in the room carries a trait tag; a memory shares that trait
        # (but not the room/actor-identity anchors A5 scopes on). The in-room
        # actor is an anchor entity, so T7 must surface the memory.
        repo.save_actor("mon-1", "camp-1", "monster", "cultist", "Cultist",
                        "active", room_id="crypt")
        repo._conn.execute(
            "UPDATE actors SET tags = ? WHERE actor_id = ?",
            ['["trait:cultist"]', "mon-1"],
        )
        repo.save_memory_entry("mem-cult", "camp-1", "lore", "The Cult",
                               summary="They serve the deep.",
                               importance=5, status="approved")
        repo.add_memory_tag("mem-cult", "trait:cultist")

        bundle = ContextBundleBuilder(
            "camp-1", "scene-1", "run_scene", ["actor-1"], 1000,
            current_room_id="crypt",
        ).build(repo)

        assert "mem-cult" in {c["memory_id"] for c in bundle.related_lore}

    def test_memory_already_in_cards_not_duplicated_in_lore(self, repo):
        # mem-2 (location:crypt) is already in memory_cards. Even though the room
        # object also shares a tag with it, it must NOT be re-listed under lore.
        repo.save_room_object(_crucible_object("crypt", "object:altar", "theme:shared"))
        repo.add_memory_tag("mem-2", "theme:shared")  # mem-2 already in scope

        bundle = ContextBundleBuilder(
            "camp-1", "scene-1", "run_scene", ["actor-1"], 1000,
            current_room_id="crypt",
        ).build(repo)

        assert "mem-2" in {c["memory_id"] for c in bundle.memory_cards}
        assert "mem-2" not in {c["memory_id"] for c in bundle.related_lore}

    def test_no_current_room_yields_empty_related_lore(self, repo):
        repo.save_room_object(_crucible_object("crypt", "thread:pact"))
        repo.save_memory_entry("mem-lore", "camp-1", "lore", "The Old Pact",
                               summary="s", importance=5, status="approved")
        repo.add_memory_tag("mem-lore", "thread:pact")

        bundle = ContextBundleBuilder(
            "camp-1", "scene-1", "run_scene", ["actor-1"], 1000,
        ).build(repo)  # no current_room_id

        assert bundle.related_lore == []
        assert bundle.provenance["related_lore_retrieved"] == 0

    def test_related_lore_trimmed_to_sub_budget(self, repo):
        # Two large lore memories share the anchor tag; the ~400-token section
        # sub-budget holds only the first (higher importance), omitting the next.
        repo.save_room_object(_crucible_object("crypt", "thread:pact"))
        repo.save_memory_entry("mem-big-hi", "camp-1", "lore", "H" * 40,
                               summary="s" * 1200, importance=6, status="approved")
        repo.add_memory_tag("mem-big-hi", "thread:pact")
        repo.save_memory_entry("mem-big-lo", "camp-1", "lore", "L" * 40,
                               summary="s" * 1200, importance=4, status="approved")
        repo.add_memory_tag("mem-big-lo", "thread:pact")

        bundle = ContextBundleBuilder(
            "camp-1", "scene-1", "run_scene", ["actor-1"], 1000,
            current_room_id="crypt",
        ).build(repo)

        lore_ids = [c["memory_id"] for c in bundle.related_lore]
        assert lore_ids == ["mem-big-hi"]                       # only the first fits
        assert bundle.provenance["related_lore_retrieved"] == 2
        assert bundle.provenance["related_lore_omitted"] == 1


# ---------------------------------------------------------------------------
# Bullet 3: token budget trim leaves provenance.omitted accurate
# ---------------------------------------------------------------------------

class TestTokenBudgetTrim:
    def test_provenance_omitted_count_accurate(self, repo):
        # Budget of 1 token: pinned entry (mem-1, importance=9) always kept;
        # regular entries (mem-2, mem-3) exceed budget and are omitted.
        bundle = ContextBundleBuilder("camp-1", "scene-1", "run_scene", [], 1).build(repo)
        assert bundle.provenance["retrieved"] == 3   # 3 active entries
        assert bundle.provenance["omitted"] == 2     # 2 regular entries trimmed
        assert len(bundle.memory_cards) == 1         # only pinned entry kept
