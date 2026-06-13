"""Unit tests for Phase 40.4 — campaign export."""
from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository

_MIGRATIONS = Path(__file__).parent.parent.parent.parent / "dungeon_daddy" / "data" / "migrations"


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    db = tmp_path / "test.duckdb"
    r = MemoryRepository(db)
    r.initialize_schema(_MIGRATIONS)
    r.save_campaign("campaign:test", "test", "Test Campaign", dungeon_slug="test-dungeon")
    yield r
    r.close()


# ---------------------------------------------------------------------------
# Slice 1 — export empty campaign returns manifest with slug/title
# ---------------------------------------------------------------------------

def test_export_empty_campaign_returns_manifest_with_slug_and_title(repo: MemoryRepository) -> None:
    from dungeon_daddy.campaign.exporter import export_campaign_manifest

    manifest = export_campaign_manifest("campaign:test", repo)

    assert manifest.slug == "test"
    assert manifest.title == "Test Campaign"
    assert manifest.dungeon_slug == "test-dungeon"
    assert manifest.world_actors == []
    assert manifest.clocks == []
    assert manifest.memory_seeds == []


# ---------------------------------------------------------------------------
# Slice 2 — export actors
# ---------------------------------------------------------------------------

def test_export_campaign_includes_actors(repo: MemoryRepository) -> None:
    from dungeon_daddy.campaign.exporter import export_campaign_manifest

    repo.save_actor("actor:test:hero", "campaign:test", "pc", "hero", "Hero", "active")
    repo.save_actor("actor:test:warden", "campaign:test", "dungeon", "warden", "The Warden", "active")

    manifest = export_campaign_manifest("campaign:test", repo)

    slugs = {a.slug for a in manifest.world_actors}
    assert "hero" in slugs
    assert "warden" in slugs
    hero = next(a for a in manifest.world_actors if a.slug == "hero")
    assert hero.display_name == "Hero"
    assert hero.actor_type == "pc"
    assert hero.status == "active"


# ---------------------------------------------------------------------------
# Slice 3 — export actor action ratings
# ---------------------------------------------------------------------------

def test_export_campaign_includes_actor_action_ratings(repo: MemoryRepository) -> None:
    from dungeon_daddy.campaign.exporter import export_campaign_manifest

    repo.save_actor("actor:test:hero", "campaign:test", "pc", "hero", "Hero")
    repo.save_actor_action_rating("actor:test:hero", "fight", 2)
    repo.save_actor_action_rating("actor:test:hero", "study", 1)

    manifest = export_campaign_manifest("campaign:test", repo)

    hero = next(a for a in manifest.world_actors if a.slug == "hero")
    assert hero.action_ratings == {"fight": 2, "study": 1}


# ---------------------------------------------------------------------------
# Slice 4 — export actor stress tracks
# ---------------------------------------------------------------------------

def test_export_campaign_includes_actor_stress_tracks(repo: MemoryRepository) -> None:
    from dungeon_daddy.campaign.exporter import export_campaign_manifest

    repo.save_actor("actor:test:hero", "campaign:test", "pc", "hero", "Hero")
    repo.save_actor_stress_track("actor:test:hero", "body", capacity=6, filled=2)
    repo.save_actor_stress_track("actor:test:hero", "composure", capacity=4, filled=0)

    manifest = export_campaign_manifest("campaign:test", repo)

    hero = next(a for a in manifest.world_actors if a.slug == "hero")
    track_keys = {t["track_key"] for t in hero.stress_tracks}
    assert "body" in track_keys
    assert "composure" in track_keys
    body = next(t for t in hero.stress_tracks if t["track_key"] == "body")
    assert body["capacity"] == 6
    assert body["filled"] == 2


# ---------------------------------------------------------------------------
# Slice 5 — export clocks with all fields
# ---------------------------------------------------------------------------

def test_export_campaign_includes_clocks(repo: MemoryRepository) -> None:
    from dungeon_daddy.campaign.exporter import export_campaign_manifest

    repo.save_clock(
        "clock:test:doom",
        "campaign:test",
        "Doom Clock",
        segments=6,
        filled=2,
        status="active",
        clock_level="dungeon",
        category="danger",
        scope_room_id="room-1",
        action_tags=["fight", "endure"],
        stakes="The dungeon collapses",
        completion_effect="Everyone takes body stress",
        visible_to_player=True,
    )

    manifest = export_campaign_manifest("campaign:test", repo)

    assert len(manifest.clocks) == 1
    clock = manifest.clocks[0]
    assert clock.slug == "doom"
    assert clock.label == "Doom Clock"
    assert clock.segments == 6
    assert clock.filled == 2
    assert clock.clock_level == "dungeon"
    assert clock.category == "danger"
    assert clock.scope_room_id == "room-1"
    assert clock.action_tags == ["fight", "endure"]
    assert clock.stakes == "The dungeon collapses"
    assert clock.completion_effect == "Everyone takes body stress"
    assert clock.visible_to_player is True


# ---------------------------------------------------------------------------
# Slice 6 — export approved memories only
# ---------------------------------------------------------------------------

def test_export_campaign_includes_only_approved_memories(repo: MemoryRepository) -> None:
    from dungeon_daddy.campaign.exporter import export_campaign_manifest

    repo.save_memory_entry("mem:1", "campaign:test", "event", "Approved mem", "The party arrived.", status="approved")
    repo.save_memory_entry("mem:2", "campaign:test", "event", "Draft mem", "Something happened.", status="draft")
    repo.save_memory_entry("mem:3", "campaign:test", "event", "Archived mem", "Old thing.", status="archived")

    manifest = export_campaign_manifest("campaign:test", repo)

    assert len(manifest.memory_seeds) == 1
    assert "The party arrived." in manifest.memory_seeds


# ---------------------------------------------------------------------------
# Slice 7 — player_side populated from pc-type actors
# ---------------------------------------------------------------------------

def test_export_campaign_player_side_contains_pc_slugs(repo: MemoryRepository) -> None:
    from dungeon_daddy.campaign.exporter import export_campaign_manifest

    repo.save_actor("actor:test:hero", "campaign:test", "pc", "hero", "Hero")
    repo.save_actor("actor:test:warden", "campaign:test", "dungeon", "warden", "The Warden")

    manifest = export_campaign_manifest("campaign:test", repo)

    assert "hero" in manifest.player_side
    assert "warden" not in manifest.player_side
