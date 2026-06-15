"""Tests for migrate_campaigns_to_libraries in dungeon_daddy/data/repository.py."""

import json
from pathlib import Path

import pytest


def _dirs(tmp_path: Path):
    campaigns = tmp_path / "campaigns"
    dungeons = tmp_path / "dungeons"
    seeds = tmp_path / "campaign_seeds"
    saves = tmp_path / "saves"
    for d in (campaigns, dungeons, seeds, saves):
        d.mkdir()
    return campaigns, dungeons, seeds, saves


# ---------------------------------------------------------------------------
# Behavior 1: empty campaigns dir → no-op, no error
# ---------------------------------------------------------------------------

def test_empty_campaigns_dir_is_noop(tmp_path):
    from dungeon_daddy.data.repository import migrate_campaigns_to_libraries
    campaigns, dungeons, seeds, saves = _dirs(tmp_path)
    migrate_campaigns_to_libraries(campaigns, dungeons, seeds, saves)
    assert list(dungeons.iterdir()) == []
    assert list(seeds.iterdir()) == []
    assert list(saves.iterdir()) == []


# ---------------------------------------------------------------------------
# Behavior 2: dungeon.json → copied to dungeons/<name>/ AND saves/<name>/
# ---------------------------------------------------------------------------

def test_dungeon_json_copied_to_dungeons_and_saves(tmp_path):
    from dungeon_daddy.data.repository import migrate_campaigns_to_libraries
    campaigns, dungeons, seeds, saves = _dirs(tmp_path)
    (campaigns / "my-dungeon").mkdir()
    (campaigns / "my-dungeon" / "dungeon.json").write_text('{"title": "X"}')

    migrate_campaigns_to_libraries(campaigns, dungeons, seeds, saves)

    assert (dungeons / "my-dungeon" / "dungeon.json").read_text() == '{"title": "X"}'
    assert (saves / "my-dungeon" / "dungeon.json").read_text() == '{"title": "X"}'


# ---------------------------------------------------------------------------
# Behavior 3: context docs → dungeons/ only; full folder → saves/
# ---------------------------------------------------------------------------

def test_context_docs_and_full_save_copy(tmp_path):
    from dungeon_daddy.data.repository import migrate_campaigns_to_libraries
    campaigns, dungeons, seeds, saves = _dirs(tmp_path)
    src = campaigns / "the-crucible"
    src.mkdir()
    (src / "dungeon.json").write_text("{}")
    (src / "setting.md").write_text("setting")
    (src / "party.md").write_text("party")
    (src / "level_1_design.md").write_text("level1")
    (src / "campaign.duckdb").write_bytes(b"\x00db")
    (src / "session.json").write_text("{}")
    (src / "memory").mkdir()
    (src / "memory" / "level_1.md").write_text("mem")

    migrate_campaigns_to_libraries(campaigns, dungeons, seeds, saves)

    # context docs in dungeons/
    d = dungeons / "the-crucible"
    assert (d / "dungeon.json").exists()
    assert (d / "setting.md").read_text() == "setting"
    assert (d / "party.md").read_text() == "party"
    assert (d / "level_1_design.md").read_text() == "level1"
    assert not (d / "campaign.duckdb").exists()  # live-state NOT in dungeons/

    # full folder in saves/
    s = saves / "the-crucible"
    assert (s / "dungeon.json").exists()
    assert (s / "campaign.duckdb").read_bytes() == b"\x00db"
    assert (s / "session.json").exists()
    assert (s / "memory" / "level_1.md").read_text() == "mem"


# ---------------------------------------------------------------------------
# Behavior 4: campaign.json present → copied to campaign_seeds/<name>/
# ---------------------------------------------------------------------------

def test_manifest_copied_to_seeds(tmp_path):
    from dungeon_daddy.data.repository import migrate_campaigns_to_libraries
    campaigns, dungeons, seeds, saves = _dirs(tmp_path)
    src = campaigns / "bone-cathedral"
    src.mkdir()
    (src / "dungeon.json").write_text("{}")
    manifest = '{"slug": "bone-cathedral", "title": "Bone Cathedral"}'
    (src / "campaign.json").write_text(manifest)

    migrate_campaigns_to_libraries(campaigns, dungeons, seeds, saves)

    seed_file = seeds / "bone-cathedral" / "campaign.json"
    assert seed_file.exists()
    assert seed_file.read_text() == manifest


def test_no_manifest_no_seed_entry(tmp_path):
    from dungeon_daddy.data.repository import migrate_campaigns_to_libraries
    campaigns, dungeons, seeds, saves = _dirs(tmp_path)
    src = campaigns / "no-manifest"
    src.mkdir()
    (src / "dungeon.json").write_text("{}")

    migrate_campaigns_to_libraries(campaigns, dungeons, seeds, saves)

    assert not (seeds / "no-manifest").exists()


# ---------------------------------------------------------------------------
# Behavior 5: completion marked; second run is a no-op
# ---------------------------------------------------------------------------

def test_source_renamed_after_migration(tmp_path):
    from dungeon_daddy.data.repository import migrate_campaigns_to_libraries
    campaigns, dungeons, seeds, saves = _dirs(tmp_path)
    src = campaigns / "my-dungeon"
    src.mkdir()
    (src / "dungeon.json").write_text("{}")

    migrate_campaigns_to_libraries(campaigns, dungeons, seeds, saves)

    assert not src.exists()
    assert (tmp_path / "campaigns.migrated" / "my-dungeon").is_dir()


def test_second_run_is_noop(tmp_path):
    from dungeon_daddy.data.repository import migrate_campaigns_to_libraries
    campaigns, dungeons, seeds, saves = _dirs(tmp_path)
    src = campaigns / "my-dungeon"
    src.mkdir()
    (src / "dungeon.json").write_text("{}")

    migrate_campaigns_to_libraries(campaigns, dungeons, seeds, saves)
    # second run must not raise and must not change anything
    migrate_campaigns_to_libraries(campaigns, dungeons, seeds, saves)

    assert (dungeons / "my-dungeon" / "dungeon.json").exists()
    assert (saves / "my-dungeon" / "dungeon.json").exists()


# ---------------------------------------------------------------------------
# Behavior 6: multiple campaigns migrated independently
# ---------------------------------------------------------------------------

def test_multiple_campaigns_all_migrated(tmp_path):
    from dungeon_daddy.data.repository import migrate_campaigns_to_libraries
    campaigns, dungeons, seeds, saves = _dirs(tmp_path)
    for name in ("alpha", "beta", "gamma"):
        (campaigns / name).mkdir()
        (campaigns / name / "dungeon.json").write_text(f'{{"title": "{name}"}}')

    migrate_campaigns_to_libraries(campaigns, dungeons, seeds, saves)

    for name in ("alpha", "beta", "gamma"):
        assert (dungeons / name / "dungeon.json").exists()
        assert (saves / name / "dungeon.json").exists()
    # all three moved to campaigns.migrated/
    migrated = tmp_path / "campaigns.migrated"
    assert {p.name for p in migrated.iterdir()} == {"alpha", "beta", "gamma"}
