"""Populate Level 1 of "The Crucible" save with items, objects, monsters & NPCs.

Senior-design content pass over the five rooms of Level 1 (a sand-choked Dwarven
artificer citadel patrolled by reactivated, insane golems and mechanical
scorpions). Threats are calibrated low for early-game adventurers; the locked
R2->R4 lift door is given a findable key in the Marketplace (R2), matching the
dungeon's own design note ("key obtained in Marketplace").

Idempotent: stable ids + repository upserts, so re-running just refreshes the
same content. Close the app first (DuckDB is single-writer).

Run:  python -m tools.populate_crucible_level1
"""
from __future__ import annotations

import os
from pathlib import Path

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import Item, ObjectTransition, RoomObject

CAMPAIGN_ID = "campaign:the-crucible"
LEVEL_ID = "level:1"

# Existing seeded monsters we place into rooms (rather than spawn duplicates).
SCORPION_SWARM_ID = "89999c99-4370-510a-9571-9ecc4270d4bf"
GOLEM_A7_ID = "a15f3370-3e37-526b-894c-a9de1fba21d9"


def _save_path() -> Path:
    base = Path(os.environ["LOCALAPPDATA"]) / "DungeonDaddy" / "saves" / "The Crucible"
    return base / "campaign.duckdb"


def _oid(room: str, slug: str) -> str:
    return f"object:the-crucible:{room}:{slug}"


def _iid(room: str, slug: str) -> str:
    return f"item:the-crucible:{room}:{slug}"


def _aid(room: str, slug: str) -> str:
    return f"actor:the-crucible:{room}:{slug}"


def _t(obj_id: str, n: int, frm: str, to: str, trigger: str, **kw) -> ObjectTransition:
    return ObjectTransition(
        transition_id=f"transition:the-crucible:{obj_id.split(':')[-1]}:{n}",
        object_id=obj_id, from_state=frm, to_state=to, trigger=trigger, **kw,
    )


def _obj(room, slug, name, archetype, state, desc, transitions) -> RoomObject:
    oid = _oid(room, slug)
    return RoomObject(
        object_id=oid, campaign_id=CAMPAIGN_ID, room_id=room, level_id=LEVEL_ID,
        slug=slug, display_name=name, archetype=archetype, description=desc,
        current_state=state, transitions=transitions,
    )


def _item(room, slug, name, desc) -> Item:
    iid = _iid(room, slug)
    return Item(
        item_id=iid, campaign_id=CAMPAIGN_ID, slug=slug, display_name=name,
        item_type="dungeon_item", description=desc, room_id=room, level_id=LEVEL_ID,
        status="active",
    )


def _objects() -> list[RoomObject]:
    out: list[RoomObject] = []

    # --- R1 Receiving Hall ---------------------------------------------------
    o = _oid("R1", "toppled-statue")
    out.append(_obj(
        "R1", "toppled-statue", "Toppled Artificer Statue", "lore_fixture", "intact",
        "A fallen granite figure of a hooded Dwarven artificer, one bronze hand still "
        "raised as if mid-command. Drifted sand half-buries the worn dedication plate.",
        [_t(o, 1, "intact", "examined", "examine")],
    ))
    o = _oid("R1", "supply-locker")
    out.append(_obj(
        "R1", "supply-locker", "Half-Buried Supply Locker", "container", "closed",
        "A dented iron locker leans out of a sand drift near the entry arch, its latch "
        "crusted but workable.",
        [_t(o, 1, "closed", "open", "open"),
         _t(o, 2, "closed", "open", "force")],
    ))

    # --- R2 Marketplace ------------------------------------------------------
    o = _oid("R2", "market-stall")
    out.append(_obj(
        "R2", "market-stall", "Collapsed Market Stall", "container", "closed",
        "A caved-in trade stall of rune-etched planks. Goods spill from a strongbox "
        "wedged beneath the counter, its lid sprung loose.",
        [_t(o, 1, "closed", "open", "open"),
         _t(o, 2, "closed", "open", "force")],
    ))
    o = _oid("R2", "notice-board")
    out.append(_obj(
        "R2", "notice-board", "Warden's Notice Board", "lore_fixture", "legible",
        "A scorched bronze board still bolted to a pillar. Beneath faded trade notices, "
        "the warden's last standing order is still legible: 'By my hand — the lift-key "
        "stays at the watch-stall here in the market until the core is secured. None "
        "take the cage down without it. — Warden Brakkus'",
        [_t(o, 1, "legible", "examined", "examine")],
    ))

    # --- R3 Cargo Bay --------------------------------------------------------
    o = _oid("R3", "cargo-crate")
    out.append(_obj(
        "R3", "cargo-crate", "Sealed Dwarven Cargo Crate", "container", "sealed",
        "A heavy crate banded in cold iron, stencilled with the hold's anvil sigil. "
        "The seal is intact but brittle with age.",
        [_t(o, 1, "sealed", "open", "force"),
         _t(o, 2, "sealed", "open", "open")],
    ))
    o = _oid("R3", "manifest-terminal")
    out.append(_obj(
        "R3", "manifest-terminal", "Cargo Manifest Terminal", "lore_fixture", "dim",
        "A dust-filmed crystal panel that flickers when brushed. Its last manifest "
        "scrolls past: the power core was being moved to the lower vault when the "
        "golems turned.",
        [_t(o, 1, "dim", "examined", "examine")],
    ))

    # --- R4 Elevator Shaft ---------------------------------------------------
    o = _oid("R4", "great-lift")
    out.append(_obj(
        "R4", "great-lift", "The Great Lift", "mechanism", "unpowered",
        "A cage of dwarven brass straddling a shaft that plunges into darkness. Its "
        "control podium is dead — a fuse slot gapes empty where a power cell should sit.",
        [_t(o, 1, "unpowered", "powered", "activate", requires_item_slug="lift-fuse")],
    ))
    o = _oid("R4", "gearworks")
    out.append(_obj(
        "R4", "gearworks", "Sand-Choked Gearworks", "structure", "jammed",
        "The lift's drive gears, packed solid with red sand. Clearing them by hand "
        "would be slow, loud work.",
        [_t(o, 1, "jammed", "cleared", "force")],
    ))

    # --- R5 Trap Room --------------------------------------------------------
    o = _oid("R5", "spike-plates")
    out.append(_obj(
        "R5", "spike-plates", "Spring-Spike Floor Plates", "trap", "armed",
        "A grid of subtly raised floor plates. Pressure springs beneath glint with "
        "oiled spikes, primed to drive upward.",
        [_t(o, 1, "armed", "disarmed", "disarm"),
         _t(o, 2, "armed", "sprung", "trigger")],
    ))
    o = _oid("R5", "dart-vents")
    out.append(_obj(
        "R5", "dart-vents", "Dart-Wall Vents", "trap", "armed",
        "Rows of finger-width holes line the walls at chest height, each loaded with "
        "a needle dart behind a hair-trigger reed.",
        [_t(o, 1, "armed", "disarmed", "disarm"),
         _t(o, 2, "armed", "sprung", "trigger")],
    ))
    o = _oid("R5", "trap-lever")
    out.append(_obj(
        "R5", "trap-lever", "Trap Control Lever", "mechanism", "active",
        "A wall lever stamped with the warden's sigil, set behind a grille at the far "
        "end of the room. Thrown, it cuts power to the chamber's traps.",
        [_t(o, 1, "active", "disabled", "toggle")],
    ))
    return out


def _items() -> list[Item]:
    return [
        # R1 — lore + a breadcrumb pointing at the Marketplace key.
        _item("R1", "travel-journal", "Sun-Bleached Travel Journal",
              "A dead scavenger's journal. The last entry: 'Lift's locked tight. "
              "Warden's key never left the market stalls — but the scorpions own them now.'"),
        # R2 — THE KEY (findable per request) + modest loot.
        _item("R2", "lift-warden-key", "Lift Warden's Iron Key",
              "A heavy iron key on a brass fob stamped with a descending-cage sigil. "
              "It fits the locked lift door between the Marketplace and the Elevator Shaft."),
        _item("R2", "healing-draught", "Dwarven Healing Draught",
              "A squat blue vial of resin-sealed tonic. Still good — one solid swallow "
              "of restorative dwarven brew."),
        _item("R2", "trade-coins", "Tarnished Trade-Coins",
              "A fistful of square dwarven trade-coins, blackened but solid silver beneath."),
        # R3 — utility + the fuse that powers the R4 lift.
        _item("R3", "lift-fuse", "Lift Power Fuse",
              "A palm-sized brass power cell humming faintly with stored charge. Sized to "
              "seat in a lift control podium."),
        _item("R3", "dwarven-rope", "Coil of Dwarven Rope",
              "Forty feet of fine silk-and-wire rope, light and strong, wound on a horn spool."),
        # R5 — reward for braving the trap room.
        _item("R5", "trap-spanner", "Artificer's Trap-Spanner",
              "A finely machined multi-tool of dwarven make, its jaws shaped for prising "
              "open mechanisms and stilling triggers."),
    ]


def main() -> None:
    db = _save_path()
    if not db.exists():
        raise SystemExit(f"Save DB not found: {db}")
    repo = MemoryRepository(db)
    try:
        # Objects
        objects = _objects()
        for obj in objects:
            repo.save_room_object(obj)
        # Items
        items = _items()
        for it in items:
            repo.save_item(it)
        # NPC — a still-sane caretaker construct sheltering in the Cargo Bay.
        repo.save_actor(
            _aid("R3", "pinion-caretaker"), CAMPAIGN_ID, "npc", "pinion-caretaker",
            "Pinion, the Caretaker Cog", status="active",
            tags=["construct", "friendly", "lore"], room_id="R3",
        )
        # Monsters — new room-specific threats.
        repo.save_actor(
            _aid("R2", "iron-scorpions"), CAMPAIGN_ID, "monster", "iron-scorpions",
            "Skittering Iron Scorpions", status="active",
            tags=["construct", "swarm"], room_id="R2",
        )
        repo.save_actor(
            _aid("R5", "sweeper-drone"), CAMPAIGN_ID, "monster", "sweeper-drone",
            "Malfunctioning Sweeper Drone", status="active",
            tags=["construct", "damaged"], room_id="R5",
        )
        # Monsters — place existing seeded constructs into fitting rooms.
        repo._conn.execute(  # type: ignore[union-attr]
            "UPDATE actors SET room_id = ? WHERE actor_id = ?", ["R1", SCORPION_SWARM_ID])
        repo._conn.execute(  # type: ignore[union-attr]
            "UPDATE actors SET room_id = ? WHERE actor_id = ?", ["R4", GOLEM_A7_ID])

        print(f"Populated Level 1 of The Crucible at {db}")
        print(f"  objects: {len(objects)}   loose items: {len(items)}")
        print("  monsters: R1 Scorpion Swarm, R2 Iron Scorpions, R4 Golem A-7, "
              "R5 Sweeper Drone")
        print("  npc:      R3 Pinion, the Caretaker Cog")
        print("  KEY:      'Lift Warden's Iron Key' placed in R2 (Marketplace)")
    finally:
        repo.close()


if __name__ == "__main__":
    main()
