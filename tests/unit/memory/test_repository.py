import json
from pathlib import Path

import pytest

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository, MigrationRunner

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


# ---------------------------------------------------------------------------
# MigrationRunner
# ---------------------------------------------------------------------------


class TestMigrationRunner:
    def test_sql_files_returns_sorted_list(self, tmp_path: Path) -> None:
        (tmp_path / "002_b.sql").write_text("SELECT 1;")
        (tmp_path / "001_a.sql").write_text("SELECT 1;")
        runner = MigrationRunner(migrations_dir=tmp_path, db_path=tmp_path / "test.duckdb")
        files = runner.sql_files()
        assert [f.name for f in files] == ["001_a.sql", "002_b.sql"]

    def test_run_creates_schema_migration_table(self, tmp_path: Path) -> None:
        (tmp_path / "001_init.sql").write_text("CREATE TABLE IF NOT EXISTS foo (id TEXT);")
        db_path = tmp_path / "test.duckdb"
        runner = MigrationRunner(migrations_dir=tmp_path, db_path=db_path)
        runner.run()
        import duckdb
        conn = duckdb.connect(str(db_path))
        rows = conn.execute("SELECT name FROM schema_migration").fetchall()
        conn.close()
        assert rows == [("001_init.sql",)]

    def test_run_applies_migration_once(self, tmp_path: Path) -> None:
        (tmp_path / "001_init.sql").write_text("CREATE TABLE IF NOT EXISTS foo (id TEXT);")
        db_path = tmp_path / "test.duckdb"
        runner = MigrationRunner(migrations_dir=tmp_path, db_path=db_path)
        applied = runner.run()
        assert applied == ["001_init.sql"]

    def test_run_is_idempotent(self, tmp_path: Path) -> None:
        (tmp_path / "001_init.sql").write_text("CREATE TABLE IF NOT EXISTS foo (id TEXT);")
        db_path = tmp_path / "test.duckdb"
        runner = MigrationRunner(migrations_dir=tmp_path, db_path=db_path)
        runner.run()
        applied_second = runner.run()
        assert applied_second == []
        import duckdb
        conn = duckdb.connect(str(db_path))
        count = conn.execute("SELECT count(*) FROM schema_migration").fetchone()[0]
        conn.close()
        assert count == 1


# ---------------------------------------------------------------------------
# MemoryRepository
# ---------------------------------------------------------------------------


class TestMemoryRepository:
    def test_health_check_returns_true(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        assert repo.health_check() is True
        repo.close()

    def test_initialize_schema_creates_all_tables(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        tables = repo.list_tables()
        assert "domain_events" in tables
        assert "memory_entries" in tables
        assert "actors" in tables
        repo.close()

    def test_insert_domain_event_writes_row(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        event = DomainEvent(
            event_id="evt_001",
            campaign_id="camp_test",
            event_type="action.resolved",
            payload={"actor": "pc_mara"},
        )
        repo.insert_domain_event(event)
        events = repo.get_domain_events("camp_test")
        assert len(events) == 1
        assert events[0].event_id == "evt_001"
        assert events[0].payload["actor"] == "pc_mara"
        repo.close()

    def test_get_domain_events_filters_by_campaign(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        repo.insert_domain_event(
            DomainEvent(event_id="e1", campaign_id="camp_a", event_type="scene.started")
        )
        repo.insert_domain_event(
            DomainEvent(event_id="e2", campaign_id="camp_b", event_type="scene.started")
        )
        events_a = repo.get_domain_events("camp_a")
        assert len(events_a) == 1
        assert events_a[0].event_id == "e1"
        repo.close()

    def test_list_migrations_returns_applied_names(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        migrations = repo.list_migrations()
        assert "001_rpg_memory_foundation.sql" in migrations
        repo.close()

    def test_close_makes_health_check_false(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.close()
        assert repo.health_check() is False

    def test_get_actors_by_campaign_returns_matching_actors(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        repo.save_actor("a1", "camp-A", "pc", "hero", "Elara", "active")
        repo.save_actor("a2", "camp-A", "npc", "merchant", "Old Tom", "active")
        repo.save_actor("a3", "camp-B", "pc", "rogue", "Silas", "active")
        actors = repo.get_actors_by_campaign("camp-A")
        assert len(actors) == 2
        ids = {a["actor_id"] for a in actors}
        assert ids == {"a1", "a2"}
        repo.close()

    def test_get_actors_by_campaign_returns_empty_for_unknown_campaign(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        assert repo.get_actors_by_campaign("nonexistent") == []
        repo.close()

    def test_campaigns_table_has_dungeon_slug_column(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        import duckdb
        conn = duckdb.connect(str(tmp_path / "test.duckdb"))
        cols = [row[1] for row in conn.execute("PRAGMA table_info('campaigns')").fetchall()]
        conn.close()
        repo.close()
        assert "dungeon_slug" in cols
