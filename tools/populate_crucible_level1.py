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
from dungeon_daddy.rpg.models import (
    Item,
    ObjectReactionBinding,
    ObjectTransition,
    RoomExit,
    RoomObject,
)

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


def _rb(obj_id: str, verb: str, outcome: str, **kw) -> ObjectReactionBinding:
    """A scripted world-reaction binding (Phase 51.6 §5) for ``obj_id``."""
    return ObjectReactionBinding(
        binding_id=f"binding:the-crucible:{obj_id.split(':')[-1]}:{verb}:{outcome}",
        object_id=obj_id, action_verb=verb, outcome=outcome, **kw,
    )


def _obj(
    room, slug, name, archetype, state, desc, transitions,
    *, policy: str = "ambient", bindings=None,
) -> RoomObject:
    oid = _oid(room, slug)
    return RoomObject(
        object_id=oid, campaign_id=CAMPAIGN_ID, room_id=room, level_id=LEVEL_ID,
        slug=slug, display_name=name, archetype=archetype, description=desc,
        current_state=state, transitions=transitions,
        reaction_policy=policy, reaction_bindings=bindings or [],
    )


def _item(room, slug, name, desc, *, placed: bool = True) -> Item:
    """Author a Level-1 item.

    ``placed`` (default) drops it loose in ``room``. Pass ``placed=False`` for
    *container loot*: an unplaced, inert item (no room, no owner) that a
    container's ``spawns_item_slug`` transition reveals into the room on open.
    """
    iid = _iid(room, slug)
    return Item(
        item_id=iid, campaign_id=CAMPAIGN_ID, slug=slug, display_name=name,
        item_type="dungeon_item", description=desc,
        room_id=room if placed else None, level_id=LEVEL_ID,
        status="active" if placed else "inert",
    )


def _lift_exits() -> list[RoomExit]:
    return [
        RoomExit(
            exit_id="exit:the-crucible:R2:R4",
            campaign_id=CAMPAIGN_ID,
            from_room_id="R2",
            to_room_id="R4",
            level_id=LEVEL_ID,
            label="Door",
            status="open",
            requires_item_slug="lift-warden-key",
        ),
        RoomExit(
            exit_id="exit:the-crucible:R4:R2",
            campaign_id=CAMPAIGN_ID,
            from_room_id="R4",
            to_room_id="R2",
            level_id=LEVEL_ID,
            label="Door",
            status="open",
        ),
        RoomExit(
            exit_id="exit:the-crucible:R4:L2",
            campaign_id=CAMPAIGN_ID,
            from_room_id="R4",
            to_room_id="r01",
            level_id=LEVEL_ID,
            connector_type="vertical",
            to_level_id="level:1",  # 0-based list index: levels[1] = Level 2 (Factory Floor)
            label="Great Lift",
            exit_type="vertical",
            status="open",
            requires_object_id="object:the-crucible:R4:great-lift",
            requires_object_state="powered",
        ),
    ]


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
        # Opening or forcing it reveals the travel journal stowed inside (rewards
        # curiosity — the journal is no longer loose in the room).
        [_t(o, 1, "closed", "open", "open", spawns_item_slug="travel-journal"),
         _t(o, 2, "closed", "open", "force", spawns_item_slug="travel-journal")],
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
        # Mission gate (§6, scripted): mishandling its arcane power feeds the
        # Overload clock — no more miss fan-out across unrelated campaign clocks.
        policy="scripted",
        bindings=[_rb(o, "*", "miss", clock_slug="arcane-overload-building", clock_delta=1)],
    ))
    o = _oid("R4", "gearworks")
    out.append(_obj(
        "R4", "gearworks", "Sand-Choked Gearworks", "structure", "jammed",
        "The lift's drive gears, packed solid with red sand. They can be freed by "
        "careful mechanism-work, by brute force, or by slow, grinding hand-labor.",
        # Obstacle: three class-flavored contested approaches converging on 'cleared'
        # (Phase 51.5 Part A — Artificer/Thief tinker, Fighter strong blow, dogged
        # endurance). All to the same state so the objective completes uniformly.
        [_t(o, 1, "jammed", "cleared", "tinker", contested=True, action_verb="tinker"),
         _t(o, 2, "jammed", "cleared", "fight", contested=True, action_verb="fight"),
         _t(o, 3, "jammed", "cleared", "endure", contested=True, action_verb="endure")],
        # Tier-0 intimacy obstacle (§6, scripted): forcing/grinding the works is
        # noisy — a miss draws the sensors, not the dungeon's regard (D5 firewall).
        policy="scripted",
        bindings=[_rb(o, "*", "miss", clock_slug="party-detected", clock_delta=1)],
    ))

    # --- R5 Trap Room --------------------------------------------------------
    o = _oid("R5", "spike-plates")
    out.append(_obj(
        "R5", "spike-plates", "Spring-Spike Floor Plates", "trap", "armed",
        "A grid of subtly raised floor plates. Pressure springs beneath glint with "
        "oiled spikes, primed to drive upward.",
        [_t(o, 1, "armed", "disarmed", "disarm"),
         _t(o, 2, "armed", "sprung", "trigger")],
        # Trap (§6, scripted): a botched handling springs it — heavy spikes deal
        # authored Body stress (+2 is reserved for genuinely dangerous fiction, §5).
        policy="scripted",
        bindings=[_rb(o, "*", "miss", stress_track="body", stress_amount=2)],
    ))
    o = _oid("R5", "dart-vents")
    out.append(_obj(
        "R5", "dart-vents", "Dart-Wall Vents", "trap", "armed",
        "Rows of finger-width holes line the walls at chest height, each loaded with "
        "a needle dart behind a hair-trigger reed.",
        [_t(o, 1, "armed", "disarmed", "disarm"),
         _t(o, 2, "armed", "sprung", "trigger")],
        # Trap (§6, scripted): lighter needle darts — a botched handling costs +1 Body.
        policy="scripted",
        bindings=[_rb(o, "*", "miss", stress_track="body", stress_amount=1)],
    ))
    o = _oid("R5", "trap-lever")
    out.append(_obj(
        "R5", "trap-lever", "Trap Control Lever", "mechanism", "active",
        "A wall lever stamped with the warden's sigil, set behind a grille at the far "
        "end of the room. Thrown, it cuts power to the chamber's traps.",
        [_t(o, 1, "active", "disabled", "toggle")],
        # Trap-system control (§6, scripted): pure deterministic gate — it works or
        # it doesn't. No reaction binding: a fumbled throw moves no world clock.
        policy="scripted",
    ))
    return out


def _items() -> list[Item]:
    return [
        # R1 — lore + a breadcrumb pointing at the Marketplace key. Stowed inside
        # the Half-Buried Supply Locker (unplaced/inert), spawned into R1 on open.
        _item("R1", "travel-journal", "Sun-Bleached Travel Journal",
              "A dead scavenger's journal. The last entry: 'Lift's locked tight. "
              "Warden's key never left the market stalls — but the scorpions own them now.'",
              placed=False),
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


def save_objects_preserving_state(
    repo: MemoryRepository, objects: list[RoomObject]
) -> None:
    """Upsert authored objects, preserving any object's already-played state.

    Reseeding is additive: it refreshes an object's authored definition (name,
    description, transitions) but keeps a ``current_state`` the party has already
    changed — so re-running never resets a cleared obstacle back to blocked.
    """
    existing = {
        o["object_id"]: o for o in repo.get_objects_for_campaign(CAMPAIGN_ID)
    }
    for obj in objects:
        prior = existing.get(obj.object_id)
        if prior is not None:
            obj = obj.model_copy(update={"current_state": prior["current_state"]})
        repo.save_room_object(obj)


def main() -> None:
    db = _save_path()
    if not db.exists():
        raise SystemExit(f"Save DB not found: {db}")
    repo = MemoryRepository(db)
    try:
        # Objects
        objects = _objects()
        save_objects_preserving_state(repo, objects)
        # Items
        items = _items()
        for it in items:
            repo.save_item(it)
        # Exits — wire key/door gate on R2→R4 lift door
        exits = _lift_exits()
        for ex in exits:
            repo.save_room_exit(ex)
        # NPC — a still-sane caretaker construct sheltering in the Cargo Bay.
        # Disposition "willing" → speakable, so a sway/talk action opens the
        # SAY box (Phase 50.6 §6 dialogue gate).
        repo.save_actor(
            _aid("R3", "pinion-caretaker"), CAMPAIGN_ID, "npc", "pinion-caretaker",
            "Pinion, the Caretaker Cog", status="active",
            tags=["construct", "friendly", "lore"], room_id="R3",
            disposition="willing",
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
        print("  exits:    R2->R4 requires lift-warden-key; R4->R2 open; "
              "R4->Level2 Great Lift (connector=vertical, requires powered)")
        print("  KEY:      'Lift Warden's Iron Key' placed in R2 (Marketplace)")
    finally:
        repo.close()


if __name__ == "__main__":
    main()
