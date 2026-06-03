from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import FalloutRecord

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "campaign.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    return r


def _fallout(fallout_id: str = "fo_001", actor_id: str = "pc_1") -> FalloutRecord:
    return FalloutRecord(
        fallout_id=fallout_id,
        campaign_id="camp_1",
        actor_id=actor_id,
        track_key="body",
        severity="minor",
        title="Battered",
        summary="Bruises and cuts.",
    )


def test_save_and_get_fallout_record(repo: MemoryRepository) -> None:
    fallout = _fallout()
    repo.save_fallout_record(fallout)
    results = repo.get_fallout_records("camp_1", "pc_1")
    assert len(results) == 1
    assert results[0]["fallout_id"] == "fo_001"
    assert results[0]["track_key"] == "body"
    assert results[0]["severity"] == "minor"


def test_fallout_appears_in_retrieval_by_actor(repo: MemoryRepository) -> None:
    fallout = _fallout(actor_id="pc_mara")
    repo.save_fallout_record(fallout)
    results = repo.get_fallout_records("camp_1", "pc_mara")
    assert any(r["actor_id"] == "pc_mara" for r in results)
