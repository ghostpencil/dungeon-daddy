from __future__ import annotations

from typing import Any

from dungeon_daddy.memory.models import MemoryEntry
from dungeon_daddy.memory.repository import MemoryRepository


class MemoryRetriever:
    def __init__(self, repo: MemoryRepository, campaign_id: str) -> None:
        self._repo = repo
        self._campaign_id = campaign_id

    def query(
        self,
        tags: list[str] | None = None,
        actor_ids: list[str] | None = None,
        location_slug: str | None = None,
        include_archived: bool = False,
    ) -> list[MemoryEntry]:
        assert self._repo._conn is not None
        tag_filters: list[str] = list(tags or [])
        if actor_ids:
            tag_filters.extend(f"actor:{aid}" for aid in actor_ids)
        if location_slug:
            tag_filters.append(f"location:{location_slug}")

        status_clause = (
            "AND e.status = 'approved'"
            if not include_archived
            else ""
        )

        if tag_filters:
            placeholders = ", ".join("?" for _ in tag_filters)
            sql = f"""
                SELECT DISTINCT e.memory_id, e.campaign_id, e.type, e.title,
                       e.summary, e.status, e.importance, e.markdown_path,
                       e.checksum, e.created_at
                FROM memory_entries e
                JOIN memory_tags t ON e.memory_id = t.memory_id
                WHERE e.campaign_id = ?
                  AND t.tag IN ({placeholders})
                  {status_clause}
                ORDER BY e.importance DESC, e.created_at DESC
            """
            params = [self._campaign_id] + tag_filters
        else:
            sql = f"""
                SELECT e.memory_id, e.campaign_id, e.type, e.title,
                       e.summary, e.status, e.importance, e.markdown_path,
                       e.checksum, e.created_at
                FROM memory_entries e
                WHERE e.campaign_id = ?
                  {status_clause}
                ORDER BY e.importance DESC, e.created_at DESC
            """
            params = [self._campaign_id]

        rows = self._repo._conn.execute(sql, params).fetchall()
        return [
            MemoryEntry(
                memory_id=r[0],
                campaign_id=r[1],
                type=r[2],
                title=r[3],
                summary=r[4],
                status=r[5],
                importance=r[6],
                markdown_path=r[7],
                checksum=r[8],
                created_at=r[9],
            )
            for r in rows
        ]

    def trim_to_budget(
        self, entries: list[MemoryEntry], max_tokens: int
    ) -> tuple[list[MemoryEntry], int]:
        kept: list[MemoryEntry] = []
        used = 0
        for entry in entries:
            cost = (len(entry.title) + len(entry.summary)) // 4
            if used + cost > max_tokens:
                break
            kept.append(entry)
            used += cost
        return kept, len(entries) - len(kept)


class MemoryRetrieval:
    def __init__(self, repo: MemoryRepository) -> None:
        self._repo = repo

    def by_actor(self, actor_tag: str) -> list[dict[str, Any]]:
        return self._by_tag_query(actor_tag)

    def by_location(self, location_tag: str) -> list[dict[str, Any]]:
        return self._by_tag_query(location_tag)

    def by_tag(self, tag: str) -> list[dict[str, Any]]:
        return self._by_tag_query(tag)

    def _by_tag_query(self, tag: str) -> list[dict[str, Any]]:
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
