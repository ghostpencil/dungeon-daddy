from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from dungeon_daddy.memory.models import MemoryEntry
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.tags import actor_tag, validate_tag

_log = logging.getLogger(__name__)


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


def scene_memory_tags(
    repo: MemoryRepository,
    campaign_id: str,
    room_id: str | None,
    party_ids: Iterable[str],
) -> list[str]:
    """Write-side twin of :func:`present_actor_ids` (Slice A5b).

    The canonical scene-anchor tags to stamp on an engine memory write so A5
    scoped retrieval resurfaces it: the current-room ``location:<room_id>``
    (grid id) plus ``actor_tag(...)`` for the party and any NPCs/monsters in the
    room — exactly the anchors the reader filters on (``query``'s
    ``location_slug`` + ``present_actor_ids``), so writes and reads are
    symmetric by construction. Every tag passes :func:`validate_tag` (they are
    canonical by construction; the call is a loud regression guard). An unknown
    or cross-campaign actor id contributes nothing (and is logged, since a
    party/room actor that fails to resolve permanently under-tags the memory).
    Order-preserving, deduped.
    """
    tags: list[str] = []
    if room_id:
        tags.append(validate_tag(f"location:{room_id}"))
    for aid in present_actor_ids(repo, campaign_id, room_id, party_ids):
        actor = repo.get_actor(aid)
        if actor is not None and actor["campaign_id"] == campaign_id:
            tags.append(validate_tag(actor_tag(actor["actor_type"], actor["slug"])))
        else:
            _log.warning(
                "scene_memory_tags: actor_id %r did not resolve (campaign=%r); "
                "omitted from memory anchor tags",
                aid,
                campaign_id,
            )
    return list(dict.fromkeys(tags))


def _entry_from_row(r: tuple[Any, ...]) -> MemoryEntry:
    """Map a memory_entries SELECT row (columns memory_id..created_at, in
    schema order) to a :class:`MemoryEntry`. Any trailing columns (e.g. a
    COUNT used only for ranking) are ignored."""
    return MemoryEntry(
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
            # contributes nothing (get_actor is not campaign-scoped, so guard it)
            # and is logged, since a dropped filter silently narrows the result.
            actor = self._repo.get_actor(aid)
            if actor is not None and actor["campaign_id"] == self._campaign_id:
                tag_filters.append(actor_tag(actor["actor_type"], actor["slug"]))
            else:
                _log.warning(
                    "query: actor_id %r did not resolve to a canonical tag "
                    "(campaign=%r); dropped from filter",
                    aid,
                    self._campaign_id,
                )
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
        return [_entry_from_row(r) for r in rows]

    def query_by_tag_relevance(self, tags: list[str]) -> list[MemoryEntry]:
        """Slice A6 (T7): related-lore retrieval ranked by *relevance*.

        Returns approved memories sharing any of ``tags``, ordered by tag-hit
        count DESC (how many of the anchor tags a memory carries), then
        importance DESC, then recency (``created_at`` DESC) — the ranking the
        ``# Related Lore`` pre-fetch wants (spec §5 T7). An empty tag list
        returns nothing (no anchors → no related lore).
        """
        assert self._repo._conn is not None
        if not tags:
            return []
        placeholders = ", ".join("?" for _ in tags)
        sql = f"""
            SELECT e.memory_id, e.campaign_id, e.type, e.title, e.summary,
                   e.status, e.importance, e.markdown_path, e.checksum,
                   e.created_at, COUNT(t.tag) AS hits
            FROM memory_entries e
            JOIN memory_tags t ON e.memory_id = t.memory_id
            WHERE e.campaign_id = ?
              AND t.tag IN ({placeholders})
              AND e.status = 'approved'
            GROUP BY e.memory_id, e.campaign_id, e.type, e.title, e.summary,
                     e.status, e.importance, e.markdown_path, e.checksum,
                     e.created_at
            ORDER BY hits DESC, e.importance DESC, e.created_at DESC
        """
        params = [self._campaign_id] + tags
        rows = self._repo._conn.execute(sql, params).fetchall()
        # The extra COUNT(...) column (r[10]) is used only for ORDER BY.
        return [_entry_from_row(r) for r in rows]

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
