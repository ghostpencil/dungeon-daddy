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

    def test_error_is_recorded_on_the_record(self, tmp_path: Path) -> None:
        # L6: a failed lookup must be distinguishable from a legitimate
        # no-match in the debug panel, so the error rides on the record.
        service, _ = _service(tmp_path)
        from dungeon_daddy.llm.lookup_tool import LookupRecord, build_lookup_executor

        records: list[LookupRecord] = []
        executor = build_lookup_executor(
            service, bundle_entity_ids=set(), on_lookup=records.append
        )
        executor(_call())

        assert records[0].error
        assert records[0].hit_count == 0

    def test_omitted_is_recorded_on_the_record(self, tmp_path: Path) -> None:
        # L6: rows the ~1,200-token budget dropped are provenance too —
        # `hit_count` alone hides that the narrator's evidence was truncated.
        service, repo = _service(tmp_path)
        from dungeon_daddy.llm.lookup_tool import LookupRecord, build_lookup_executor
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

        records: list[LookupRecord] = []
        executor = build_lookup_executor(
            service, bundle_entity_ids=set(), on_lookup=records.append
        )
        executor(_call(tags=["theme:big"], limit=20))

        assert records[0].omitted >= 1
        assert records[0].hit_count + records[0].omitted == 20


class TestArgumentCoercion:
    """The model's JSON is untrusted input (Slice B4 review fix).

    Round 0 is the only tool round (`max_rounds=2` forces plain text on the
    last), so a rejected argument costs the narrator the fact entirely. Coerce
    what has an obvious reading; error only on the genuinely ambiguous.
    """

    def test_null_limit_falls_back_to_the_default(self, tmp_path: Path) -> None:
        # `{"limit": null}` is a routine serialization of an unset optional int.
        service, repo = _service(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["actor:npc:mira"])
        from dungeon_daddy.llm.lookup_tool import build_lookup_executor

        executor = build_lookup_executor(service, bundle_entity_ids=set())
        payload = json.loads(executor(_call(query="mira", limit=None)))
        assert payload["results"][0]["id"] == "a1"
        assert "error" not in payload

    def test_string_limit_is_coerced(self, tmp_path: Path) -> None:
        service, repo = _service(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["actor:npc:mira"])
        from dungeon_daddy.llm.lookup_tool import build_lookup_executor

        executor = build_lookup_executor(service, bundle_entity_ids=set())
        payload = json.loads(executor(_call(query="mira", limit="5")))
        assert payload["results"][0]["id"] == "a1"

    def test_unusable_limit_falls_back_rather_than_failing(self, tmp_path: Path) -> None:
        # `limit` is an optimization knob — a bad one must not cost the lookup.
        service, repo = _service(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["actor:npc:mira"])
        from dungeon_daddy.llm.lookup_tool import build_lookup_executor

        executor = build_lookup_executor(service, bundle_entity_ids=set())
        payload = json.loads(executor(_call(query="mira", limit="lots")))
        assert payload["results"][0]["id"] == "a1"

    def test_bare_string_tags_is_read_as_a_single_tag(self, tmp_path: Path) -> None:
        # Without this, `set("theme:guilt")` becomes a set of CHARACTERS, which
        # matches no tag — a silent zero-hit answer the narrator reads as
        # "this lore does not exist".
        service, repo = _service(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["theme:guilt"])
        from dungeon_daddy.llm.lookup_tool import build_lookup_executor

        executor = build_lookup_executor(service, bundle_entity_ids=set())
        payload = json.loads(executor(_call(tags="theme:guilt")))
        assert [r["id"] for r in payload["results"]] == ["a1"]

    def test_bare_string_entity_types_is_read_as_a_single_type(self, tmp_path: Path) -> None:
        service, repo = _service(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["theme:guilt"])
        from dungeon_daddy.llm.lookup_tool import build_lookup_executor

        executor = build_lookup_executor(service, bundle_entity_ids=set())
        payload = json.loads(executor(_call(query="mira", entity_types="actor")))
        assert [r["id"] for r in payload["results"]] == ["a1"]

    def test_uninterpretable_tags_error_rather_than_search_wrongly(
        self, tmp_path: Path
    ) -> None:
        service, _ = _service(tmp_path)
        from dungeon_daddy.llm.lookup_tool import LookupRecord, build_lookup_executor

        records: list[LookupRecord] = []
        executor = build_lookup_executor(
            service, bundle_entity_ids=set(), on_lookup=records.append
        )
        payload = json.loads(executor(_call(tags={"theme": "guilt"})))
        assert "tags" in payload["error"]
        assert records[0].error  # L6: visible in the debug panel, not silent

    def test_unknown_entity_type_errors_instead_of_matching_nothing(
        self, tmp_path: Path
    ) -> None:
        # `search_entities` doesn't validate `entity_types` — it just filters,
        # so a plural/misspelled type quietly matches no source and the
        # narrator reads the empty result as "this doesn't exist". Name the
        # valid types so the model can correct itself.
        service, repo = _service(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["actor:npc:mira"])
        from dungeon_daddy.llm.lookup_tool import build_lookup_executor

        executor = build_lookup_executor(service, bundle_entity_ids=set())
        payload = json.loads(executor(_call(query="mira", entity_types=["actors"])))
        assert payload["results"] == []
        assert "actors" in payload["error"]
        assert "actor" in payload["error"]  # the valid types are listed

    def test_valid_entity_types_match_the_repository_sources(self) -> None:
        # Drift guard: the tool's advertised vocabulary is hand-maintained
        # against `_ENTITY_SOURCES` + the dedicated memory branch. If a source
        # is added and this set isn't updated, the new type is rejected at the
        # boundary and the table is unreachable through the tool.
        from dungeon_daddy.llm.lookup_tool import VALID_ENTITY_TYPES
        from dungeon_daddy.memory.repository import _ENTITY_SOURCES

        assert VALID_ENTITY_TYPES == {s.entity_type for s in _ENTITY_SOURCES} | {"memory"}

    def test_tool_description_advertises_the_valid_entity_types(self) -> None:
        from dungeon_daddy.llm.lookup_tool import LOOKUP_WORLD_TOOL, VALID_ENTITY_TYPES

        described = LOOKUP_WORLD_TOOL.parameters["properties"]["entity_types"]["description"]
        for entity_type in VALID_ENTITY_TYPES:
            assert entity_type in described

    def test_non_dict_arguments_do_not_raise(self, tmp_path: Path) -> None:
        # A provider can hand back a JSON array: `json.loads("[1,2]")` parses
        # fine, and `.get` on it would be an AttributeError through the turn.
        service, _ = _service(tmp_path)
        from dungeon_daddy.llm.lookup_tool import build_lookup_executor

        executor = build_lookup_executor(service, bundle_entity_ids=set())
        call = LLMToolCall(call_id="c1", name="lookup_world", arguments=[1, 2])  # type: ignore[arg-type]
        payload = json.loads(executor(call))
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
