from __future__ import annotations

from dungeon_daddy.memory.repository import MemoryRepository


class MemoryRetrieval:
    def __init__(self, repo: MemoryRepository) -> None:
        self._repo = repo

    def by_actor(self, actor_tag: str) -> list[dict]:
        return self._by_tag_query(actor_tag)

    def by_location(self, location_tag: str) -> list[dict]:
        return self._by_tag_query(location_tag)

    def by_tag(self, tag: str) -> list[dict]:
        return self._by_tag_query(tag)

    def _by_tag_query(self, tag: str) -> list[dict]:
        assert self._repo._conn is not None
        rows = self._repo._conn.execute(
            """
            SELECT e.memory_id, e.campaign_id, e.type, e.title, e.summary,
                   e.status, e.importance, e.markdown_path, e.checksum
            FROM memory_entries e
            JOIN memory_tags t ON e.memory_id = t.memory_id
            WHERE t.tag = ?
            ORDER BY e.importance DESC
            """,
            [tag],
        ).fetchall()
        return [
            {
                "memory_id": r[0],
                "campaign_id": r[1],
                "type": r[2],
                "title": r[3],
                "summary": r[4],
                "status": r[5],
                "importance": r[6],
                "markdown_path": r[7],
                "checksum": r[8],
            }
            for r in rows
        ]
