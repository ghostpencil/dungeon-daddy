"""Integration tests — LoopPatternCatalog roundtrip and loop pattern cross-reference validation."""
from __future__ import annotations

from dungeon_daddy.data.models import (
    Connection,
    Dungeon,
    DungeonMeta,
    Level,
    Loop,
    LoopPatternCatalog,
    Room,
    validate_dungeon,
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


def _make_dungeon(loop_key: str = "lock_key", loop_patterns=None) -> Dungeon:
    loop = Loop(
        id="lp1", pattern=loop_key, note="", entry="R1", goal="R3",
        path_a=[], path_b=[], type="main", explanation="Ready.", rooms=[],
    )
    level = Level(
        id=1, name="Test Level", summary=".", ecology="None",
        loop=loop_key, loops=[loop],
        width=10, height=5, entries=[],
        rooms=_three_rooms(),
        connections=_two_doors(),
    )
    return Dungeon(
        meta=DungeonMeta(title="Pattern Test", theme="Test", setting=".", party="4", quest="."),
        levels=[level],
        loop_patterns=loop_patterns or {},
    )


# ---------------------------------------------------------------------------
# Behavior 1: loop_patterns dict survives save/load roundtrip (tracer bullet)
# ---------------------------------------------------------------------------

def test_catalog_roundtrip_preserves_all_patterns(tmp_path):
    catalog = LoopPatternCatalog.load_bundled()
    dungeon = _make_dungeon(loop_patterns=catalog.patterns)

    repo = DungeonRepository(tmp_path)
    repo.save(dungeon, "pattern_test")
    loaded = repo.load("pattern_test")

    assert set(loaded.loop_patterns.keys()) == set(catalog.patterns.keys())
    assert loaded.loop_patterns["lock_key"].name == "Lock & Key"


# ---------------------------------------------------------------------------
# Behavior 2: level.loop key absent from loop_patterns triggers validation error
# ---------------------------------------------------------------------------

def test_absent_loop_pattern_key_fails_validation():
    catalog = LoopPatternCatalog.load_bundled()
    dungeon = _make_dungeon(loop_key="nonexistent_pattern", loop_patterns=catalog.patterns)

    result = validate_dungeon(dungeon)

    assert not result.is_valid
    assert any("nonexistent_pattern" in e for e in result.errors)
