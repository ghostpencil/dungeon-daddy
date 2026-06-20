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

    def test_migration_006_converts_old_memory_statuses(self, tmp_path: Path) -> None:
        import duckdb
        # Apply migrations 001-005 first, then insert rows with old status values
        migrations_up_to_005 = sorted(
            p for p in MIGRATIONS_DIR.glob("*.sql")
            if p.name < "006"
        )
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))
        from dungeon_daddy.memory.repository import _apply_migrations, _ensure_migration_table
        _ensure_migration_table(conn)
        for sql_file in migrations_up_to_005:
            sql = sql_file.read_text(encoding="utf-8")
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if stmt and not stmt.startswith("--"):
                    conn.execute(stmt)
            conn.execute("INSERT INTO schema_migration (name) VALUES (?)", [sql_file.name])
        # Insert rows using old status values (bypassing Pydantic)
        conn.execute(
            "INSERT INTO memory_entries (memory_id, campaign_id, type, title, status)"
            " VALUES ('m1', 'c1', 'event', 'T1', 'active'),"
            "        ('m2', 'c1', 'event', 'T2', 'resolved'),"
            "        ('m3', 'c1', 'event', 'T3', 'archived')"
        )
        conn.close()
        # Apply migration 006
        migration_006 = MIGRATIONS_DIR / "006_memory_approval_status.sql"
        conn2 = duckdb.connect(str(db_path))
        _ensure_migration_table(conn2)
        sql = migration_006.read_text(encoding="utf-8")
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                conn2.execute(stmt)
        conn2.close()
        # Verify the conversion
        conn3 = duckdb.connect(str(db_path))
        rows = {
            r[0]: r[1]
            for r in conn3.execute(
                "SELECT memory_id, status FROM memory_entries ORDER BY memory_id"
            ).fetchall()
        }
        conn3.close()
        assert rows["m1"] == "approved"
        assert rows["m2"] == "archived"
        assert rows["m3"] == "archived"

    def test_campaigns_table_has_dungeon_slug_column(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        import duckdb
        conn = duckdb.connect(str(tmp_path / "test.duckdb"))
        cols = [row[1] for row in conn.execute("PRAGMA table_info('campaigns')").fetchall()]
        conn.close()
        repo.close()
        assert "dungeon_slug" in cols


# ---------------------------------------------------------------------------
# actor_abilities — Cycles 14–21
# ---------------------------------------------------------------------------


class TestActorAbilities:
    def test_migration_011_creates_actor_abilities_table(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        tables = repo.list_tables()
        repo.close()
        assert "actor_abilities" in tables

    def test_migration_011_adds_playbook_slug_to_actors(self, tmp_path: Path) -> None:
        import duckdb
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        repo.close()
        conn = duckdb.connect(str(tmp_path / "test.duckdb"))
        cols = [row[1] for row in conn.execute("PRAGMA table_info('actors')").fetchall()]
        conn.close()
        assert "playbook_slug" in cols

    def test_get_actor_abilities_returns_empty_when_none(self, tmp_path: Path) -> None:
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        result = repo.get_actor_abilities("actor:x:nobody")
        repo.close()
        assert result == []

    def test_save_and_get_actor_ability_roundtrip(self, tmp_path: Path) -> None:
        from dungeon_daddy.rpg.models import ActorAbility
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        ability = ActorAbility(
            actor_id="actor:campaign:hero",
            ability_slug="combat-gear",
            display_name="Combat Gear",
            description="A kit of fighting tools.",
            source="kit",
        )
        repo.save_actor_ability(ability)
        result = repo.get_actor_abilities("actor:campaign:hero")
        repo.close()
        assert len(result) == 1
        assert result[0].ability_slug == "combat-gear"
        assert result[0].display_name == "Combat Gear"
        assert result[0].source == "kit"

    def test_actor_ability_target_types_roundtrip(self, tmp_path: Path) -> None:
        from dungeon_daddy.rpg.models import ActorAbility
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        ability = ActorAbility(
            actor_id="actor:campaign:hero",
            ability_slug="strike",
            display_name="Strike",
            description="A melee attack.",
            source="playbook_start",
            surfaces_as_verb=True,
            target_types=["npc", "monster"],
        )
        repo.save_actor_ability(ability)
        result = repo.get_actor_abilities("actor:campaign:hero")
        repo.close()
        assert result[0].target_types == ["npc", "monster"]
        assert result[0].surfaces_as_verb is True

    def test_save_actor_ability_is_idempotent(self, tmp_path: Path) -> None:
        from dungeon_daddy.rpg.models import ActorAbility
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        repo.save_actor_ability(ActorAbility(
            actor_id="actor:c:hero",
            ability_slug="strike",
            display_name="Strike",
            description="First.",
            source="kit",
        ))
        repo.save_actor_ability(ActorAbility(
            actor_id="actor:c:hero",
            ability_slug="strike",
            display_name="Strike Updated",
            description="Second.",
            source="kit",
        ))
        result = repo.get_actor_abilities("actor:c:hero")
        repo.close()
        assert len(result) == 1
        assert result[0].display_name == "Strike Updated"

    def test_delete_actor_ability_removes_only_that_slug(self, tmp_path: Path) -> None:
        from dungeon_daddy.rpg.models import ActorAbility
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        for slug, name in [("strike", "Strike"), ("dodge", "Dodge")]:
            repo.save_actor_ability(ActorAbility(
                actor_id="actor:c:hero",
                ability_slug=slug,
                display_name=name,
                description="desc",
                source="kit",
            ))
        repo.delete_actor_ability("actor:c:hero", "strike")
        result = repo.get_actor_abilities("actor:c:hero")
        repo.close()
        assert len(result) == 1
        assert result[0].ability_slug == "dodge"

    def test_migration_011_applies_on_existing_db(self, tmp_path: Path) -> None:
        import shutil
        staged_dir = tmp_path / "migrations_staged"
        staged_dir.mkdir()
        for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if f.name >= "011":
                break
            shutil.copy(f, staged_dir / f.name)
        repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo.initialize_schema(staged_dir)
        repo.close()
        shutil.copy(MIGRATIONS_DIR / "011_actor_abilities.sql", staged_dir / "011_actor_abilities.sql")
        repo2 = MemoryRepository(db_path=tmp_path / "test.duckdb")
        repo2.initialize_schema(staged_dir)
        tables = repo2.list_tables()
        repo2.close()
        assert "actor_abilities" in tables
