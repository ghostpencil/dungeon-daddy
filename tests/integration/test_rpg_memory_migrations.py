"""Integration tests: migration runner applies SQL once, idempotent, tables present."""
from pathlib import Path

import duckdb

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.memory.repository import MemoryRepository, MigrationRunner

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent / "dungeon_daddy" / "data" / "migrations"
)

EXPECTED_TABLES = {
    "schema_migration",
    "campaigns",
    "sessions",
    "scenes",
    "actors",
    "action_ratings",
    "stress_tracks",
    "abilities",
    "clocks",
    "action_resolutions",
    "fallout",
    "memory_entries",
    "memory_tags",
    "memory_links",
    "domain_events",
    "room_objects",
    "object_transitions",
    "object_reaction_bindings",
    "room_exits",
}


class TestMigrationRunnerIntegration:
    def test_applies_migration_once(self, tmp_path: Path) -> None:
        db_path = tmp_path / "dungeon.duckdb"
        runner = MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path)
        applied = runner.run()
        assert "001_rpg_memory_foundation.sql" in applied

    def test_schema_migration_row_count_matches_files(self, tmp_path: Path) -> None:
        db_path = tmp_path / "dungeon.duckdb"
        runner = MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path)
        runner.run()
        conn = duckdb.connect(str(db_path))
        count = conn.execute("SELECT count(*) FROM schema_migration").fetchone()[0]
        conn.close()
        assert count == len(list(MIGRATIONS_DIR.glob("*.sql")))

    def test_run_twice_is_idempotent(self, tmp_path: Path) -> None:
        db_path = tmp_path / "dungeon.duckdb"
        runner = MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path)
        runner.run()
        applied_second = runner.run()
        assert applied_second == []
        conn = duckdb.connect(str(db_path))
        count = conn.execute("SELECT count(*) FROM schema_migration").fetchone()[0]
        conn.close()
        assert count == len(list(MIGRATIONS_DIR.glob("*.sql")))

    def test_all_expected_tables_exist_after_migration(self, tmp_path: Path) -> None:
        db_path = tmp_path / "dungeon.duckdb"
        runner = MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path)
        runner.run()
        conn = duckdb.connect(str(db_path))
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        conn.close()
        tables = {row[0] for row in rows}
        assert EXPECTED_TABLES <= tables

    def test_room_objects_has_reaction_policy_column(self, tmp_path: Path) -> None:
        db_path = tmp_path / "dungeon.duckdb"
        runner = MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path)
        runner.run()
        conn = duckdb.connect(str(db_path))
        cols = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'room_objects'"
            ).fetchall()
        }
        conn.close()
        assert "reaction_policy" in cols

    def test_019_applies_on_018_head_db(self, tmp_path: Path) -> None:
        """A DB migrated through 018 then to 019: old rows default to 'ambient'."""
        db_path = tmp_path / "dungeon.duckdb"
        # Build an 018-head DB from a migrations dir holding only 001..018.
        head_dir = tmp_path / "migrations_018"
        head_dir.mkdir()
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if sql_file.name < "019":
                (head_dir / sql_file.name).write_text(
                    sql_file.read_text(encoding="utf-8"), encoding="utf-8"
                )
        MigrationRunner(migrations_dir=head_dir, db_path=db_path).run()
        # Insert a room object with the pre-019 schema (no reaction_policy column).
        conn = duckdb.connect(str(db_path))
        conn.execute(
            """
            INSERT INTO room_objects (
                object_id, campaign_id, room_id, level_id, slug,
                display_name, archetype, description, current_state
            )
            VALUES ('obj:old', 'camp:old', 'room:old', 'level:old', 'old-statue',
                    'Old Statue', 'lore_fixture', 'A weathered statue.', 'intact')
            """
        )
        conn.close()
        # Now migrate to 019 (full dir) on the same DB.
        applied = MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path).run()
        assert "019_reaction_policy.sql" in applied
        conn = duckdb.connect(str(db_path))
        policy = conn.execute(
            "SELECT reaction_policy FROM room_objects WHERE object_id = 'obj:old'"
        ).fetchone()[0]
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        }
        conn.close()
        assert policy == "ambient"
        assert "object_reaction_bindings" in tables

    def test_items_table_has_room_id_column(self, tmp_path: Path) -> None:
        db_path = tmp_path / "dungeon.duckdb"
        runner = MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path)
        runner.run()
        conn = duckdb.connect(str(db_path))
        cols = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'items'"
            ).fetchall()
        }
        conn.close()
        assert "room_id" in cols


class TestMemoryRepositoryIntegration:
    def test_domain_event_round_trip(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "dungeon.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        event = DomainEvent(
            event_id="evt_int_001",
            campaign_id="camp_int",
            event_type="action.resolved",
            payload={"actor_id": "pc_mara", "outcome": "full"},
        )
        repo.insert_domain_event(event)
        results = repo.get_domain_events("camp_int")
        assert len(results) == 1
        assert results[0].event_id == "evt_int_001"
        assert results[0].payload["outcome"] == "full"
        repo.close()

    def test_list_migrations_after_init(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "dungeon.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        migrations = repo.list_migrations()
        assert "001_rpg_memory_foundation.sql" in migrations
        assert "002_dungeon_slug.sql" in migrations
        repo.close()

    def test_no_existing_play_mode_tables_affected(self, tmp_path: Path) -> None:
        """Migration should not create or alter any dungeon design tables."""
        repo = MemoryRepository(db_path=tmp_path / "dungeon.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        tables = set(repo.list_tables())
        # Dungeon design tables live in the main DungeonRepository (SQLite-based JSON),
        # not in this DuckDB. Confirm none of the legacy table names are present here.
        legacy_names = {"dungeons", "rooms", "connections", "levels"}
        assert tables.isdisjoint(legacy_names)
        repo.close()
