"""Minimal Level 2 population for "The Crucible" — Great Lift return only.

Seeds the upper Great Lift landing in r01 (Entry Chamber, Level 2) so the party
can descend back to Level 1 (R4) after arriving via the Great Lift from below.

Idempotent: re-running refreshes the same content. Close the app first.

Run:  python -m tools.populate_crucible_level2
"""
from __future__ import annotations

import os
from pathlib import Path

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import ObjectTransition, RoomExit, RoomObject

CAMPAIGN_ID = "campaign:the-crucible"
LEVEL_ID = "level:2"  # 1-based level ID for data scoping
# Taxonomy scope tag (A4 §4.4) — the `level:` tag uses the level-<n> convention
# (matches actor/memory tags + retrieval), deliberately NOT the DB level_id above.
LEVEL_TAG = "level:level-2"


def _save_path() -> Path:
    base = Path(os.environ["LOCALAPPDATA"]) / "DungeonDaddy" / "saves" / "The Crucible"
    return base / "campaign.duckdb"


def _great_lift_upper() -> RoomObject:
    oid = "object:the-crucible:r01:great-lift-upper"
    return RoomObject(
        object_id=oid,
        campaign_id=CAMPAIGN_ID,
        room_id="r01",
        level_id=LEVEL_ID,
        slug="great-lift-upper",
        display_name="Great Lift",
        # Scenery, not a subsystem: the Great Lift is one physical object, modelled
        # once as the load-bearing mechanism on Level 1 (R4) that gates the vertical
        # exit. This upper landing is only its presence at the top of the shaft, so it
        # must not appear as a second reported subsystem in the dungeon's systems status.
        archetype="lore_fixture",
        description=(
            "The upper landing of the Great Lift — the same dwarven brass cage whose "
            "control podium stands on the floor below. Whether it will carry you depends "
            "on the lift's condition there."
        ),
        current_state="present",
        transitions=[
            ObjectTransition(
                transition_id="transition:the-crucible:great-lift-upper:1",
                object_id=oid,
                from_state="present",
                to_state="present",
                trigger="examine",
                contested=False,
            ),
        ],
        # A4 §4.4: identity + scope + the power-core thread it gates.
        tags=["object:great-lift-upper", LEVEL_TAG, "thread:power-core"],
    )


def _lift_return_exit() -> RoomExit:
    return RoomExit(
        exit_id="exit:the-crucible:r01:R4",
        campaign_id=CAMPAIGN_ID,
        from_room_id="r01",
        to_room_id="R4",
        level_id=LEVEL_ID,
        connector_type="vertical",
        to_level_id="level:0",  # 0-based index: levels[0] = Level 1
        label="Great Lift",
        exit_type="vertical",
        status="open",
    )


# Room lore tags (Slice B0 §7.1): connect each Level-2 room to the theme/thread
# lore memories that share these slugs, so `lookup_world` and the T7 pre-fetch
# surface a room's lore. The base seed plants each room's summary + derived
# quest_role; this only enriches the tags. Reuses the canonical A4 vocabulary.
_ROOM_TAGS: dict[str, list[str]] = {
    "r01": ["thread:power-core"],
    "r02": ["thread:power-core"],
    "r03": ["thread:power-core"],
    "r04": ["thread:power-core", "theme:mystery"],
    "r05": ["theme:hazard"],
    "r06": ["theme:history"],
}


def save_room_tags(repo: MemoryRepository) -> int:
    """Enrich Level-2 base-seeded rooms with the authored lore tags (idempotent).
    Thin wrapper over the shared :func:`enrich_room_tags`."""
    from dungeon_daddy.rpg.seed_pack import enrich_room_tags

    return enrich_room_tags(repo, CAMPAIGN_ID, _ROOM_TAGS)


def main() -> None:
    db = _save_path()
    if not db.exists():
        raise SystemExit(f"Save DB not found: {db}")
    repo = MemoryRepository(db)
    rooms_tagged = save_room_tags(repo)
    repo.save_room_object(_great_lift_upper())
    repo.save_room_exit(_lift_return_exit())
    print(f"Populated Level 2 of The Crucible at {db}")
    print(f"  rooms tagged: {rooms_tagged}")
    print("  objects: Great Lift upper landing in r01 (lore_fixture scenery)")
    print("  exits:   r01->R4 Great Lift return (connector=vertical, open)")


if __name__ == "__main__":
    main()
