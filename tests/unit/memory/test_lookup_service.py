"""Slice B1 — LookupService (read-only façade over search_entities; spec §7/§8).

Formats `lookup_world` tool results: compact rows, snippet truncated to ~200
chars, a ~1,200-token result budget with overflow reported as an `omitted`
count, and errors surfaced as data (never raised).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest

from dungeon_daddy.memory.lookup import LookupService
from dungeon_daddy.memory.repository import MemoryRepository

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[3]
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


def _service(tmp_path: Path, campaign_id: str = "camp-A") -> tuple[LookupService, MemoryRepository]:
    repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
    repo.initialize_schema(MIGRATIONS_DIR)
    return LookupService(repo, campaign_id), repo


class TestLookupServiceFormatting:
    def test_returns_compact_rows(self, tmp_path: Path) -> None:
        service, repo = _service(tmp_path)
        repo.save_actor(
            "a1", "camp-A", "npc", "mira", "Mira", tags=["actor:npc:mira"]
        )
        result = service.lookup(query="mira")
        assert result["omitted"] == 0
        row = result["results"][0]
        assert row == {
            "entity_type": "actor",
            "id": "a1",
            "slug": "mira",
            "display_name": "Mira",
            "room_id": None,
            "status": "active",
            "tags": ["actor:npc:mira"],
            "snippet": "",
        }

    def test_snippet_truncated_to_200_chars(self, tmp_path: Path) -> None:
        service, repo = _service(tmp_path)
        from dungeon_daddy.rpg.models import RoomObject

        long_desc = "x" * 500
        repo.save_room_object(
            RoomObject(
                object_id="o1", campaign_id="camp-A", room_id="R1", level_id="level:0",
                slug="thing", display_name="Thing", archetype="lore_fixture",
                description=long_desc, current_state="present",
            )
        )
        row = service.lookup(query="thing")["results"][0]
        assert len(row["snippet"]) <= 201  # 200 + ellipsis char
        assert row["snippet"].endswith("…")


class TestLookupServiceBudget:
    def test_overflow_rows_dropped_and_counted(self, tmp_path: Path) -> None:
        service, repo = _service(tmp_path)
        from dungeon_daddy.rpg.models import RoomObject

        for i in range(20):
            repo.save_room_object(
                RoomObject(
                    object_id=f"o{i}", campaign_id="camp-A", room_id="R1",
                    level_id="level:0", slug=f"relic-{i}", display_name=f"Relic {i}",
                    archetype="lore_fixture", description="x" * 200,
                    current_state="present", tags=["theme:big"],
                )
            )
        result = service.lookup(tags=["theme:big"], limit=20)
        # 20 fat rows exceed the ~1,200-token budget, so some are dropped.
        assert result["omitted"] >= 1
        assert len(result["results"]) + result["omitted"] == 20

    def test_small_result_set_omits_nothing(self, tmp_path: Path) -> None:
        service, repo = _service(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira")
        result = service.lookup(query="mira", limit=20)
        assert result["omitted"] == 0
        assert len(result["results"]) == 1


class TestLookupServiceReadOnly:
    def test_exposes_only_lookup(self, tmp_path: Path) -> None:
        # spec §8 hard rule: the tool executor holds a read-only service that
        # exposes no write method. `lookup` is its entire public surface.
        public = [n for n in dir(LookupService) if not n.startswith("_")]
        assert public == ["lookup"]


class TestLookupServiceErrors:
    def test_missing_query_and_tags_returns_error_not_raise(self, tmp_path: Path) -> None:
        service, _ = _service(tmp_path)
        result = service.lookup()
        assert result["results"] == []
        assert isinstance(result["error"], str)
        assert result["error"]

    def test_bad_request_error_keeps_its_correctable_text(self, tmp_path: Path) -> None:
        # A ValueError is the model's own fault and its text tells it how to
        # fix the call — that detail must survive (L4).
        service, _ = _service(tmp_path)
        result = service.lookup()
        assert "query" in result["error"]


class _SearchOnly:
    """The smallest object satisfying the search seam: `search_entities` and
    nothing else — no write methods, no repository machinery."""

    def search_entities(
        self,
        campaign_id: str,
        query: str | None = None,
        tags: list[str] | None = None,
        entity_types: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        return []


class TestLookupServiceCtorSeam:
    """Cleanup item 1 (Phase B review): "read-only by construction" (spec §8)
    must be compiler-enforced. The ctor's seam is the search-only
    `EntitySearch` Protocol, so a write method on the service could not even
    type-check — the write-capable repository is only one possible provider."""

    def test_real_repository_satisfies_the_search_seam(self, tmp_path: Path) -> None:
        from dungeon_daddy.memory.lookup import EntitySearch

        repo = MemoryRepository(db_path=tmp_path / "t.duckdb")
        assert isinstance(repo, EntitySearch)

    def test_a_search_only_object_is_a_complete_dependency(self) -> None:
        service = LookupService(_SearchOnly(), "camp-A")
        assert service.lookup(query="mira") == {"results": [], "omitted": 0}


class _ExplodingRepo:
    """A repo whose search raises the way DuckDB does — with the SQL in the
    message. Real repos can't be made to fail this way on demand."""

    MESSAGE = (
        "Catalog Error: Table with name rooms does not exist!\n"
        "LINE 1: ...SELECT room_id, slug, display_name FROM rooms WHERE campaign_id = ?"
    )

    def search_entities(self, *args: object, **kwargs: object) -> list[dict[str, Any]]:
        raise RuntimeError(self.MESSAGE)


class TestLookupServiceInfrastructureErrors:
    """Slice B4 review fix: only `ValueError` was caught, so a schema-drifted DB
    (e.g. migration 022 unapplied) raised out through the executor — where it
    became an unlogged `Error: ...` string with no LookupRecord behind it."""

    def test_infrastructure_error_is_returned_as_data(self) -> None:
        service = LookupService(_ExplodingRepo(), "camp-A")
        result = service.lookup(query="mira")
        assert result["results"] == []
        assert result["error"]

    def test_infrastructure_error_does_not_leak_sql_to_the_model(self) -> None:
        # docs/LLM_AUTHORITY_BOUNDARY.md promises "the LLM never sees SQL".
        # The error string is fed straight back as a tool result, so a raw
        # DuckDB message would break that promise.
        service = LookupService(_ExplodingRepo(), "camp-A")
        error = service.lookup(query="mira")["error"]
        assert "SELECT" not in error
        assert "FROM rooms" not in error
        assert "campaign_id = ?" not in error

    def test_infrastructure_error_is_logged_with_its_detail(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # The model gets a generic string; the developer must still get the
        # real cause, or the failure is invisible everywhere.
        service = LookupService(_ExplodingRepo(), "camp-A")
        with caplog.at_level(logging.ERROR):
            service.lookup(query="mira")
        assert "rooms does not exist" in caplog.text
