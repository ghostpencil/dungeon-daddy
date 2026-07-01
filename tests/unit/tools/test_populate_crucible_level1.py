"""Tests for the Crucible Level-1 seed (`populate_crucible_level1`).

Phase 51.5 Part A Slice 4 focus: the tier-0 Sand-Choked Gearworks is an
*obstacle* — solvable by multiple class-flavored, contested approaches that all
converge on one resolved state — and reseeding is additive (it never resets a
subsystem the party has already changed). Real `MemoryRepository` on `tmp_path`,
no mocks.
"""
from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.obstacles import (
    obstacle_approach_verbs,
    obstacle_resolved_state,
)
from tools.populate_crucible_level1 import (
    CAMPAIGN_ID,
    _objects,
    _oid,
    save_objects_preserving_state,
)

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")

# The nine core action ratings — an approach verb must be one of these so an
# actor can actually attempt it.
_CORE_VERBS = {
    "fight", "endure", "move", "tinker", "study", "focus", "sway", "sense", "channel",
}


def _gearworks():
    return next(o for o in _objects() if o.slug == "gearworks")


def test_gearworks_is_a_contested_obstacle_converging_on_cleared():
    gear = _gearworks()
    assert gear.current_state == "jammed"
    verbs = obstacle_approach_verbs(gear)
    # Multiple class-flavored ways to clear it (thematic: tinker / fight / endure).
    assert len(verbs) >= 2
    assert set(verbs) <= _CORE_VERBS
    # All approaches converge on the one resolved state (#1 normalize completion).
    assert obstacle_resolved_state(gear) == "cleared"


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


def test_reseed_preserves_played_object_state(repo):
    save_objects_preserving_state(repo, _objects())
    gear_id = _oid("R4", "gearworks")
    repo.update_object_state(gear_id, "cleared")  # the party clears it

    save_objects_preserving_state(repo, _objects())  # additive reseed

    assert repo.get_room_object(gear_id)["current_state"] == "cleared"
