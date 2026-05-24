"""Integration tests — validate → auto_fix → save → load → validate cycle."""
from __future__ import annotations

import pytest

from dungeon_daddy.data.models import (
    Connection,
    Dungeon,
    DungeonMeta,
    Level,
    Loop,
    Room,
    validate_dungeon,
    auto_fix_dungeon,
)
from dungeon_daddy.data.repository import DungeonRepository


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _three_rooms() -> list[Room]:
    return [
        Room(id="R1", num=1, name="Entry", x=0, y=0, w=2, h=2, type="hall", note=""),
        Room(id="R2", num=2, name="Middle", x=3, y=0, w=2, h=2, type="hall", note=""),
        Room(id="R3", num=3, name="Goal", x=6, y=0, w=2, h=2, type="vault", note=""),
    ]


def _two_doors() -> list[Connection]:
    return [
        Connection(**{"from": "R1", "to": "R2", "type": "door"}),
        Connection(**{"from": "R2", "to": "R3", "type": "door"}),
    ]


def _make_dungeon(loops: list[Loop]) -> Dungeon:
    level = Level(
        id=1, name="Test Level", summary=".", ecology="None",
        loop="lock_key", loops=loops,
        width=10, height=5, entries=[],
        rooms=_three_rooms(),
        connections=_two_doors(),
    )
    return Dungeon(
        meta=DungeonMeta(title="Fix Test", theme="Test", setting=".", party="4", quest="."),
        levels=[level],
    )


def _main_loop(loop_id: str, explanation: str = "Ready.") -> Loop:
    return Loop(
        id=loop_id, pattern="lock_key", note="", entry="R1", goal="R3",
        path_a=[], path_b=[], type="main", explanation=explanation, rooms=[],
    )


# ---------------------------------------------------------------------------
# Behavior 1: empty explanation fix persists through save/load (tracer bullet)
# ---------------------------------------------------------------------------

def test_empty_explanation_fix_persists(tmp_path):
    repo = DungeonRepository(tmp_path)
    dungeon = _make_dungeon([_main_loop("lp1", explanation="")])

    assert not validate_dungeon(dungeon).is_valid

    auto_fix_dungeon(dungeon)

    repo.save(dungeon, "fix_test")
    loaded = repo.load("fix_test")

    result = validate_dungeon(loaded)
    assert result.is_valid, result.errors
    assert loaded.levels[0].loops[0].explanation == "Explanation pending."


# ---------------------------------------------------------------------------
# Behavior 2: demoted loop type (main → sub) persists through save/load
# ---------------------------------------------------------------------------

def test_demoted_loop_type_persists(tmp_path):
    repo = DungeonRepository(tmp_path)
    loop_a = _main_loop("lp1", explanation="Primary story.")
    loop_b = Loop(
        id="lp2", pattern="lock_key", note="", entry="R1", goal="R3",
        path_a=[], path_b=[], type="main", explanation="Secondary story.", rooms=[],
    )
    dungeon = _make_dungeon([loop_a, loop_b])

    assert not validate_dungeon(dungeon).is_valid

    auto_fix_dungeon(dungeon)

    repo.save(dungeon, "fix_test")
    loaded = repo.load("fix_test")

    result = validate_dungeon(loaded)
    assert result.is_valid, result.errors
    types = [lp.type for lp in loaded.levels[0].loops]
    assert types.count("main") == 1
    assert types.count("sub") == 1


# ---------------------------------------------------------------------------
# Behavior 3: auto_fix returns a description for every fix applied
# ---------------------------------------------------------------------------

def test_auto_fix_returns_descriptions_of_all_fixes(tmp_path):
    loop_a = _main_loop("lp1", explanation="")
    loop_b = Loop(
        id="lp2", pattern="lock_key", note="", entry="R1", goal="R3",
        path_a=[], path_b=[], type="main", explanation="", rooms=[],
    )
    dungeon = _make_dungeon([loop_a, loop_b])

    fixes = auto_fix_dungeon(dungeon)

    assert len(fixes) == 3  # 2 explanation fixes + 1 demotion
    assert any("lp1" in f and "explanation" in f for f in fixes)
    assert any("lp2" in f and "explanation" in f for f in fixes)
    assert any("lp2" in f and "demoted" in f for f in fixes)
