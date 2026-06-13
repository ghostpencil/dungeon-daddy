from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import FactionState

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


class TestFactionMigration:
    def test_migration_creates_factions_table(self, repo: MemoryRepository) -> None:
        assert "factions" in repo.list_tables()


class TestSaveFaction:
    def test_save_faction_inserts(self, repo: MemoryRepository) -> None:
        faction = FactionState(
            faction_id="fac-001",
            campaign_id="camp-1",
            slug="ossuary-cult",
            display_name="The Ossuary Cult",
        )
        repo.save_faction(faction)
        results = repo.get_factions("camp-1")
        assert len(results) == 1
        assert results[0]["slug"] == "ossuary-cult"

    def test_save_faction_is_idempotent(self, repo: MemoryRepository) -> None:
        faction = FactionState(
            faction_id="fac-001",
            campaign_id="camp-1",
            slug="ossuary-cult",
            display_name="The Ossuary Cult",
        )
        repo.save_faction(faction)
        repo.save_faction(faction)
        results = repo.get_factions("camp-1")
        assert len(results) == 1


class TestGetFactions:
    def test_get_factions_scoped_by_campaign(self, repo: MemoryRepository) -> None:
        f1 = FactionState(faction_id="f1", campaign_id="camp-A", slug="cult", display_name="Cult")
        f2 = FactionState(faction_id="f2", campaign_id="camp-B", slug="guild", display_name="Guild")
        repo.save_faction(f1)
        repo.save_faction(f2)
        results = repo.get_factions("camp-A")
        assert len(results) == 1
        assert results[0]["faction_id"] == "f1"


class TestUpdateFactionReputation:
    def test_steps_forward_through_tiers(self, repo: MemoryRepository) -> None:
        faction = FactionState(
            faction_id="f1", campaign_id="c1", slug="cult", display_name="Cult",
            reputation="cold",
        )
        repo.save_faction(faction)
        new_rep = repo.update_faction_reputation("f1", delta_steps=1)
        assert new_rep == "neutral"
        assert repo.get_factions("c1")[0]["reputation"] == "neutral"

    def test_clamps_at_allied(self, repo: MemoryRepository) -> None:
        faction = FactionState(
            faction_id="f1", campaign_id="c1", slug="cult", display_name="Cult",
            reputation="warm",
        )
        repo.save_faction(faction)
        new_rep = repo.update_faction_reputation("f1", delta_steps=3)
        assert new_rep == "allied"

    def test_clamps_at_hostile(self, repo: MemoryRepository) -> None:
        faction = FactionState(
            faction_id="f1", campaign_id="c1", slug="cult", display_name="Cult",
            reputation="cold",
        )
        repo.save_faction(faction)
        new_rep = repo.update_faction_reputation("f1", delta_steps=-5)
        assert new_rep == "hostile"
