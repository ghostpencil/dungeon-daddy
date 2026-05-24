"""Integration tests — dungeon and session persistence via real filesystem."""
from __future__ import annotations

import pytest

from dungeon_daddy.data.models import (
    Connection,
    Dungeon,
    DungeonMeta,
    Level,
    Room,
    SessionState,
)
from dungeon_daddy.data.repository import DungeonRepository


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _make_dungeon() -> Dungeon:
    room_a = Room(id="1-A", num=1, name="Entry Hall", x=0, y=0, w=3, h=3, type="hall", note="")
    room_b = Room(id="1-B", num=2, name="Guard Post", x=5, y=0, w=3, h=3, type="vault", note="Guards here.")
    level = Level(
        id=1, name="The Sunken Vestibule", summary="Flooded entry.", ecology="Goblins",
        loop="lock_key", width=12, height=10, entries=[],
        rooms=[room_a, room_b],
        connections=[Connection(**{"from": "1-A", "to": "1-B", "type": "door"})],
    )
    return Dungeon(
        meta=DungeonMeta(
            title="Tomb of Persistence",
            theme="Undead",
            setting="Underground.",
            party="4 adventurers",
            quest="Survive.",
        ),
        levels=[level],
    )


# ---------------------------------------------------------------------------
# Behavior 1: save + load round-trip
# ---------------------------------------------------------------------------

def test_save_load_roundtrip(tmp_path):
    repo = DungeonRepository(tmp_path)
    dungeon = _make_dungeon()

    repo.save(dungeon, "tomb_of_persistence")
    loaded = repo.load("tomb_of_persistence")

    assert loaded.meta.title == dungeon.meta.title
    assert len(loaded.levels) == len(dungeon.levels)
    assert loaded.levels[0].rooms[1].name == "Guard Post"
    assert loaded.levels[0].connections[0].type == "door"


# ---------------------------------------------------------------------------
# Behavior 2: append_room_event + load_room_memory round-trip
# ---------------------------------------------------------------------------

def test_append_and_load_room_memory(tmp_path):
    repo = DungeonRepository(tmp_path)

    repo.append_room_event("crypt", 1, "1-A", "Entry Hall", "Party found a hidden lever.")

    memory = repo.load_room_memory("crypt", 1)
    assert "Party found a hidden lever." in memory


def test_multiple_events_accumulate(tmp_path):
    repo = DungeonRepository(tmp_path)

    repo.append_room_event("crypt", 1, "1-A", "Entry Hall", "First event.")
    repo.append_room_event("crypt", 1, "1-A", "Entry Hall", "Second event.")

    memory = repo.load_room_memory("crypt", 1)
    assert "First event." in memory
    assert "Second event." in memory


def test_load_room_memory_returns_empty_when_none(tmp_path):
    repo = DungeonRepository(tmp_path)
    assert repo.load_room_memory("nonexistent", 1) == ""


# ---------------------------------------------------------------------------
# Behavior 3: save_session + load_session round-trip
# ---------------------------------------------------------------------------

def test_save_load_session(tmp_path):
    repo = DungeonRepository(tmp_path)
    state = SessionState(
        dungeon_id="crypt",
        current_level_idx=1,
        current_room_id="1-B",
        visited_rooms=["1-A", "1-B"],
    )

    repo.save_session(state)
    loaded = repo.load_session("crypt")

    assert loaded is not None
    assert loaded.current_level_idx == 1
    assert loaded.current_room_id == "1-B"
    assert "1-A" in loaded.visited_rooms


def test_load_session_returns_none_when_missing(tmp_path):
    repo = DungeonRepository(tmp_path)
    assert repo.load_session("nonexistent") is None


# ---------------------------------------------------------------------------
# Behavior 4: schema evolution — missing optional meta fields get defaults
# ---------------------------------------------------------------------------

def test_missing_optional_meta_fields_get_defaults(tmp_path):
    import json

    dungeon_dir = tmp_path / "old_dungeon"
    dungeon_dir.mkdir()
    minimal_json = {
        "meta": {
            "title": "Old Dungeon",
            "theme": "Ruins",
            "setting": "A forgotten place.",
            "party": "3 wanderers",
            "quest": "Escape.",
        },
        "levels": [],
    }
    (dungeon_dir / "dungeon.json").write_text(
        json.dumps(minimal_json), encoding="utf-8"
    )

    repo = DungeonRepository(tmp_path)
    loaded = repo.load("old_dungeon")

    assert loaded.meta.party_size == 0
    assert loaded.meta.num_levels == 3
    assert loaded.meta.complexity == "Moderate"
    assert loaded.meta.save_name is None


# ---------------------------------------------------------------------------
# Behavior 5: Connection "from" alias survives save/load roundtrip
# ---------------------------------------------------------------------------

def test_connection_from_alias_survives_roundtrip(tmp_path):
    repo = DungeonRepository(tmp_path)
    dungeon = _make_dungeon()

    repo.save(dungeon, "alias_test")
    loaded = repo.load("alias_test")

    conn = loaded.levels[0].connections[0]
    assert conn.from_room == "1-A"
    assert conn.to_room == "1-B"


# ---------------------------------------------------------------------------
# Behavior 6: load_room_memory corruption recovery (SI-4)
# ---------------------------------------------------------------------------

def test_load_room_memory_returns_empty_string_for_missing_file(tmp_path):
    """Contract: missing memory file → empty string, never raises."""
    repo = DungeonRepository(tmp_path)
    result = repo.load_room_memory("no_such_dungeon", 1)
    assert result == ""


def test_load_room_memory_never_raises_for_corrupt_utf8_file(tmp_path):
    """Contract: corrupt / truncated UTF-8 bytes → str, never raises."""
    repo = DungeonRepository(tmp_path)
    memory_path = tmp_path / "dungeon_x" / "memory" / "level_1.md"
    memory_path.parent.mkdir(parents=True)
    # Simulate a partial write: valid UTF-8 header + truncated multi-byte sequence
    memory_path.write_bytes(b"## Level 1 Memory\n\n- Party found a key.\n\xe2\x80")

    result = repo.load_room_memory("dungeon_x", 1)
    assert isinstance(result, str)
