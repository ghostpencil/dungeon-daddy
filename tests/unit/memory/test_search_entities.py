"""Slice B1 — MemoryRepository.search_entities (narrator-lookup backend).

Tracer-bullet TDD (spec/TESTING.md): one behavior per cycle. search_entities
unions the campaign's entity tables (actors/objects/items/clocks/objectives/
factions/rooms/memories), matching a case-insensitive substring query on
slug/display_name and/or exact tag membership, and returns normalized rows
`{entity_type, id, slug, display_name, room_id, tags, snippet}`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import (
    FactionState,
    Item,
    Objective,
    ObjectiveCompletion,
    RoomObject,
    RoomState,
)

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[3]
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


def _repo(tmp_path: Path) -> MemoryRepository:
    repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
    repo.initialize_schema(MIGRATIONS_DIR)
    return repo


def _one(results: list[dict]) -> dict:
    assert len(results) == 1, f"expected exactly one result, got {results}"
    return results[0]


class TestSearchEntitiesValidation:
    def test_requires_query_or_tags(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        with pytest.raises(ValueError):
            repo.search_entities("camp-A")

    def test_empty_tags_without_query_also_raises(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        with pytest.raises(ValueError):
            repo.search_entities("camp-A", tags=[])


class TestSearchEntitiesQuery:
    def test_query_matches_actor_by_display_name(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_actor(
            "actor:c:mira", "camp-A", "npc", "mira-coldwell", "Mira Coldwell",
            tags=["actor:npc:mira-coldwell"],
        )
        results = repo.search_entities("camp-A", query="mira")
        assert len(results) == 1
        row = results[0]
        assert row["entity_type"] == "actor"
        assert row["id"] == "actor:c:mira"
        assert row["slug"] == "mira-coldwell"
        assert row["display_name"] == "Mira Coldwell"
        assert row["room_id"] is None
        assert row["tags"] == ["actor:npc:mira-coldwell"]

    def test_query_is_case_insensitive(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira-coldwell", "Mira Coldwell")
        # Uppercase query still matches a lowercase slug / mixed-case name.
        assert len(repo.search_entities("camp-A", query="MIRA")) == 1
        assert len(repo.search_entities("camp-A", query="coLDweLL")) == 1

    def test_query_no_match_returns_empty(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira-coldwell", "Mira Coldwell")
        assert repo.search_entities("camp-A", query="dragon") == []


class TestSearchEntitiesTags:
    def test_tags_match_by_exact_membership(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["theme:guilt"])
        repo.save_actor("a2", "camp-A", "npc", "tom", "Tom", tags=["theme:hope"])
        results = repo.search_entities("camp-A", tags=["theme:guilt"])
        assert [r["id"] for r in results] == ["a1"]

    def test_tags_are_or_semantics(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["theme:guilt"])
        repo.save_actor("a2", "camp-A", "npc", "tom", "Tom", tags=["theme:hope"])
        repo.save_actor("a3", "camp-A", "npc", "sal", "Sal", tags=["trait:boss"])
        results = repo.search_entities("camp-A", tags=["theme:guilt", "theme:hope"])
        assert {r["id"] for r in results} == {"a1", "a2"}

    def test_query_or_tags_union(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", tags=["theme:guilt"])
        repo.save_actor("a2", "camp-A", "npc", "dragon", "Dragon", tags=["theme:hope"])
        # Row matches when it hits the query OR carries a requested tag.
        results = repo.search_entities("camp-A", query="mira", tags=["theme:hope"])
        assert {r["id"] for r in results} == {"a1", "a2"}


class TestSearchEntitiesFilters:
    def test_entity_types_includes_matching_type(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira")
        assert len(repo.search_entities("camp-A", query="mira", entity_types=["actor"])) == 1

    def test_entity_types_excludes_other_types(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira")
        assert repo.search_entities("camp-A", query="mira", entity_types=["object"]) == []

    def test_empty_entity_types_means_no_filter(self, tmp_path: Path) -> None:
        # An empty list is a plausible "unset filter" serialization; it must
        # not silently match nothing (would surface as "world is empty").
        repo = _repo(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira")
        repo.save_memory_entry(
            "m1", "camp-A", "lore", "Mira's past", status="approved"
        )
        results = repo.search_entities("camp-A", query="mira", entity_types=[])
        assert {r["id"] for r in results} == {"a1", "m1"}

    def test_limit_defaults_to_eight(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        for i in range(12):
            repo.save_actor(f"a{i}", "camp-A", "npc", f"guard-{i}", f"Guard {i}")
        assert len(repo.search_entities("camp-A", query="guard")) == 8

    def test_limit_is_honored(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        for i in range(12):
            repo.save_actor(f"a{i}", "camp-A", "npc", f"guard-{i}", f"Guard {i}")
        assert len(repo.search_entities("camp-A", query="guard", limit=3)) == 3

    def test_limit_caps_at_twenty(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        for i in range(25):
            repo.save_actor(f"a{i}", "camp-A", "npc", f"guard-{i}", f"Guard {i}")
        assert len(repo.search_entities("camp-A", query="guard", limit=100)) == 20


class TestSearchEntitiesTables:
    """Each entity table is union'd with the correct column mapping."""

    def test_finds_room_object_with_description_snippet(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_room_object(
            RoomObject(
                object_id="obj:1", campaign_id="camp-A", room_id="R1", level_id="level:0",
                slug="brass-lift", display_name="Brass Lift", archetype="lore_fixture",
                description="A dwarven brass cage.", current_state="present",
                tags=["object:brass-lift"],
            )
        )
        row = _one(repo.search_entities("camp-A", query="lift"))
        assert row["entity_type"] == "object"
        assert row["id"] == "obj:1"
        assert row["room_id"] == "R1"
        assert row["snippet"] == "A dwarven brass cage."

    def test_finds_item_by_tag(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_item(
            Item(
                item_id="item:1", campaign_id="camp-A", slug="journal",
                display_name="Travel Journal", item_type="dungeon_item",
                description="Water-stained pages.", room_id="R1", tags=["item:journal"],
            )
        )
        row = _one(repo.search_entities("camp-A", tags=["item:journal"]))
        assert row["entity_type"] == "item"
        assert row["id"] == "item:1"
        assert row["snippet"] == "Water-stained pages."

    def test_finds_clock_by_label_no_slug(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_clock(
            "clock:1", "camp-A", "Power Core Meltdown", 6,
            scope_room_id="R4", stakes="The factory explodes.", tags=["thread:power-core"],
        )
        row = _one(repo.search_entities("camp-A", query="meltdown"))
        assert row["entity_type"] == "clock"
        assert row["slug"] is None
        assert row["display_name"] == "Power Core Meltdown"
        assert row["room_id"] == "R4"
        assert row["snippet"] == "The factory explodes."

    def test_finds_objective_by_title(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_objective(
            Objective(
                objective_id="obj:q1", campaign_id="camp-A", slug="reach-core",
                title="Reach the Power Core", description="Descend to the reactor.",
                tier_index=0, completion=ObjectiveCompletion(kind="room_reached", target_slug="R4"),
                tags=["quest:main"],
            )
        )
        row = _one(repo.search_entities("camp-A", query="power core"))
        assert row["entity_type"] == "objective"
        assert row["room_id"] is None
        assert row["snippet"] == "Descend to the reactor."

    def test_finds_faction_with_concept_snippet(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_faction(
            FactionState(
                faction_id="fac:1", campaign_id="camp-A", slug="iron-guild",
                display_name="Iron Guild", concept="Dwarven smiths.", tags=["faction:iron-guild"],
            )
        )
        row = _one(repo.search_entities("camp-A", query="iron"))
        assert row["entity_type"] == "faction"
        assert row["snippet"] == "Dwarven smiths."

    def test_finds_room_with_summary_snippet(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_room(
            RoomState(
                room_id="R4", campaign_id="camp-A", level_id="level:0", slug="great-lift",
                display_name="Great Lift", room_type="chamber",
                summary="A vertical shaft.", tags=["thread:power-core"],
            )
        )
        row = _one(repo.search_entities("camp-A", query="great lift"))
        assert row["entity_type"] == "room"
        assert row["id"] == "R4"
        assert row["room_id"] == "R4"
        assert row["snippet"] == "A vertical shaft."


class TestSearchEntitiesMemory:
    def test_finds_memory_by_title(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_memory_entry(
            "mem:1", "camp-A", "lore", "The Power Core Is Destabilizing",
            summary="It hums louder each day.", status="approved", importance=8,
        )
        row = _one(repo.search_entities("camp-A", query="power core"))
        assert row["entity_type"] == "memory"
        assert row["id"] == "mem:1"
        assert row["slug"] is None
        assert row["display_name"] == "The Power Core Is Destabilizing"
        assert row["room_id"] is None
        assert row["snippet"] == "It hums louder each day."

    def test_finds_memory_by_tag(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_memory_entry(
            "mem:1", "camp-A", "lore", "Power Core", status="approved",
        )
        repo.add_memory_tag("mem:1", "thread:power-core")
        row = _one(repo.search_entities("camp-A", tags=["thread:power-core"]))
        assert row["id"] == "mem:1"
        assert row["tags"] == ["thread:power-core"]

    def test_unapproved_memory_is_not_returned(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        # Default status is "draft" — a lookup must not surface unapproved lore.
        repo.save_memory_entry("mem:1", "camp-A", "lore", "Power Core Secret")
        assert repo.search_entities("camp-A", query="power core") == []

    def test_memory_excluded_by_entity_types(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_memory_entry(
            "mem:1", "camp-A", "lore", "Power Core", status="approved",
        )
        assert repo.search_entities(
            "camp-A", query="power", entity_types=["actor"]
        ) == []


class TestSearchEntitiesRanking:
    def test_exact_slug_match_ranks_first(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        # Both match the substring "core"; only a2's slug equals it exactly.
        repo.save_actor("a1", "camp-A", "npc", "core-guardian", "Core Guardian")
        repo.save_actor("a2", "camp-A", "npc", "core", "The Core")
        results = repo.search_entities("camp-A", query="core")
        assert [r["id"] for r in results] == ["a2", "a1"]

    def test_higher_tag_hit_count_ranks_first(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "one", "One", tags=["theme:guilt"])
        repo.save_actor(
            "a2", "camp-A", "npc", "two", "Two", tags=["theme:guilt", "theme:hope"]
        )
        results = repo.search_entities("camp-A", tags=["theme:guilt", "theme:hope"])
        assert [r["id"] for r in results] == ["a2", "a1"]

    def test_memories_ranked_by_importance(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_memory_entry(
            "m-low", "camp-A", "lore", "Core note", status="approved", importance=3
        )
        repo.save_memory_entry(
            "m-high", "camp-A", "lore", "Core alarm", status="approved", importance=9
        )
        results = repo.search_entities("camp-A", query="core")
        assert [r["id"] for r in results] == ["m-high", "m-low"]

    def test_ranking_applied_before_limit(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "core-guardian", "Core Guardian")
        repo.save_actor("a2", "camp-A", "npc", "core", "The Core")
        # The exact-slug match survives a limit of 1.
        results = repo.search_entities("camp-A", query="core", limit=1)
        assert [r["id"] for r in results] == ["a2"]

    def test_memory_importance_does_not_outrank_tied_entity(self, tmp_path: Path) -> None:
        # Both match "core" by substring only (tie on exact_slug=0, tag_hits=0).
        # Importance orders memories among themselves but must NOT push the
        # non-memory entity below a high-importance memory (owner ruling).
        repo = _repo(tmp_path)
        repo.save_faction(
            FactionState(
                faction_id="f1", campaign_id="camp-A", slug="core-guild",
                display_name="Core Guild",
            )
        )
        repo.save_memory_entry(
            "m1", "camp-A", "lore", "Core lore", status="approved", importance=9
        )
        results = repo.search_entities("camp-A", query="core")
        assert [r["entity_type"] for r in results] == ["faction", "memory"]


class TestSearchEntitiesStatus:
    """Each row carries the entity's status so the narrator can tell a live
    entity from a defunct one (owner ruling 2026-07-12)."""

    def test_actor_status_surfaces(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira", status="dead")
        assert _one(repo.search_entities("camp-A", query="mira"))["status"] == "dead"

    def test_object_status_is_current_state(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_room_object(
            RoomObject(
                object_id="o1", campaign_id="camp-A", room_id="R1", level_id="level:0",
                slug="hatch", display_name="Hatch", archetype="lore_fixture",
                description="A hatch.", current_state="open",
            )
        )
        assert _one(repo.search_entities("camp-A", query="hatch"))["status"] == "open"

    def test_room_status_is_none(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_room(
            RoomState(
                room_id="R4", campaign_id="camp-A", level_id="level:0", slug="lift",
                display_name="Lift", room_type="chamber",
            )
        )
        assert _one(repo.search_entities("camp-A", query="lift"))["status"] is None

    def test_memory_status_is_approved(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_memory_entry("m1", "camp-A", "lore", "Core", status="approved")
        assert _one(repo.search_entities("camp-A", query="core"))["status"] == "approved"


class TestSearchEntitiesScoping:
    def test_other_campaign_entities_excluded(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_actor("a1", "camp-A", "npc", "mira", "Mira")
        repo.save_actor("a2", "camp-B", "npc", "mira", "Mira")
        results = repo.search_entities("camp-A", query="mira")
        assert [r["id"] for r in results] == ["a1"]

    def test_memory_is_campaign_scoped(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.save_memory_entry("m1", "camp-A", "lore", "Core", status="approved")
        repo.save_memory_entry("m2", "camp-B", "lore", "Core", status="approved")
        results = repo.search_entities("camp-A", query="core")
        assert [r["id"] for r in results] == ["m1"]


# ---------------------------------------------------------------------------
# Cleanup item 3 (Phase B review): the row shape is a TypedDict, pinned once
# here instead of drifting across three readers' docstrings.
# ---------------------------------------------------------------------------

def test_entity_row_type_names_the_documented_row_shape() -> None:
    from dungeon_daddy.memory.models import EntityRow

    assert set(EntityRow.__annotations__) == {
        "entity_type",
        "id",
        "slug",
        "display_name",
        "room_id",
        "status",
        "tags",
        "snippet",
    }
