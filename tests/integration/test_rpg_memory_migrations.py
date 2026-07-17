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
    "rooms",
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

    def test_tags_columns_present_on_all_three_tables(self, tmp_path: Path) -> None:
        """Migration 020 adds a `tags` column to room_objects, items, objectives."""
        db_path = tmp_path / "dungeon.duckdb"
        MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path).run()
        conn = duckdb.connect(str(db_path))
        for table in ("room_objects", "items", "objectives"):
            cols = {
                row[0]
                for row in conn.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = ?",
                    [table],
                ).fetchall()
            }
            assert "tags" in cols, f"{table} missing tags column"
        conn.close()

    def test_020_applies_on_019_head_db(self, tmp_path: Path) -> None:
        """A DB migrated through 019 then to 020: old rows default to '[]'."""
        db_path = tmp_path / "dungeon.duckdb"
        head_dir = tmp_path / "migrations_019"
        head_dir.mkdir()
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if sql_file.name < "020":
                (head_dir / sql_file.name).write_text(
                    sql_file.read_text(encoding="utf-8"), encoding="utf-8"
                )
        MigrationRunner(migrations_dir=head_dir, db_path=db_path).run()
        # Insert a pre-020 objective (no tags column).
        conn = duckdb.connect(str(db_path))
        conn.execute(
            """
            INSERT INTO objectives (
                objective_id, campaign_id, slug, title, description,
                tier_index, status, completion_kind, completion_target_slug,
                completion_required_state, advances_clock_slug
            )
            VALUES ('obj:old', 'camp:old', 'old-goal', 'Old Goal', 'A pre-020 goal.',
                    0, 'active', 'object_state', 'coolant-loop', 'restored', NULL)
            """
        )
        conn.close()
        applied = MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path).run()
        assert "020_tag_taxonomy.sql" in applied
        conn = duckdb.connect(str(db_path))
        tags = conn.execute(
            "SELECT tags FROM objectives WHERE objective_id = 'obj:old'"
        ).fetchone()[0]
        conn.close()
        assert tags == "[]"
        # Back-compat read through the models/repo: the legacy row loads with an
        # empty tags list, no crash (spec/TESTING.md Migration Tests §3).
        repo = MemoryRepository(db_path)
        repo.initialize_schema(MIGRATIONS_DIR)
        try:
            loaded = repo.get_objectives("camp:old")
        finally:
            repo.close()
        assert [o["objective_id"] for o in loaded] == ["obj:old"]
        assert loaded[0]["tags"] == []

    def test_clocks_table_has_tags_column(self, tmp_path: Path) -> None:
        """Migration 021 adds a `tags` column to clocks."""
        db_path = tmp_path / "dungeon.duckdb"
        MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path).run()
        conn = duckdb.connect(str(db_path))
        cols = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'clocks'"
            ).fetchall()
        }
        conn.close()
        assert "tags" in cols

    def test_021_applies_on_020_head_db(self, tmp_path: Path) -> None:
        """A DB migrated through 020 then to 021: old clocks default to '[]'."""
        db_path = tmp_path / "dungeon.duckdb"
        head_dir = tmp_path / "migrations_020"
        head_dir.mkdir()
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if sql_file.name < "021":
                (head_dir / sql_file.name).write_text(
                    sql_file.read_text(encoding="utf-8"), encoding="utf-8"
                )
        MigrationRunner(migrations_dir=head_dir, db_path=db_path).run()
        # Insert a pre-021 clock (no tags column).
        conn = duckdb.connect(str(db_path))
        conn.execute(
            """
            INSERT INTO clocks (clock_id, campaign_id, label, segments, filled, status)
            VALUES ('clk:old', 'camp:old', 'Old Clock', 4, 0, 'active')
            """
        )
        conn.close()
        applied = MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path).run()
        assert "021_clock_tags.sql" in applied
        conn = duckdb.connect(str(db_path))
        tags = conn.execute(
            "SELECT tags FROM clocks WHERE clock_id = 'clk:old'"
        ).fetchone()[0]
        conn.close()
        assert tags == "[]"
        # Back-compat read through the repo: the legacy clock loads with an empty
        # tags list, no crash (spec/TESTING.md Migration Tests §3).
        repo = MemoryRepository(db_path)
        repo.initialize_schema(MIGRATIONS_DIR)
        try:
            clocks = repo.get_clocks("camp:old")
        finally:
            repo.close()
        assert [c["clock_id"] for c in clocks] == ["clk:old"]
        assert clocks[0]["tags"] == []

    def test_rooms_table_present_with_expected_columns(self, tmp_path: Path) -> None:
        """Migration 022 adds a first-class `rooms` table (Slice B0, spec §7.1)."""
        db_path = tmp_path / "dungeon.duckdb"
        MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path).run()
        conn = duckdb.connect(str(db_path))
        cols = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'rooms'"
            ).fetchall()
        }
        conn.close()
        assert {
            "room_id", "campaign_id", "level_id", "slug", "display_name",
            "room_type", "summary", "quest_role", "markdown_path", "checksum", "tags",
        } <= cols

    def test_022_applies_on_021_head_db(self, tmp_path: Path) -> None:
        """A DB migrated through 021 then to 022 gains the rooms table cleanly."""
        db_path = tmp_path / "dungeon.duckdb"
        head_dir = tmp_path / "migrations_021"
        head_dir.mkdir()
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if sql_file.name < "022":
                (head_dir / sql_file.name).write_text(
                    sql_file.read_text(encoding="utf-8"), encoding="utf-8"
                )
        MigrationRunner(migrations_dir=head_dir, db_path=db_path).run()
        conn = duckdb.connect(str(db_path))
        tables_before = {
            row[0]
            for row in conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        }
        conn.close()
        assert "rooms" not in tables_before
        applied = MigrationRunner(migrations_dir=MIGRATIONS_DIR, db_path=db_path).run()
        assert "022_rooms.sql" in applied
        # Back-compat read through the repo: a freshly-migrated DB has an empty
        # rooms table that loads with no crash (spec/TESTING.md Migration Tests §3).
        repo = MemoryRepository(db_path)
        repo.initialize_schema(MIGRATIONS_DIR)
        try:
            assert repo.get_rooms("camp:none") == []
        finally:
            repo.close()

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
        """Migration should not create or alter any dungeon *design* tables.

        The dungeon *layout* (geometry, level structure, the visual connection
        graph) lives in the main DungeonRepository (JSON), not this DuckDB. Note
        that as of Slice B0 the campaign DB DOES hold a `rooms` table — a
        campaign-runtime projection of each room (searchable/taggable/lore), which
        is deliberately distinct from the design-side layout (spec §7.1). So
        `rooms` is no longer a forbidden name; `dungeons`/`connections`/`levels`
        remain design-only.
        """
        repo = MemoryRepository(db_path=tmp_path / "dungeon.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        tables = set(repo.list_tables())
        design_only_names = {"dungeons", "connections", "levels"}
        assert tables.isdisjoint(design_only_names)
        repo.close()
