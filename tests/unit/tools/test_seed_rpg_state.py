"""Tests for tools/seed_rpg_state.py — Phase 33/34 campaign seeder."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from seed_rpg_state import SeedResult, seed_campaign, seed_campaign_with_pack


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


# ---------------------------------------------------------------------------
# Slice 5 — seed pack integration (34-4)
# ---------------------------------------------------------------------------

_PACK_DATA = {
    "campaign_slug": "test-campaign",
    "player_side": {
        "label": "The Party",
        "actors": [
            {
                "slug": "mara",
                "display_name": "Mara",
                "actor_type": "pc",
                "actions": {"fight": 2, "move": 1},
                "stress_tracks": ["body", "composure"],
            }
        ],
    },
    "dungeon_side": {
        "actors": [
            {
                "slug": "bone-warden",
                "display_name": "The Bone Warden",
                "actor_type": "monster",
            }
        ]
    },
    "clocks": [
        {
            "slug": "bone-warden-stirs",
            "label": "The Bone Warden Stirs",
            "segments": 6,
            "category": "danger",
        }
    ],
    "memories": [
        {
            "title": "The Expedition's Purpose",
            "summary": "The party seeks the Shattered Seal.",
            "type": "campaign_premise",
            "importance": 8,
            "tags": ["thread:main-quest"],
        }
    ],
    "room_threats": [],
}


def _write_pack(tmp_path: Path, data: dict | None = None) -> Path:
    pack_file = tmp_path / "rpg_seed.json"
    pack_file.write_text(json.dumps(data or _PACK_DATA), encoding="utf-8")
    return pack_file


class TestSeedCampaignWithPack:
    def test_dry_run_creates_no_duckdb(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path, dry_run=True)
        assert not (campaign_dir / "campaign.duckdb").exists()

    def test_first_apply_creates_actors(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        result = seed_campaign_with_pack(campaign_dir, pack_path)
        assert result.created > 0
        repo = _open_repo(campaign_dir)
        actors = repo.get_actors_by_campaign("campaign:test-campaign")
        repo.close()
        display_names = {a["display_name"] for a in actors}
        assert "Mara" in display_names
        assert "The Bone Warden" in display_names

    def test_first_apply_creates_clock(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)
        repo = _open_repo(campaign_dir)
        clocks = repo.get_clocks("campaign:test-campaign")
        repo.close()
        labels = {c["label"] for c in clocks}
        assert "The Bone Warden Stirs" in labels

    def test_first_apply_creates_memory_with_tag(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)
        repo = _open_repo(campaign_dir)
        entries = repo.get_memory_entries_by_campaign("campaign:test-campaign")
        repo.close()
        assert any(e["title"] == "The Expedition's Purpose" for e in entries)

    def test_second_apply_without_force_skips_existing(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)
        result2 = seed_campaign_with_pack(campaign_dir, pack_path, force=False)
        assert result2.created == 0
        assert result2.skipped > 0

    def test_second_apply_with_force_updates_existing(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)
        result2 = seed_campaign_with_pack(campaign_dir, pack_path, force=True)
        assert result2.updated > 0

    def test_missing_folder_returns_warning(self, tmp_path: Path) -> None:
        pack_path = _write_pack(tmp_path)
        result = seed_campaign_with_pack(tmp_path / "nonexistent", pack_path)
        assert len(result.warnings) == 1

    def test_result_is_seed_result(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        result = seed_campaign_with_pack(campaign_dir, pack_path, dry_run=True)
        assert isinstance(result, SeedResult)
