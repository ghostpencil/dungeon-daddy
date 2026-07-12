"""Slice B1 — LookupService (read-only façade over search_entities; spec §7/§8).

Formats `lookup_world` tool results: compact rows, snippet truncated to ~200
chars, a ~1,200-token result budget with overflow dropped behind a `+N more`
marker, and errors surfaced as data (never raised).
"""
from __future__ import annotations

from pathlib import Path

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
