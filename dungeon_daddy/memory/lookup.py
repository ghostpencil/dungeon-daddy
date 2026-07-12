"""Read-only lookup façade for the narrator `lookup_world` tool.

Phase 51.8 Slice B1 (spec §7/§8). `LookupService` wraps
`MemoryRepository.search_entities` and formats its rows into a compact,
budget-bounded tool result. It exposes **no write method** — the tool executor
that holds it is read-only by construction (spec §8).
"""
from __future__ import annotations

import json
from typing import Any

from dungeon_daddy.memory.repository import MemoryRepository

# Snippet cap (~200 chars, spec §7). Overflow is truncated with an ellipsis.
_SNIPPET_MAX = 200

# Total tool-result token budget (~1,200, spec §7). Rows past it are dropped
# and reported via `omitted`. Token cost is estimated as JSON-length // 4,
# matching the retrieval layer's `trim_to_budget` heuristic.
_RESULT_TOKEN_BUDGET = 1200


def _row_tokens(row: dict[str, Any]) -> int:
    return len(json.dumps(row, ensure_ascii=False)) // 4


def _truncate_snippet(text: str) -> str:
    if len(text) <= _SNIPPET_MAX:
        return text
    return text[:_SNIPPET_MAX] + "…"


class LookupService:
    def __init__(self, repo: MemoryRepository, campaign_id: str) -> None:
        self._repo = repo
        self._campaign_id = campaign_id

    def lookup(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        entity_types: list[str] | None = None,
        limit: int = 8,
    ) -> dict[str, Any]:
        """Return `{results: [compact rows], omitted: N}` for the tool.

        `results` are ranked `search_entities` rows with snippets truncated;
        `omitted` counts rows dropped to stay within the token budget. A bad
        request (e.g. neither query nor tags) is surfaced as `error` rather than
        raised — the tool loop reports errors as data (spec §13 L4).
        """
        try:
            rows = self._repo.search_entities(
                self._campaign_id, query, tags, entity_types, limit
            )
        except ValueError as exc:
            return {"results": [], "omitted": 0, "error": str(exc)}

        results: list[dict[str, Any]] = []
        used = 0
        for i, row in enumerate(rows):
            compact = self._compact(row)
            cost = _row_tokens(compact)
            # Always keep the first row so a single fat row still returns; drop
            # the rest once the budget would be exceeded.
            if results and used + cost > _RESULT_TOKEN_BUDGET:
                return {"results": results, "omitted": len(rows) - i}
            results.append(compact)
            used += cost
        return {"results": results, "omitted": 0}

    @staticmethod
    def _compact(row: dict[str, Any]) -> dict[str, Any]:
        return {**row, "snippet": _truncate_snippet(row["snippet"])}
