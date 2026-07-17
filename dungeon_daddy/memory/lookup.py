"""Read-only lookup façade for the narrator `lookup_world` tool.

Phase 51.8 Slice B1 (spec §7/§8). `LookupService` wraps
`MemoryRepository.search_entities` and formats its rows into a compact,
budget-bounded tool result. It exposes **no write method** — the tool executor
that holds it is read-only by construction (spec §8).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from dungeon_daddy.memory.repository import MemoryRepository

_log = logging.getLogger(__name__)

# What the model is told when the search itself broke. Deliberately carries no
# detail: the string becomes a tool result, and a raw DuckDB message quotes the
# SQL (spec §8). It still reads as retryable-or-not to the narrator.
_LOOKUP_FAILED_MESSAGE = "lookup failed — the world database could not be searched"

# Snippet cap (~200 chars, spec §7). Overflow is truncated with an ellipsis.
_SNIPPET_MAX = 200

# Total tool-result token budget (~1,200, spec §7). Rows past it are dropped
# and reported via `omitted`. Token cost is estimated as JSON-length // 4 — the
# same `chars // 4` heuristic as the retrieval layer's `trim_to_budget`, though
# not the same measurement: that one costs plain title+summary text, and it
# drops an oversized first entry where `lookup` deliberately keeps it.
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
            # The model's own bad request: its text says how to fix the call,
            # so hand it back verbatim.
            return {"results": [], "omitted": 0, "error": str(exc)}
        except Exception:
            # Anything else is ours, not the model's (schema drift, a locked
            # DB). It gets a generic string: the error is fed straight back as
            # a tool result, and DuckDB echoes the failing SQL in its message —
            # which would break the §8 "the LLM never sees SQL" boundary. The
            # real cause goes to the log instead.
            _log.exception(
                "search_entities failed: campaign=%r query=%r tags=%r",
                self._campaign_id, query, tags,
            )
            return {"results": [], "omitted": 0, "error": _LOOKUP_FAILED_MESSAGE}

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
