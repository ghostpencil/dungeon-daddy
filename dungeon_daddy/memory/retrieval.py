from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from dungeon_daddy.memory.models import MemoryEntry
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.tags import actor_tag


def present_actor_ids(
    repo: MemoryRepository,
    campaign_id: str,
    room_id: str | None,
    party_ids: Iterable[str],
) -> list[str]:
    """Actor ids present in the scene: the party plus any NPCs/monsters in the
    given room. Deduped, order-preserving. An empty/None room contributes no
    room actors (and callers should likewise pass no ``location_slug``)."""
    ids = list(party_ids)
    if room_id:
        in_room = repo.get_actors_by_room(
            campaign_id, room_id, actor_types=["npc", "monster"]
        )
        ids.extend(a["actor_id"] for a in in_room)
    return list(dict.fromkeys(ids))


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
        # Whether the caller asked to scope the query at all. Distinguishes a
        # no-filter "give me everything" call from a scoped call whose filters
        # resolved to nothing (e.g. an unknown actor_id) — the latter must
        # return no rows, not silently widen to the whole campaign.
        filters_requested = bool(tags or actor_ids or location_slug)
        tag_filters: list[str] = list(tags or [])
        for aid in actor_ids or []:
            # §5.1: resolve the actor record to its canonical
            # actor:<subtype>:<slug> tag; an unknown or cross-campaign id
            # contributes nothing (get_actor is not campaign-scoped, so guard it).
            actor = self._repo.get_actor(aid)
            if actor is not None and actor["campaign_id"] == self._campaign_id:
                tag_filters.append(actor_tag(actor["actor_type"], actor["slug"]))
        if location_slug:
            tag_filters.append(f"location:{location_slug}")

        if filters_requested and not tag_filters:
            return []

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
