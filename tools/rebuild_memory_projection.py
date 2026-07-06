"""Rebuild the memory search projection from raw rows.

Drops and recreates a flat `memory_search_projection` table that combines
memory_entries with their tags — useful after manual DB edits or migrations.
"""
from __future__ import annotations

from pathlib import Path

from dungeon_daddy.memory.repository import MemoryRepository


def rebuild_memory_projection(repo: MemoryRepository) -> int:
    """Drop and rebuild memory_search_projection. Returns row count."""
    conn = repo._conn
    assert conn is not None

    conn.execute("DROP TABLE IF EXISTS memory_search_projection")
    conn.execute(
        """
        CREATE TABLE memory_search_projection AS
        SELECT
            e.memory_id,
            e.campaign_id,
            e.type,
            e.title,
            e.summary,
            e.status,
            e.importance,
            string_agg(t.tag, ' ') AS tags
        FROM memory_entries e
        LEFT JOIN memory_tags t ON e.memory_id = t.memory_id
        GROUP BY
            e.memory_id, e.campaign_id, e.type, e.title,
            e.summary, e.status, e.importance
        """
    )
    count: int = conn.execute(
        "SELECT COUNT(*) FROM memory_search_projection"
    ).fetchone()[0]
    return count


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Rebuild the memory search projection from raw rows"
    )
    parser.add_argument("db_path", help="Path to campaign.duckdb")
    args = parser.parse_args()

    _MIGRATIONS = (
        Path(__file__).parent.parent / "dungeon_daddy" / "data" / "migrations"
    )
    r = MemoryRepository(Path(args.db_path))
    r.initialize_schema(_MIGRATIONS)
    n = rebuild_memory_projection(r)
    r.close()
    print(f"Rebuilt projection: {n} rows")
