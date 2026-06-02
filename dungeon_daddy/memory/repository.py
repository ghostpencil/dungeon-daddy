from __future__ import annotations

import json
from pathlib import Path

import duckdb

from dungeon_daddy.memory.models import DomainEvent


def _ensure_migration_table(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migration (
            name       TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _apply_migrations(conn: duckdb.DuckDBPyConnection, migrations_dir: Path) -> list[str]:
    _ensure_migration_table(conn)
    applied: set[str] = {
        row[0] for row in conn.execute("SELECT name FROM schema_migration").fetchall()
    }
    newly_applied: list[str] = []
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        if sql_file.name in applied:
            continue
        sql = sql_file.read_text(encoding="utf-8")
        # Execute each statement individually to handle multi-statement files
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                conn.execute(stmt)
        conn.execute(
            "INSERT INTO schema_migration (name) VALUES (?)", [sql_file.name]
        )
        newly_applied.append(sql_file.name)
    return newly_applied


class MigrationRunner:
    """Standalone migration runner — opens and closes its own connection."""

    def __init__(self, migrations_dir: Path, db_path: Path) -> None:
        self._migrations_dir = migrations_dir
        self._db_path = db_path

    def sql_files(self) -> list[Path]:
        return sorted(self._migrations_dir.glob("*.sql"))

    def run(self) -> list[str]:
        conn = duckdb.connect(str(self._db_path))
        try:
            return _apply_migrations(conn, self._migrations_dir)
        finally:
            conn.close()


class MemoryRepository:
    """Persistent DuckDB repository for memory and domain events."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: duckdb.DuckDBPyConnection | None = duckdb.connect(str(db_path))

    def health_check(self) -> bool:
        if self._conn is None:
            return False
        try:
            self._conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def initialize_schema(self, migrations_dir: Path) -> None:
        assert self._conn is not None
        _apply_migrations(self._conn, migrations_dir)

    def list_tables(self) -> list[str]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        return [row[0] for row in rows]

    def insert_domain_event(self, event: DomainEvent) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO domain_events (event_id, campaign_id, event_type, payload, occurred_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                event.event_id,
                event.campaign_id,
                event.event_type,
                json.dumps(event.payload),
                event.occurred_at,
            ],
        )

    def get_domain_events(self, campaign_id: str) -> list[DomainEvent]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT event_id, campaign_id, event_type, payload, occurred_at
            FROM domain_events
            WHERE campaign_id = ?
            ORDER BY occurred_at
            """,
            [campaign_id],
        ).fetchall()
        return [
            DomainEvent(
                event_id=row[0],
                campaign_id=row[1],
                event_type=row[2],
                payload=json.loads(row[3]),
                occurred_at=row[4],
            )
            for row in rows
        ]

    def list_migrations(self) -> list[str]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT name FROM schema_migration ORDER BY applied_at"
        ).fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
