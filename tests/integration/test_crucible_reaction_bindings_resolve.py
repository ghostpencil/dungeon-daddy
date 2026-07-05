"""Integration guard: every authored Crucible scripted CLOCK binding resolves
to a live, adverse clock.

Phase 51.6 hardening (review Gap #1 + silent-failure #1): a scripted binding's
``clock_slug`` is authored in the populate scripts, but the target clock is
created by a *different* path — ``apply_seed_pack``, which writes uuid5 ids
(``derive_clock_id``). A rename or typo on either side makes the binding
silently no-op on the real save — the exact class the ``f5ab7b1`` uuid5-resolution
fix addressed, and which the unit tests only cover with a hand-built id. This
test seeds the Crucible for real (seed pack + both populate scripts), reads the
bindings back through the repo, and pins that each CLOCK binding resolves to an
active, adverse clock. Real ``MemoryRepository`` on ``tmp_path``; no mocks.
"""
from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import (
    ClockState,
    RoomObject,
    is_adverse,
    normalize_clock_category,
)
from dungeon_daddy.rpg.seed_pack import apply_seed_pack, load_seed_pack
from dungeon_daddy.rpg.world_reaction import _find_clock_by_slug
from tools.populate_crucible_dungeon_channel import seed_dungeon_channel
from tools.populate_crucible_level1 import (
    CAMPAIGN_ID,
    _objects,
    save_objects_preserving_state,
)

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")
_SEED_PACK = Path("seed_data/campaigns/the-crucible/rpg_seed.json")


def _clock_state(row: dict) -> ClockState:
    # Mirror play_view._apply_world_reaction's dict → ClockState mapping so the
    # test resolves clocks exactly as the engine does at play time.
    return ClockState(
        clock_id=row["clock_id"],
        campaign_id=row["campaign_id"],
        label=row["label"],
        segments=row["segments"],
        filled=row["filled"],
        status=row["status"],
        scope_room_id=row.get("scope_room_id"),
        action_tags=row.get("action_tags", []),
        clock_level=row.get("clock_level", "dungeon"),
        category=row.get("category"),
        level_id=row.get("level_id"),
    )


@pytest.fixture
def seeded_repo(tmp_path: Path):
    repo = MemoryRepository(tmp_path / "campaign.duckdb")
    repo.initialize_schema(_MIGRATIONS_DIR)
    repo.save_campaign(
        campaign_id=CAMPAIGN_ID,
        slug="the-crucible",
        title="The Crucible",
        dungeon_slug="the-crucible",
    )
    # Clocks (uuid5 ids) first, then the objects + bindings that reference them.
    apply_seed_pack(load_seed_pack(_SEED_PACK), CAMPAIGN_ID, repo, _MIGRATIONS_DIR)
    save_objects_preserving_state(repo, _objects())
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    yield repo
    repo.close()


def test_every_scripted_clock_binding_resolves_to_an_active_adverse_clock(seeded_repo):
    clocks = [_clock_state(c) for c in seeded_repo.get_clocks(CAMPAIGN_ID)]
    objects = [
        RoomObject(**d) for d in seeded_repo.get_objects_for_campaign(CAMPAIGN_ID)
    ]
    clock_bindings = [
        (obj, b)
        for obj in objects
        for b in obj.reaction_bindings
        if b.clock_slug is not None
    ]
    assert clock_bindings, "expected the Crucible seed to author scripted CLOCK bindings"

    for obj, b in clock_bindings:
        clock = _find_clock_by_slug(clocks, b.clock_slug)
        assert clock is not None, (
            f"{obj.slug} binding {b.binding_id} names clock slug {b.clock_slug!r} "
            "that resolves to no live clock — it would silently no-op on the save"
        )
        assert clock.status == "active", (
            f"{obj.slug} binding targets non-active clock {b.clock_slug!r}"
        )
        assert is_adverse(normalize_clock_category(clock.category)), (
            f"{obj.slug} binding targets non-adverse clock {b.clock_slug!r} "
            f"(category={clock.category!r}) — it can never fire"
        )
