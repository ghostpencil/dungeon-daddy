"""Tests for the Level 2 Crucible seed (`populate_crucible_level2`).

The Great Lift is one physical object that spans levels. It is modelled once as a
load-bearing ``mechanism`` on Level 1 (R4, the object that gates the vertical
exit). The Level 2 upper landing is a *scenery* presence only — it must not be a
second reported subsystem, or the dungeon's truthful systems assessment lists the
lift twice (and the LLM collapses the duplicate, dropping a state).
"""
from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.dungeon_channel import (
    SUBSYSTEM_ARCHETYPES,
    dungeon_systems_status,
)
from dungeon_daddy.rpg.models import RoomState
from tools.populate_crucible_level2 import (
    _ROOM_TAGS,
    CAMPAIGN_ID,
    _great_lift_upper,
    save_room_tags,
)

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")


def test_upper_landing_is_scenery_not_a_subsystem():
    upper = _great_lift_upper()
    assert upper.archetype not in SUBSYSTEM_ARCHETYPES


def test_upper_landing_drops_out_of_systems_status():
    upper = _great_lift_upper()
    obj = {
        "display_name": upper.display_name,
        "archetype": upper.archetype,
        "current_state": upper.current_state,
    }
    assert dungeon_systems_status([obj]) == []


def test_upper_landing_carries_canonical_taxonomy_tags():
    from dungeon_daddy.memory.tags import validate_tag

    upper = _great_lift_upper()
    assert upper.tags
    for t in upper.tags:
        validate_tag(t)
    assert "object:great-lift-upper" in upper.tags
    assert "level:level-2" in upper.tags


# --- Slice B0 §7.1: room lore-tag enrichment ------------------------------


@pytest.fixture
def repo(tmp_path: Path):
    r = MemoryRepository(tmp_path / "campaign.duckdb")
    r.initialize_schema(_MIGRATIONS_DIR)
    r.save_campaign(
        campaign_id=CAMPAIGN_ID,
        slug="the-crucible",
        title="The Crucible",
        dungeon_slug="the-crucible",
    )
    yield r
    r.close()


def _seed_base_room(repo, room_id, *, summary="base lore", quest_role="goal"):
    repo.save_room(RoomState(
        room_id=room_id, campaign_id=CAMPAIGN_ID, level_id="level:2",
        slug=room_id, display_name=room_id, room_type="chamber",
        summary=summary, quest_role=quest_role,
    ))


def test_room_tags_are_canonical():
    from dungeon_daddy.memory.tags import validate_tag
    for tags in _ROOM_TAGS.values():
        for t in tags:
            assert validate_tag(t) == t


def test_save_room_tags_enriches_base_room_preserving_summary_and_role(repo):
    _seed_base_room(repo, "r02", summary="Central Hub lore.", quest_role="goal")
    save_room_tags(repo)
    row = repo.get_room(CAMPAIGN_ID, "r02")
    assert set(row["tags"]) >= set(_ROOM_TAGS["r02"])
    assert row["summary"] == "Central Hub lore."
    assert row["quest_role"] == "goal"


def test_save_room_tags_skips_unseeded_room(repo):
    save_room_tags(repo)
    assert repo.get_rooms(CAMPAIGN_ID) == []
