"""Reset "The Crucible" save to a fresh new-game state (dev / playtest tool).

A full new-game reset — useful for repeatedly re-testing the early game as the
RPG systems develop. It reverts *play progress* while preserving the authored
campaign (rooms, exits, seeded objects/items/actors, dungeon persona docs):

- **Party** → Level 1 (index 0), room ``R1``; ``visited_rooms`` = ``[R1]``;
  transcripts and active loop cleared (``session.json``).
- **Clocks** → all ``filled`` reset to 0.
- **Objectives** → initial ladder (tier 0 ``active``, tiers 1-3 ``locked``),
  which re-gates the per-tier unlocked knowledge (derived from status).
- **Room objects** → their authored seed state (gearworks ``jammed``, the Great
  Lift ``unpowered``, the four subsystems back to blocked, …). Initial states are
  read from the seed builders, so this stays correct as the seeds evolve.
- **Actor stress** → all tracks ``filled`` 0; **items** → seeded placement
  (unowned, active).
- **Play memory wiped** → ``memory_entries`` (+ tags/links), ``domain_events``,
  and the ``memory/level_*.md`` play-memory files. The static dungeon persona
  docs under ``memory/dungeon/`` are kept.

``main()`` takes a timestamped backup of ``campaign.duckdb`` + ``session.json``
before mutating. Close the app first (DuckDB is single-writer).

Run:  python -m tools.reset_crucible_new_game
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from dungeon_daddy.memory.repository import MemoryRepository
from tools.populate_crucible_dungeon_channel import LADDER, RESONANCE_OBJECT_ID
from tools.populate_crucible_level1 import _items as _level1_items
from tools.populate_crucible_level1 import _objects as _level1_objects

CAMPAIGN_ID = "campaign:the-crucible"
START_LEVEL_IDX = 0
START_ROOM_ID = "R1"


def _initial_object_states() -> dict[str, str]:
    """Authored initial ``current_state`` for every seeded object, by object id.

    Sourced from the seed builders (Level-1 objects + the tier-1-3 subsystems +
    the resonance node) so a reset always matches the current authored seed.
    """
    states = {o.object_id: o.current_state for o in _level1_objects()}
    for rung in LADDER:
        if rung.room_id is not None and rung.broken_state is not None:
            oid = f"object:the-crucible:{rung.room_id}:{rung.subsystem_slug}"
            states[oid] = rung.broken_state
    states[RESONANCE_OBJECT_ID] = "attuned"
    return states


def _initial_item_placement() -> dict[str, tuple[str | None, str]]:
    """Authored ``(room_id, status)`` for every Level-1 seed item, by item id.

    Restores placement a reset must honor: container loot returns to its
    unplaced/inert state (so its container re-spawns it on open), and loose items
    return to their authored room — both of which the blanket unown/activate pass
    can't express on its own.
    """
    return {i.item_id: (i.room_id, i.status) for i in _level1_items()}


def _reset_session_json(save_dir: Path) -> None:
    """Send the party back to the first room of the first floor, clear logs."""
    path = save_dir / "session.json"
    data: dict = {}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("dungeon_id", "The Crucible")
    data.setdefault("map_variant", "grid")
    data["current_level_idx"] = START_LEVEL_IDX
    data["current_room_id"] = START_ROOM_ID
    data["visited_rooms"] = [START_ROOM_ID]
    data["active_loop_id"] = None
    data["play_transcript"] = []
    data["design_transcript"] = []
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def reset_to_new_game(
    repo: MemoryRepository,
    save_dir: Path,
    campaign_id: str = CAMPAIGN_ID,
) -> dict[str, int]:
    """Reset ``campaign_id`` to a fresh new-game state (see module docstring).

    Returns a small counts summary. Operates on the given repo + save dir so it
    is unit-testable; ``main()`` wires the live save path and a backup.
    """
    _reset_session_json(save_dir)
    con = repo._conn  # type: ignore[union-attr]

    con.execute("UPDATE clocks SET filled = 0 WHERE campaign_id = ?", [campaign_id])
    con.execute(
        "UPDATE objectives SET status = CASE WHEN tier_index = 0 THEN 'active' "
        "ELSE 'locked' END WHERE campaign_id = ?",
        [campaign_id],
    )

    objects_reset = 0
    for oid, state in _initial_object_states().items():
        cur = con.execute(
            "SELECT current_state FROM room_objects WHERE object_id = ? AND campaign_id = ?",
            [oid, campaign_id],
        ).fetchone()
        if cur is not None and cur[0] != state:
            repo.update_object_state(oid, state)
            objects_reset += 1

    con.execute(
        "UPDATE stress_tracks SET filled = 0 WHERE actor_id IN "
        "(SELECT actor_id FROM actors WHERE campaign_id = ?)",
        [campaign_id],
    )
    con.execute(
        "UPDATE items SET owner_actor_id = NULL, status = 'active' WHERE campaign_id = ?",
        [campaign_id],
    )
    # Restore authored placement for seed items the blanket pass above can't
    # express: unplaced/inert container loot, and loose items dropped/moved
    # during play. (Keyed by item_id so only seeded items are touched.)
    for iid, (room_id, status) in _initial_item_placement().items():
        con.execute(
            "UPDATE items SET room_id = ?, status = ? WHERE item_id = ? AND campaign_id = ?",
            [room_id, status, iid, campaign_id],
        )

    memories = con.execute(
        "SELECT COUNT(*) FROM memory_entries WHERE campaign_id = ?", [campaign_id]
    ).fetchone()[0]
    events = con.execute(
        "SELECT COUNT(*) FROM domain_events WHERE campaign_id = ?", [campaign_id]
    ).fetchone()[0]
    con.execute(
        "DELETE FROM memory_links WHERE from_id IN "
        "(SELECT memory_id FROM memory_entries WHERE campaign_id = ?) "
        "OR to_id IN (SELECT memory_id FROM memory_entries WHERE campaign_id = ?)",
        [campaign_id, campaign_id],
    )
    con.execute(
        "DELETE FROM memory_tags WHERE memory_id IN "
        "(SELECT memory_id FROM memory_entries WHERE campaign_id = ?)",
        [campaign_id],
    )
    con.execute("DELETE FROM memory_entries WHERE campaign_id = ?", [campaign_id])
    con.execute("DELETE FROM domain_events WHERE campaign_id = ?", [campaign_id])

    md_deleted = 0
    for md in sorted((save_dir / "memory").glob("level_*.md")):
        md.unlink()
        md_deleted += 1

    return {
        "objects_reset": objects_reset,
        "memories_wiped": memories,
        "events_wiped": events,
        "play_memory_md_deleted": md_deleted,
    }


def _save_dir() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / "DungeonDaddy" / "saves" / "The Crucible"


def _backup(path: Path, stamp: str) -> Path:
    dest = path.with_name(f"{path.name}.bak-newgame-{stamp}")
    shutil.copy2(path, dest)
    return dest


def main() -> None:
    save_dir = _save_dir()
    db = save_dir / "campaign.duckdb"
    if not db.exists():
        raise SystemExit(f"Save DB not found: {db}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"Backup: {_backup(db, stamp).name}")
    session = save_dir / "session.json"
    if session.exists():
        print(f"Backup: {_backup(session, stamp).name}")

    repo = MemoryRepository(db)
    try:
        counts = reset_to_new_game(repo, save_dir, CAMPAIGN_ID)
    finally:
        repo.close()

    print(f"Reset The Crucible to a new-game state at {db}")
    print(f"  party:    Level 1 (idx {START_LEVEL_IDX}), room {START_ROOM_ID}")
    print("  clocks:   all filled -> 0")
    print("  ladder:   tier 0 active, tiers 1-3 locked")
    print(f"  objects:  {counts['objects_reset']} reset to seed state")
    print(f"  wiped:    {counts['memories_wiped']} memories, {counts['events_wiped']} events, "
          f"{counts['play_memory_md_deleted']} play-memory files")


if __name__ == "__main__":
    main()
