"""Phase 32 step 32-2 — golden context bundle snapshots.

Verifies that ContextBundleBuilder produces correct, deterministic output
against the Phase 32 golden fixture.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.repository import MemoryRepository
from tests.fixtures.phase32_campaign import (
    CAMPAIGN_ID,
    FALLOUT_PHYSICAL_ID,
    FALLOUT_WEIRD_ID,
    MEM_SABLE_PACT_ID,
    SABLE_ID,
    SCENE_COMBAT_ID,
    seed_campaign,
)

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent / "dungeon_daddy" / "data" / "migrations"
)


@pytest.fixture
def repo(tmp_path: Path):
    db = MemoryRepository(tmp_path / "campaign.duckdb")
    db.initialize_schema(MIGRATIONS_DIR)
    seed_campaign(db)
    yield db
    db.close()


def _build(repo, token_budget: int = 10_000):
    return ContextBundleBuilder(
        CAMPAIGN_ID, SCENE_COMBAT_ID, "run_scene", [SABLE_ID], token_budget
    ).build(repo)


# ---------------------------------------------------------------------------
# Bullet 1: build() returns a valid ContextBundle for the combat scene
# ---------------------------------------------------------------------------

class TestBundleBuild:
    def test_build_returns_bundle_with_correct_ids(self, repo):
        bundle = _build(repo)
        assert bundle.campaign_id == CAMPAIGN_ID
        assert bundle.scene_id == SCENE_COMBAT_ID
        assert bundle.bundle_id  # non-empty UUID


# ---------------------------------------------------------------------------
# Bullet 2: memory_cards order is stable across two builds (same seed)
# ---------------------------------------------------------------------------

class TestMemoryCardsOrder:
    def test_memory_cards_order_is_deterministic(self, repo):
        bundle_a = _build(repo)
        bundle_b = _build(repo)
        ids_a = [c["memory_id"] for c in bundle_a.memory_cards]
        ids_b = [c["memory_id"] for c in bundle_b.memory_cards]
        assert ids_a == ids_b


# ---------------------------------------------------------------------------
# Bullet 3: must_remember pins the importance ≥ 9 entry regardless of budget
# ---------------------------------------------------------------------------

class TestMustRemember:
    def test_must_remember_contains_high_importance_entry_with_tiny_budget(self, repo):
        bundle = _build(repo, token_budget=1)
        assert MEM_SABLE_PACT_ID in bundle.must_remember


# ---------------------------------------------------------------------------
# Bullet 4: provenance.retrieved + provenance.omitted == total active entries
# ---------------------------------------------------------------------------

class TestProvenanceAccounting:
    def test_retrieved_plus_omitted_equals_total_active(self, repo):
        # Golden fixture has 5 active memory entries; ample budget omits none.
        bundle = _build(repo)
        assert bundle.provenance["omitted"] == 0
        assert bundle.provenance["retrieved"] + bundle.provenance["omitted"] == 5


# ---------------------------------------------------------------------------
# Bullet 5: scene_brief.location_slug matches the seeded combat scene
# ---------------------------------------------------------------------------

class TestSceneBrief:
    def test_scene_brief_location_slug_matches_combat_scene(self, repo):
        bundle = _build(repo)
        assert bundle.scene_brief["location_slug"] == "forge-floor"


# ---------------------------------------------------------------------------
# Bullet 6: mechanical_state contains Sable's action ratings and stress tracks
# ---------------------------------------------------------------------------

class TestMechanicalState:
    def test_mechanical_state_has_sable_action_ratings(self, repo):
        bundle = _build(repo)
        ratings = bundle.mechanical_state[SABLE_ID]["action_ratings"]
        rating_map = {r["action_key"]: r["rating"] for r in ratings}
        assert rating_map["skirmish"] == 2
        assert rating_map["prowl"] == 3

    def test_mechanical_state_has_sable_stress_tracks(self, repo):
        bundle = _build(repo)
        tracks = bundle.mechanical_state[SABLE_ID]["stress_tracks"]
        track_map = {t["track_key"]: t for t in tracks}
        assert track_map["weird"]["filled"] == 4
        assert track_map["body"]["filled"] == 3


# ---------------------------------------------------------------------------
# Bullet 7: active_fallout lists both fallout records for Sable
# ---------------------------------------------------------------------------

class TestActiveFallout:
    def test_active_fallout_contains_both_sable_records(self, repo):
        bundle = _build(repo)
        fallout_ids = {f["fallout_id"] for f in bundle.active_fallout}
        assert FALLOUT_PHYSICAL_ID in fallout_ids
        assert FALLOUT_WEIRD_ID in fallout_ids
        assert len(bundle.active_fallout) == 2
