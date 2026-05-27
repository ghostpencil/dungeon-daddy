"""Canonical input fixtures for AI output evals."""
from __future__ import annotations

from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level, Room
from dungeon_daddy.llm.agents.wizard_agent import DungeonBrief, LevelBrief

# ---------------------------------------------------------------------------
# Generator fixtures
# ---------------------------------------------------------------------------

TOMB_BRIEF = DungeonBrief(
    title="Tomb of the Forgotten King",
    theme="undead",
    setting="ancient tomb carved into living rock",
    party="4 adventurers of level 3",
    quest="Recover the King's obsidian crown",
    num_levels=1,
)

TOMB_LEVEL_BRIEF = LevelBrief(
    level_number=1,
    ecology="Skeletons and restless spirits",
    main_loop_pattern="lock_key",
    sub_loop_pattern=None,
    gm_notes="",
)

# ---------------------------------------------------------------------------
# DM fixtures
# ---------------------------------------------------------------------------

VAULT_ROOM = Room(
    id="r1",
    num=1,
    name="The Obsidian Vault",
    x=0,
    y=0,
    w=5,
    h=5,
    type="vault",
    note="A sealed chamber holding the king's most prized relics. Dust covers everything.",
)

VAULT_LEVEL = Level(
    id=1,
    name="Depths of the Forgotten",
    summary="The first level of the tomb.",
    ecology="Undead",
    loop="lock_key",
    loops=[],
    width=20,
    height=20,
    entries=[],
    rooms=[VAULT_ROOM],
    connections=[],
)

TOMB_DUNGEON = Dungeon(
    meta=DungeonMeta(
        title="Tomb of the Forgotten King",
        theme="undead",
        setting="ancient tomb",
        party="4 adventurers",
        quest="Recover the King's obsidian crown",
    ),
    levels=[VAULT_LEVEL],
)
