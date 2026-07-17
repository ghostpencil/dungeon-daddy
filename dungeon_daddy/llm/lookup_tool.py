"""The `lookup_world` narrator tool (spec §7/§9/§10, Phase 51.8 Slice B4).

Two pieces bridge the read-only :class:`~dungeon_daddy.memory.lookup.LookupService`
to the agent-owned tool loop:

- :data:`LOOKUP_WORLD_TOOL` — the provider-neutral :class:`LLMToolDef` (L1/§7).
- :func:`build_lookup_executor` — turns an ``LLMToolCall`` into a tool-result
  string, applying the L7 scoping layers (full-overlap **redirect**, partial
  **redundant-lookup telemetry**) and L6 logging.

The executor holds only a ``LookupService`` (no write method) — read-only by
construction (spec §8).
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from .provider import LLMToolCall, LLMToolDef

if TYPE_CHECKING:
    from dungeon_daddy.memory.lookup import LookupResult
    from dungeon_daddy.memory.models import ContextBundle

_log = logging.getLogger(__name__)

# L7 full-overlap redirect: when every hit was already in the bundle, end the
# round without spending budget re-returning duplicates (spec §10).
REDIRECT_MESSAGE = "Already in your context — do not look this up again."

LOOKUP_WORLD_TOOL = LLMToolDef(
    name="lookup_world",
    description=(
        "Search this campaign's world database. ONLY for entities, places, or "
        "past events NOT covered by your context (current room contents, present "
        "actors, Related Lore). Never look up something already in your context. "
        "Returns matching entities and memories with their tags."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "optional substring, matched case-insensitively against names and slugs",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "optional list of canonical tags (OR semantics); e.g. ['actor:npc:mira-coldwell', 'theme:guilt']",
            },
            "entity_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "optional filter, exact values only: actor|object|item|clock|"
                    "objective|faction|memory|room"
                ),
            },
            "limit": {
                "type": "integer",
                "description": "max results, default 8, cap 20",
            },
        },
    },
)


@dataclass
class LookupRecord:
    """L6 provenance for a single `lookup_world` call (surfaced in the debug
    panel; spec §10 L6/L7)."""

    query: str | None
    tags: list[str] = field(default_factory=list)
    entity_types: list[str] = field(default_factory=list)
    hit_count: int = 0  # rows returned, i.e. *after* the service's budget trim
    overlap_count: int = 0  # hits already present in the bundle (redundant_lookup)
    redirected: bool = False  # full overlap → redirect returned instead of rows
    omitted: int = 0  # rows the ~1,200-token budget dropped
    error: str | None = None  # bad request surfaced as data (L4), not raised


def bundle_entity_ids(bundle: ContextBundle) -> set[str]:
    """The entity ids already surfaced in the scene context bundle (L7).

    Used to drive the redundant-lookup telemetry + full-overlap redirect: a
    ``lookup_world`` hit whose id is in this set was already available to the
    narrator. Collects memory-card + related-lore memory ids, the current
    room's own id, and the ids of its objects / loose items / present actors,
    plus open clocks and active factions — matching the ``id`` field
    ``search_entities`` returns per entity type.
    """
    ids: set[str] = set()

    def _add(value: object) -> None:
        if isinstance(value, str):
            ids.add(value)

    for card in bundle.memory_cards:
        _add(card.get("memory_id"))
    for lore in bundle.related_lore:
        _add(lore.get("memory_id"))
    for clock in bundle.open_clocks:
        _add(clock.get("clock_id"))
    for faction in bundle.faction_reputations:
        _add(faction.get("faction_id"))
    room = bundle.current_room or {}
    _add(room.get("room_id"))
    for obj in room.get("objects", []):
        _add(obj.get("object_id"))
    for item in room.get("loose_items", []):
        _add(item.get("item_id"))
    for actor in room.get("npcs", []):
        _add(actor.get("actor_id"))
    for actor in room.get("monsters", []):
        _add(actor.get("actor_id"))
    return ids


# The tool schema's documented default (mirrors `LookupService.lookup`).
_DEFAULT_LIMIT = 8

# The entity vocabulary the tool advertises. `search_entities` does NOT validate
# `entity_types` — it only filters — so an unknown type there matches no source
# and returns an empty result the narrator reads as "this doesn't exist".
# Validate at this boundary instead, and name the alternatives in the error.
# Hand-maintained against `repository._ENTITY_SOURCES` + the memory branch;
# pinned by test_valid_entity_types_match_the_repository_sources.
VALID_ENTITY_TYPES: frozenset[str] = frozenset(
    {"actor", "object", "item", "clock", "objective", "faction", "memory", "room"}
)


class _BadToolArgs(ValueError):
    """The model's arguments have no safe reading (surfaced as L4 error data)."""


def _coerce_query(value: object) -> str | None:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    raise _BadToolArgs("'query' must be a string")


def _coerce_str_list(value: object, field_name: str) -> list[str] | None:
    """Accept the schema's array, or a bare string meaning one element.

    A bare string is the common model slip and its intent is unambiguous. Left
    uncoerced it is *silently destructive*: `set("theme:guilt")` is a set of
    characters that matches no tag, and `entity_types` is membership-tested
    against the string, so "actors" would match "actor" by substring.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return list(value)
    raise _BadToolArgs(f"'{field_name}' must be a string or an array of strings")


def _coerce_limit(value: object) -> int:
    """Never fail the lookup over `limit` — it only caps an already-capped row
    count, so an unusable value falls back to the documented default."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return _DEFAULT_LIMIT
    try:
        return int(value)
    except (TypeError, ValueError):
        return _DEFAULT_LIMIT


class _Lookup(Protocol):
    def lookup(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        entity_types: list[str] | None = None,
        limit: int = 8,
    ) -> LookupResult: ...


def build_lookup_executor(
    service: _Lookup,
    bundle_entity_ids: set[str],
    *,
    on_lookup: Callable[[LookupRecord], None] | None = None,
) -> Callable[[LLMToolCall], str]:
    """Return the tool executor the loop calls per `lookup_world` request.

    ``bundle_entity_ids`` are the entity ids already in the scene context; a
    lookup whose hits fully overlap them is **redirected** (L7 hard-stop), and
    any partial overlap is recorded as ``overlap_count`` for telemetry. Each
    call is logged and reported via ``on_lookup``.
    """

    def _fail(message: str) -> str:
        """L4: a bad request comes back as data — but it is still recorded, so
        the debug panel shows `→ ERROR` rather than an innocent `0 hit(s)`."""
        _log.warning("lookup_world rejected: %s", message)
        if on_lookup is not None:
            on_lookup(LookupRecord(query=None, error=message))
        return json.dumps(
            {"results": [], "omitted": 0, "error": message}, ensure_ascii=False
        )

    def _execute(call: LLMToolCall) -> str:
        if not isinstance(call.arguments, dict):
            # A provider can hand back a JSON array; `.get` on it would raise
            # through the turn.
            return _fail("tool arguments must be a JSON object")
        args = call.arguments
        try:
            query = _coerce_query(args.get("query"))
            tags = _coerce_str_list(args.get("tags"), "tags")
            entity_types = _coerce_str_list(args.get("entity_types"), "entity_types")
        except _BadToolArgs as exc:
            return _fail(str(exc))
        if entity_types is not None:
            unknown = [t for t in entity_types if t not in VALID_ENTITY_TYPES]
            if unknown:
                return _fail(
                    f"unknown entity_types {unknown} — valid types are "
                    f"{', '.join(sorted(VALID_ENTITY_TYPES))}"
                )
        limit = _coerce_limit(args.get("limit"))

        result = service.lookup(
            query=query, tags=tags, entity_types=entity_types, limit=limit
        )
        rows = result.get("results", [])
        overlap_count = sum(1 for r in rows if r.get("id") in bundle_entity_ids)
        redirected = bool(rows) and overlap_count == len(rows)

        record = LookupRecord(
            query=query,
            tags=list(tags or []),
            entity_types=list(entity_types or []),
            hit_count=len(rows),
            overlap_count=overlap_count,
            redirected=redirected,
            omitted=result.get("omitted", 0),
            error=result.get("error"),
        )
        _log.info(
            "lookup_world query=%r tags=%r hits=%d overlap=%d redirected=%s "
            "omitted=%d error=%r",
            query,
            tags,
            record.hit_count,
            overlap_count,
            redirected,
            record.omitted,
            record.error,
        )
        if on_lookup is not None:
            on_lookup(record)

        if redirected:
            return REDIRECT_MESSAGE
        return json.dumps(result, ensure_ascii=False)

    return _execute
