"""Phase 32 step 32-3 — repair tools integration tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from tests.fixtures.phase32_campaign import (
    CAMPAIGN_ID,
    MEM_SABLE_PACT_ID,
    SABLE_ID,
    seed_campaign,
)

import validate_campaign as vc_mod
import export_campaign as ec_mod
import import_campaign_fixture as icf_mod

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent / "dungeon_daddy" / "data" / "migrations"
)


@pytest.fixture
def repo(tmp_path: Path):
    db = tmp_path / "test.duckdb"
    r = MemoryRepository(db)
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


# ── Tracer bullet 1 ─────────────────────────────────────────────────────────

def test_validate_campaign_clean_fixture_has_no_drift(repo, tmp_path):
    seed_campaign(repo)
    memory_root = tmp_path / "rpg-memory"
    memory_root.mkdir()

    issues = vc_mod.validate_campaign(repo, memory_root)

    assert issues == []


# ── Tracer bullet 2 ─────────────────────────────────────────────────────────

def test_validate_campaign_missing_md_file_reported(repo, tmp_path):
    ids = seed_campaign(repo)
    memory_root = tmp_path / "rpg-memory"
    memory_root.mkdir()

    # Point one entry at a file that does not exist
    md_path = memory_root / "events" / "sable-pact.md"
    repo.update_memory_checksum(ids.mem_sable_pact_id, "abc123", str(md_path))

    issues = vc_mod.validate_campaign(repo, memory_root)

    assert len(issues) == 1
    assert issues[0].memory_id == ids.mem_sable_pact_id
    assert issues[0].kind == "missing_file"


# ── Tracer bullet 3 ─────────────────────────────────────────────────────────

def test_export_campaign_has_expected_keys(repo):
    ids = seed_campaign(repo)

    bundle = ec_mod.export_campaign(repo, ids.campaign_id)

    expected = {"campaign", "actors", "clocks", "fallout", "memory_entries", "scenes"}
    assert expected.issubset(bundle.keys())


# ── Tracer bullet 4 ─────────────────────────────────────────────────────────

def test_import_campaign_fixture_round_trips(tmp_path):
    src_db = tmp_path / "source.duckdb"
    src = MemoryRepository(src_db)
    src.initialize_schema(MIGRATIONS_DIR)
    ids = seed_campaign(src)

    bundle = ec_mod.export_campaign(src, ids.campaign_id)
    src.close()

    tgt_db = tmp_path / "target.duckdb"
    tgt = MemoryRepository(tgt_db)
    tgt.initialize_schema(MIGRATIONS_DIR)
    icf_mod.import_campaign_fixture(tgt, bundle)

    campaign = tgt.get_campaign(ids.campaign_id)
    assert campaign is not None
    assert campaign["slug"] == "iron-vault-32"

    entries = tgt.get_memory_entries_by_campaign(ids.campaign_id)
    assert len(entries) == 5

    sable = tgt.get_actor(ids.sable_id)
    assert sable is not None
    assert sable["display_name"] == "Sable"

    tgt.close()
