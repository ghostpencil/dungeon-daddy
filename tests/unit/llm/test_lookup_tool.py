"""Slice B4a — the `lookup_world` tool def + executor factory (spec §7/§9/§10).

`build_lookup_executor` bridges an `LLMToolCall` to a read-only `LookupService`,
formats the result as a JSON string for the tool loop, and applies the L7
scoping layers (full-overlap redirect, redundant-lookup telemetry) plus L6
logging. Real `LookupService` over a real repo (mock policy: use real objects);
the L7 overlap is driven by the injected `bundle_entity_ids` set.
"""
from __future__ import annotations

import json
from pathlib import Path

from dungeon_daddy.llm.provider import LLMToolCall
from dungeon_daddy.memory.lookup import LookupService
from dungeon_daddy.memory.repository import MemoryRepository

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[3] / "dungeon_daddy" / "data" / "migrations"
)


def _service(tmp_path: Path, campaign_id: str = "camp-A") -> tuple[LookupService, MemoryRepository]:
    repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
    repo.initialize_schema(MIGRATIONS_DIR)
    return LookupService(repo, campaign_id), repo


def _call(**arguments: object) -> LLMToolCall:
    return LLMToolCall(call_id="c1", name="lookup_world", arguments=dict(arguments))


class TestExecutorResults:
    def test_returns_lookup_results_as_json(self, tmp_path: Path) -> None:
        service, repo = _service(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["actor:npc:mira"])

        from dungeon_daddy.llm.lookup_tool import build_lookup_executor

        executor = build_lookup_executor(service, bundle_entity_ids=set())
        payload = json.loads(executor(_call(query="mira")))
        assert payload["omitted"] == 0
        assert payload["results"][0]["id"] == "a1"

    def test_error_result_passed_through_as_json(self, tmp_path: Path) -> None:
        # Neither query nor tags → service returns an error dict as data; the
        # executor forwards it (not a redirect, not a raise). Spec §13 L4.
        service, _ = _service(tmp_path)
        from dungeon_daddy.llm.lookup_tool import build_lookup_executor

        executor = build_lookup_executor(service, bundle_entity_ids=set())
        payload = json.loads(executor(_call()))
        assert payload["results"] == []
        assert payload["error"]


class TestL7Scoping:
    def test_full_overlap_returns_redirect(self, tmp_path: Path) -> None:
        service, repo = _service(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["actor:npc:mira"])

        from dungeon_daddy.llm.lookup_tool import REDIRECT_MESSAGE, build_lookup_executor

        executor = build_lookup_executor(service, bundle_entity_ids={"a1"})
        assert executor(_call(query="mira")) == REDIRECT_MESSAGE

    def test_partial_overlap_returns_rows_and_flags_redundant(self, tmp_path: Path) -> None:
        service, repo = _service(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["theme:x"])
        repo.save_actor("a2", "camp-A", "npc", "boro", "Boro", tags=["theme:x"])

        from dungeon_daddy.llm.lookup_tool import LookupRecord, build_lookup_executor

        records: list[LookupRecord] = []
        executor = build_lookup_executor(
            service, bundle_entity_ids={"a1"}, on_lookup=records.append
        )
        payload = json.loads(executor(_call(tags=["theme:x"])))
        assert {r["id"] for r in payload["results"]} == {"a1", "a2"}
        assert records[0].overlap_count == 1
        assert records[0].hit_count == 2
        assert records[0].redirected is False

    def test_no_overlap_reports_zero_and_returns_rows(self, tmp_path: Path) -> None:
        service, repo = _service(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["theme:x"])

        from dungeon_daddy.llm.lookup_tool import LookupRecord, build_lookup_executor

        records: list[LookupRecord] = []
        executor = build_lookup_executor(
            service, bundle_entity_ids={"other"}, on_lookup=records.append
        )
        payload = json.loads(executor(_call(tags=["theme:x"])))
        assert payload["results"][0]["id"] == "a1"
        assert records[0].overlap_count == 0
        assert records[0].redirected is False


class TestToolDef:
    def test_tool_def_shape(self) -> None:
        from dungeon_daddy.llm.lookup_tool import LOOKUP_WORLD_TOOL

        assert LOOKUP_WORLD_TOOL.name == "lookup_world"
        props = LOOKUP_WORLD_TOOL.parameters["properties"]
        assert set(props) == {"query", "tags", "entity_types", "limit"}


class TestBundleEntityIds:
    def test_collects_all_scene_entity_ids(self) -> None:
        from dungeon_daddy.llm.lookup_tool import bundle_entity_ids
        from dungeon_daddy.memory.models import ContextBundle

        bundle = ContextBundle(
            bundle_id="b", campaign_id="c", mode="run_scene",
            memory_cards=[{"memory_id": "m1"}],
            related_lore=[{"memory_id": "m2"}],
            open_clocks=[{"clock_id": "cl1"}],
            faction_reputations=[{"faction_id": "f1"}],
            current_room={
                "room_id": "R1",
                "objects": [{"object_id": "o1"}],
                "loose_items": [{"item_id": "i1"}],
                "npcs": [{"actor_id": "n1"}],
                "monsters": [{"actor_id": "mo1"}],
            },
        )
        assert bundle_entity_ids(bundle) == {
            "m1", "m2", "cl1", "f1", "R1", "o1", "i1", "n1", "mo1"
        }

    def test_empty_bundle_yields_empty_set(self) -> None:
        from dungeon_daddy.llm.lookup_tool import bundle_entity_ids
        from dungeon_daddy.memory.models import ContextBundle

        bundle = ContextBundle(bundle_id="b", campaign_id="c", mode="run_scene")
        assert bundle_entity_ids(bundle) == set()
