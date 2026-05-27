"""Integration tests — memory feature with real filesystem.

Covers the two bugs fixed 2026-05-24 and guards against regression:
  - save_memory_overlay must persist in both play and test-drive mode
  - append_room_event and save_memory_overlay must write to the same namespace
  - dungeon save/load round-trip must preserve save_name
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from dungeon_daddy.data.models import (
    Dungeon,
    DungeonMeta,
    Level,
    SessionState,
)
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.views.play_view import PlayView

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _level(level_id: int = 1) -> Level:
    return Level(
        id=level_id, name=f"Level {level_id}", summary="", ecology="",
        loop="lock_key", width=8, height=8, entries=[], rooms=[], connections=[],
    )


def _dungeon(save_name: str | None = None, levels: list | None = None) -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(
            title="Test Dungeon", theme="Dark", setting="S", party="P", quest="Q",
            save_name=save_name,
        ),
        levels=levels or [_level()],
    )


def _play_view(repo: DungeonRepository, dungeon: Dungeon, state: SessionState,
               is_test_drive: bool = False) -> PlayView:
    """PlayView wired to a real repo — Arcade rendering components are mocked."""
    view = PlayView.__new__(PlayView)
    view._repo = repo
    view._dungeon = dungeon
    view._state = state
    view._is_test_drive = is_test_drive
    view._ui_built = False        # keeps _open_overlay_ui a no-op (no Arcade)
    view._overlay_open = False
    view._overlay_level_id = None
    view._overlay_content = None
    view._overlay_input = None    # forces save to read from _overlay_content
    view._has_memory = False
    view._chat = MagicMock()
    view._manager = MagicMock()
    return view


# ---------------------------------------------------------------------------
# Behavior 1: play mode — edited memory persists after save
# ---------------------------------------------------------------------------

def test_play_mode_edited_memory_persists(tmp_path):
    repo = DungeonRepository(tmp_path)
    state = SessionState(dungeon_id="tomb", current_level_idx=0)
    view = _play_view(repo, _dungeon(save_name="tomb"), state)

    view.open_memory_overlay()
    view._overlay_content = "## Notes\n- Party found a key."
    view.save_memory_overlay()

    assert repo.load_room_memory("tomb", 1) == "## Notes\n- Party found a key."


def test_play_mode_memory_persists_across_open_save_reopen_cycle(tmp_path):
    repo = DungeonRepository(tmp_path)
    state = SessionState(dungeon_id="tomb", current_level_idx=0)
    view = _play_view(repo, _dungeon(save_name="tomb"), state)

    # First open — empty
    view.open_memory_overlay()
    assert view._overlay_content == ""

    # Edit and save
    view._overlay_content = "Scouted 3 rooms."
    view.save_memory_overlay()

    # Re-open — should reflect saved content
    view.open_memory_overlay()
    assert view._overlay_content == "Scouted 3 rooms."


# ---------------------------------------------------------------------------
# Behavior 2: test-drive mode — edited memory persists in __test_drive__
# ---------------------------------------------------------------------------

def test_test_drive_edited_memory_persists(tmp_path):
    repo = DungeonRepository(tmp_path)
    state = SessionState(dungeon_id="__test_drive__", current_level_idx=0)
    view = _play_view(repo, _dungeon(), state, is_test_drive=True)

    view.open_memory_overlay()
    view._overlay_content = "Test drive notes."
    view.save_memory_overlay()

    assert repo.load_room_memory("__test_drive__", 1) == "Test drive notes."


def test_test_drive_memory_persists_across_reopen(tmp_path):
    repo = DungeonRepository(tmp_path)
    state = SessionState(dungeon_id="__test_drive__", current_level_idx=0)
    view = _play_view(repo, _dungeon(), state, is_test_drive=True)

    view.open_memory_overlay()
    view._overlay_content = "Test drive exploration notes."
    view.save_memory_overlay()

    view.open_memory_overlay()
    assert view._overlay_content == "Test drive exploration notes."


# ---------------------------------------------------------------------------
# Behavior 3: namespace isolation — modes write to separate files
# ---------------------------------------------------------------------------

def test_play_and_test_drive_writes_are_isolated(tmp_path):
    repo = DungeonRepository(tmp_path)

    play_state = SessionState(dungeon_id="tomb", current_level_idx=0)
    td_state = SessionState(dungeon_id="__test_drive__", current_level_idx=0)

    play_view = _play_view(repo, _dungeon(save_name="tomb"), play_state)
    td_view = _play_view(repo, _dungeon(), td_state, is_test_drive=True)

    play_view.open_memory_overlay()
    play_view._overlay_content = "Real play notes."
    play_view.save_memory_overlay()

    td_view.open_memory_overlay()
    td_view._overlay_content = "Test drive notes."
    td_view.save_memory_overlay()

    assert repo.load_room_memory("tomb", 1) == "Real play notes."
    assert repo.load_room_memory("__test_drive__", 1) == "Test drive notes."


# ---------------------------------------------------------------------------
# Behavior 4: consistency — append_room_event and save_memory_overlay
#              write to the same file in each mode
# ---------------------------------------------------------------------------

def test_auto_remember_and_manual_save_use_same_file_in_play_mode(tmp_path):
    repo = DungeonRepository(tmp_path)

    # auto-remember path (called by _auto_remember / _handle_remember)
    repo.append_room_event("tomb", 1, "r1", "Entry Hall", "Party disarmed a trap.")

    # manual save path (called by save_memory_overlay)
    existing = repo.load_room_memory("tomb", 1)
    repo.save_room_memory("tomb", 1, existing + "\n- GM added a note.")

    final = repo.load_room_memory("tomb", 1)
    assert "Party disarmed a trap." in final
    assert "GM added a note." in final


def test_auto_remember_and_manual_save_use_same_file_in_test_drive(tmp_path):
    repo = DungeonRepository(tmp_path)

    repo.append_room_event("__test_drive__", 1, "r1", "Entry", "Auto-noted event.")
    existing = repo.load_room_memory("__test_drive__", 1)
    repo.save_room_memory("__test_drive__", 1, existing + "\n- Manual edit.")

    final = repo.load_room_memory("__test_drive__", 1)
    assert "Auto-noted event." in final
    assert "Manual edit." in final


# ---------------------------------------------------------------------------
# Behavior 5: dungeon save/load round-trip preserves save_name
# ---------------------------------------------------------------------------

def test_save_load_roundtrip_preserves_save_name(tmp_path):
    repo = DungeonRepository(tmp_path)
    dungeon = _dungeon(save_name="my-dungeon")

    repo.save(dungeon, "my-dungeon")
    loaded = repo.load("my-dungeon")

    assert loaded.meta.save_name == "my-dungeon"


def test_dungeon_saved_without_save_name_loads_as_none(tmp_path):
    """Repo behaviour: save_name absent in JSON → None on load.
    window.open_dungeon back-fills it from the folder name (tested in test_window.py).
    """
    dungeon_dir = tmp_path / "legacy"
    dungeon_dir.mkdir()
    data = {"meta": {"title": "Legacy", "theme": "T", "setting": "S",
                     "party": "P", "quest": "Q"}, "levels": []}
    (dungeon_dir / "dungeon.json").write_text(json.dumps(data), encoding="utf-8")

    repo = DungeonRepository(tmp_path)
    loaded = repo.load("legacy")

    assert loaded.meta.save_name is None
