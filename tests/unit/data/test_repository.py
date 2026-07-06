"""Tests for dungeon_daddy/data/repository.py — written before implementation."""

import pytest


def make_minimal_dungeon():
    from dungeon_daddy.data.models import Connection, Dungeon, DungeonMeta, Level, Room
    return Dungeon(
        meta=DungeonMeta(
            title="Test Tomb", theme="Undead", setting="A cellar.",
            party="2 adventurers", quest="Find the key.",
        ),
        levels=[Level(
            id=1, name="L1", summary="", ecology="", loop="",
            width=10, height=8, entries=[],
            rooms=[
                Room(id="1-A", num=1, name="A", x=0, y=0, w=2, h=2, type="hall", note=""),
                Room(id="1-B", num=2, name="B", x=4, y=0, w=2, h=2, type="hall", note=""),
            ],
            connections=[Connection(from_room="1-A", to_room="1-B", type="door")],
        )],
    )


# ---------------------------------------------------------------------------
# Behavior 6: save() → load() round-trip returns equal dungeon
# ---------------------------------------------------------------------------

def test_save_and_load_round_trip(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    dungeon = make_minimal_dungeon()
    repo.save(dungeon, "test_dungeon")
    loaded = repo.load("test_dungeon")
    assert loaded == dungeon


def test_saved_file_is_pretty_printed(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save(make_minimal_dungeon(), "test_dungeon")
    raw = (tmp_path / "test_dungeon" / "dungeon.json").read_text()
    assert "  " in raw           # indented
    assert "Test Tomb" in raw    # human-readable


def test_saved_connection_uses_from_to_alias(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save(make_minimal_dungeon(), "test_dungeon")
    raw = (tmp_path / "test_dungeon" / "dungeon.json").read_text()
    assert '"from"' in raw
    assert '"to"' in raw
    assert '"from_room"' not in raw


def test_save_creates_dungeon_subfolder(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save(make_minimal_dungeon(), "my_dungeon")
    assert (tmp_path / "my_dungeon" / "dungeon.json").exists()


# ---------------------------------------------------------------------------
# Behavior 7: load() raises FileNotFoundError for missing name
# ---------------------------------------------------------------------------

def test_load_raises_for_missing_dungeon(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        repo.load("does_not_exist")


# ---------------------------------------------------------------------------
# Behavior 8: list_dungeons() excludes _session.json files
# ---------------------------------------------------------------------------

def test_list_dungeons_returns_stems(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save(make_minimal_dungeon(), "tomb_one")
    repo.save(make_minimal_dungeon(), "tomb_two")
    stems = repo.list_dungeons()
    assert sorted(stems) == ["tomb_one", "tomb_two"]


def test_list_dungeons_excludes_dirs_without_dungeon_json(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save(make_minimal_dungeon(), "tomb_one")
    # orphaned context-only folder (no dungeon.json inside)
    (tmp_path / "abandoned_dungeon").mkdir()
    stems = repo.list_dungeons()
    assert "abandoned_dungeon" not in stems
    assert stems == ["tomb_one"]


# ---------------------------------------------------------------------------
# Session state persistence
# ---------------------------------------------------------------------------

def test_save_and_load_session(tmp_path):
    from dungeon_daddy.data.models import ChatMessage, SessionState
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    state = SessionState(
        dungeon_id="tomb_one",
        current_room_id="1-A",
        visited_rooms=["1-A"],
        play_transcript=[ChatMessage(role="gm", content="hello")],
    )
    repo.save_session(state)
    loaded = repo.load_session("tomb_one")
    assert loaded == state


def test_load_session_returns_none_when_missing(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    assert repo.load_session("nonexistent") is None


def test_session_file_lives_in_dungeon_subfolder(tmp_path):
    from dungeon_daddy.data.models import SessionState
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save_session(SessionState(dungeon_id="my_dungeon"))
    assert (tmp_path / "my_dungeon" / "session.json").exists()


# ---------------------------------------------------------------------------
# Behavior 9: append_room_event() creates file + section + appends
# ---------------------------------------------------------------------------

def test_append_room_event_creates_file(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.append_room_event("tomb", 1, "1-A", "Entry Hall", "Party entered.")
    memory_file = tmp_path / "tomb" / "memory" / "level_1.md"
    assert memory_file.exists()


def test_append_room_event_creates_section_header(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.append_room_event("tomb", 1, "1-A", "Entry Hall", "Party entered.")
    content = (tmp_path / "tomb" / "memory" / "level_1.md").read_text()
    assert "## Room 1-A" in content
    assert "Entry Hall" in content


def test_append_room_event_appends_not_overwrites(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.append_room_event("tomb", 1, "1-A", "Entry Hall", "First event.")
    repo.append_room_event("tomb", 1, "1-A", "Entry Hall", "Second event.")
    content = (tmp_path / "tomb" / "memory" / "level_1.md").read_text()
    assert "First event." in content
    assert "Second event." in content


def test_append_room_event_different_rooms_same_file(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.append_room_event("tomb", 1, "1-A", "Entry Hall", "Event A.")
    repo.append_room_event("tomb", 1, "1-B", "Guard Post", "Event B.")
    content = (tmp_path / "tomb" / "memory" / "level_1.md").read_text()
    assert "## Room 1-A" in content
    assert "## Room 1-B" in content
    assert "Event A." in content
    assert "Event B." in content


# ---------------------------------------------------------------------------
# Behavior 10: load_room_memory() returns "" when no file exists
# ---------------------------------------------------------------------------

def test_load_room_memory_returns_empty_when_missing(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    assert repo.load_room_memory("tomb", 1) == ""


def test_save_and_load_room_memory_round_trip(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    content = "# Level 1 Memory\n\n## Room 1-A\n- Something happened.\n"
    repo.save_room_memory("tomb", 1, content)
    assert repo.load_room_memory("tomb", 1) == content


def test_load_sample_returns_dungeon(tmp_path):
    from dungeon_daddy.data.models import Dungeon
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    dungeon = repo.load_sample()
    assert isinstance(dungeon, Dungeon)
    assert len(dungeon.levels) > 0


# ---------------------------------------------------------------------------
# C-1: Context doc file structure + load/save
# ---------------------------------------------------------------------------

def test_save_and_load_context_doc_setting(tmp_path):
    from dungeon_daddy.data.models import ContextDocType
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    content = "# Setting\n\nA dark forest realm."
    repo.save_context_doc("my_dungeon", ContextDocType.SETTING, content)
    assert repo.load_context_doc("my_dungeon", ContextDocType.SETTING) == content


def test_save_and_load_context_doc_party(tmp_path):
    from dungeon_daddy.data.models import ContextDocType
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    content = "# Party\n\nFour adventurers of level 3."
    repo.save_context_doc("my_dungeon", ContextDocType.PARTY, content)
    assert repo.load_context_doc("my_dungeon", ContextDocType.PARTY) == content


def test_save_and_load_context_doc_level_design(tmp_path):
    from dungeon_daddy.data.models import ContextDocType
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    content = "# Level 2 Design\n\nEcology: undead."
    repo.save_context_doc("my_dungeon", ContextDocType.LEVEL_DESIGN, content, level_id=2)
    assert repo.load_context_doc("my_dungeon", ContextDocType.LEVEL_DESIGN, level_id=2) == content


def test_load_context_doc_returns_empty_when_missing(tmp_path):
    from dungeon_daddy.data.models import ContextDocType
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    assert repo.load_context_doc("my_dungeon", ContextDocType.SETTING) == ""
    assert repo.load_context_doc("my_dungeon", ContextDocType.PARTY) == ""
    assert repo.load_context_doc("my_dungeon", ContextDocType.LEVEL_DESIGN, level_id=1) == ""


def test_save_context_doc_creates_subdirectory(tmp_path):
    from dungeon_daddy.data.models import ContextDocType
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save_context_doc("my_dungeon", ContextDocType.SETTING, "content")
    assert (tmp_path / "my_dungeon").is_dir()
    assert (tmp_path / "my_dungeon" / "setting.md").exists()


def test_save_context_doc_level_design_requires_level_id(tmp_path):
    from dungeon_daddy.data.models import ContextDocType
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    with pytest.raises(ValueError):
        repo.save_context_doc("my_dungeon", ContextDocType.LEVEL_DESIGN, "content")


def test_load_context_doc_level_design_requires_level_id(tmp_path):
    from dungeon_daddy.data.models import ContextDocType
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    with pytest.raises(ValueError):
        repo.load_context_doc("my_dungeon", ContextDocType.LEVEL_DESIGN)


# ---------------------------------------------------------------------------
# migrate_legacy_layout()
# ---------------------------------------------------------------------------

def test_migrate_moves_root_json_into_subfolder(tmp_path):
    import json

    from dungeon_daddy.data.repository import DungeonRepository
    dungeon = make_minimal_dungeon()
    # write legacy layout manually
    (tmp_path / "tomb_one.json").write_text(
        json.dumps(dungeon.model_dump(mode="json", by_alias=True), indent=2)
    )
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.migrate_legacy_layout()
    assert (tmp_path / "tomb_one" / "dungeon.json").exists()
    assert not (tmp_path / "tomb_one.json").exists()


def test_migrate_moves_session_json_into_subfolder(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    (tmp_path / "tomb_one").mkdir()
    (tmp_path / "tomb_one_session.json").write_text('{"dungeon_id": "tomb_one"}')
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.migrate_legacy_layout()
    assert (tmp_path / "tomb_one" / "session.json").exists()
    assert not (tmp_path / "tomb_one_session.json").exists()


def test_migrate_moves_memory_folder_inside_dungeon_folder(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    (tmp_path / "tomb_one").mkdir()
    memory_dir = tmp_path / "tomb_one_memory"
    memory_dir.mkdir()
    (memory_dir / "level_1.md").write_text("# Memory")
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.migrate_legacy_layout()
    assert (tmp_path / "tomb_one" / "memory" / "level_1.md").exists()
    assert not memory_dir.exists()


# ---------------------------------------------------------------------------
# Phase 29.5 — list_campaigns + list_dungeons alias
# ---------------------------------------------------------------------------

def test_list_campaigns_returns_campaign_names(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save(make_minimal_dungeon(), "iron_pact")
    repo.save(make_minimal_dungeon(), "tomb_run")
    assert sorted(repo.list_campaigns()) == ["iron_pact", "tomb_run"]


def test_list_dungeons_is_alias_for_list_campaigns(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save(make_minimal_dungeon(), "iron_pact")
    assert repo.list_dungeons() == repo.list_campaigns()


# ---------------------------------------------------------------------------
# Phase 29.5 — clone_dungeon
# ---------------------------------------------------------------------------

def test_clone_dungeon_copies_dungeon_json(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save(make_minimal_dungeon(), "source_campaign")
    repo.clone_dungeon("source_campaign", "dest_campaign")
    assert (tmp_path / "dest_campaign" / "dungeon.json").exists()
    src = (tmp_path / "source_campaign" / "dungeon.json").read_text()
    dst = (tmp_path / "dest_campaign" / "dungeon.json").read_text()
    assert src == dst


def test_clone_dungeon_copies_context_docs(tmp_path):
    from dungeon_daddy.data.models import ContextDocType
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save(make_minimal_dungeon(), "source_campaign")
    repo.save_context_doc("source_campaign", ContextDocType.SETTING, "# Setting\nDark forest.")
    repo.save_context_doc("source_campaign", ContextDocType.PARTY, "# Party\nFour heroes.")
    repo.save_context_doc("source_campaign", ContextDocType.LEVEL_DESIGN, "# L1 Design\nDungeon.", level_id=1)
    repo.clone_dungeon("source_campaign", "dest_campaign")
    assert (tmp_path / "dest_campaign" / "setting.md").read_text() == "# Setting\nDark forest."
    assert (tmp_path / "dest_campaign" / "party.md").read_text() == "# Party\nFour heroes."
    assert (tmp_path / "dest_campaign" / "level_1_design.md").read_text() == "# L1 Design\nDungeon."


def test_clone_dungeon_does_not_copy_session_or_campaign_data(tmp_path):
    from dungeon_daddy.data.models import SessionState
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save(make_minimal_dungeon(), "source_campaign")
    repo.save_session(SessionState(dungeon_id="source_campaign"))
    (tmp_path / "source_campaign" / "campaign.duckdb").write_bytes(b"fake db")
    (tmp_path / "source_campaign" / "memory").mkdir()
    (tmp_path / "source_campaign" / "rpg-memory").mkdir()
    repo.clone_dungeon("source_campaign", "dest_campaign")
    assert not (tmp_path / "dest_campaign" / "session.json").exists()
    assert not (tmp_path / "dest_campaign" / "campaign.duckdb").exists()
    assert not (tmp_path / "dest_campaign" / "memory").exists()
    assert not (tmp_path / "dest_campaign" / "rpg-memory").exists()


# ---------------------------------------------------------------------------
# get_last_played — returns mtime of session.json, or None if absent
# ---------------------------------------------------------------------------

def test_get_last_played_returns_none_when_no_session(tmp_path):
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    (tmp_path / "my-save").mkdir()
    assert repo.get_last_played("my-save") is None


def test_get_last_played_returns_datetime_when_session_exists(tmp_path):
    from datetime import datetime

    from dungeon_daddy.data.models import SessionState
    from dungeon_daddy.data.repository import DungeonRepository
    repo = DungeonRepository(campaigns_dir=tmp_path)
    repo.save_session(SessionState(dungeon_id="my-save"))
    result = repo.get_last_played("my-save")
    assert isinstance(result, datetime)
