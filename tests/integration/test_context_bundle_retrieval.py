"""Integration: ContextBundleBuilder builds from real DuckDB; retriever filters and trims."""
from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.retrieval import MemoryRetriever
from dungeon_daddy.rpg.models import FalloutRecord

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
    repo.add_memory_tag("mem-1", "actor:actor-1")
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
        results = retriever.query(tags=["actor:actor-1"])
        assert len(results) == 1
        assert results[0].memory_id == "mem-1"

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
