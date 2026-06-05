"""Tests for tools/seed_rpg_state.py — Phase 33 campaign seeder."""
from __future__ import annotations

from pathlib import Path

import pytest

from seed_rpg_state import SeedResult, seed_campaign


def _make_campaign_dir(tmp_path: Path, name: str = "test-campaign") -> Path:
    d = tmp_path / name
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# Slice 1 — dry-run creates no .duckdb
# ---------------------------------------------------------------------------


def test_dry_run_creates_no_duckdb(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=True)
    assert not (campaign_dir / "campaign.duckdb").exists()


def test_dry_run_returns_seed_result(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    result = seed_campaign(campaign_dir, dry_run=True)
    assert isinstance(result, SeedResult)


# ---------------------------------------------------------------------------
# Slice 2 — first apply creates expected rows
# ---------------------------------------------------------------------------


def _open_repo(campaign_dir: Path):
    from dungeon_daddy.memory.repository import MemoryRepository
    return MemoryRepository(campaign_dir / "campaign.duckdb")


def test_first_apply_creates_duckdb(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    assert (campaign_dir / "campaign.duckdb").exists()


def test_first_apply_creates_pc_actor(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    actor = repo.get_actor(f"actor:{slug}:protagonist")
    repo.close()
    assert actor is not None
    assert actor["actor_type"] == "pc"


def test_first_apply_creates_npc_actors(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    npc = repo.get_actor(f"actor:{slug}:dungeon-presence")
    monster = repo.get_actor(f"actor:{slug}:wandering-threat")
    repo.close()
    assert npc is not None and npc["actor_type"] == "dungeon"
    assert monster is not None and monster["actor_type"] == "monster"


def test_first_apply_creates_stress_tracks_for_pc(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    tracks = repo.get_actor_stress_tracks(f"actor:{slug}:protagonist")
    repo.close()
    track_keys = {t["track_key"] for t in tracks}
    assert {"body", "composure", "bonds", "weird"}.issubset(track_keys)


def test_first_apply_creates_action_ratings_for_pc(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    ratings = repo.get_actor_action_ratings(f"actor:{slug}:protagonist")
    repo.close()
    action_keys = {r["action_key"] for r in ratings}
    assert {"fight", "move", "tinker", "study", "focus", "sway", "sense", "channel", "endure"}.issubset(action_keys)


def test_first_apply_creates_clocks(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    campaign_id = f"campaign:{slug}"
    clocks = repo.get_clocks(campaign_id)
    repo.close()
    assert len(clocks) >= 2


def test_first_apply_creates_memory_entries(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    campaign_id = f"campaign:{slug}"
    memories = repo.get_memory_entries_by_campaign(campaign_id)
    repo.close()
    assert len(memories) >= 3


def test_first_apply_result_reports_created_count(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    result = seed_campaign(campaign_dir, dry_run=False)
    assert result.created > 0
    assert result.warnings == []


# ---------------------------------------------------------------------------
# Slice 3 — second apply is idempotent (no duplicates)
# ---------------------------------------------------------------------------


def test_second_apply_creates_no_new_rows(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    result2 = seed_campaign(campaign_dir, dry_run=False)
    assert result2.created == 0


def test_second_apply_actor_count_unchanged(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)

    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    campaign_id = f"campaign:{slug}"
    after_first = len(repo.get_clocks(campaign_id))
    memories_first = len(repo.get_memory_entries_by_campaign(campaign_id))
    repo.close()

    seed_campaign(campaign_dir, dry_run=False)

    repo2 = _open_repo(campaign_dir)
    after_second = len(repo2.get_clocks(campaign_id))
    memories_second = len(repo2.get_memory_entries_by_campaign(campaign_id))
    repo2.close()

    assert after_second == after_first
    assert memories_second == memories_first


# ---------------------------------------------------------------------------
# Slice 4 — missing folder fails gracefully
# ---------------------------------------------------------------------------


def test_missing_folder_returns_warning(tmp_path: Path) -> None:
    result = seed_campaign(tmp_path / "nonexistent", dry_run=False)
    assert len(result.warnings) == 1
    assert "not found" in result.warnings[0]


def test_missing_folder_creates_no_files(tmp_path: Path) -> None:
    nonexistent = tmp_path / "nonexistent"
    seed_campaign(nonexistent, dry_run=False)
    assert not nonexistent.exists()
