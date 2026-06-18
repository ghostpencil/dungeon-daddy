"""Unit tests for LibraryView — Phase 45 Slice 6."""
from __future__ import annotations

from unittest.mock import MagicMock

from dungeon_daddy.views.library_view import LibraryView


def _make_view() -> LibraryView:
    view = LibraryView.__new__(LibraryView)
    view._init_state()
    return view


def _view_with_window() -> LibraryView:
    view = _make_view()
    view.window = MagicMock()
    return view


# ---------------------------------------------------------------------------
# Cycle 1 — initial state: empty sections when no sources are set
# ---------------------------------------------------------------------------

def test_initial_state_empty_sections():
    view = _make_view()
    assert view.dungeon_slugs() == []
    assert view.seed_slugs() == []
    assert view.save_slugs() == []


# ---------------------------------------------------------------------------
# Cycle 2 — set_sources populates dungeon slugs from dungeon_repo
# ---------------------------------------------------------------------------

def test_set_sources_dungeon_slugs():
    view = _make_view()
    repo = MagicMock()
    repo.list_campaigns.return_value = ["dungeon-a", "dungeon-b"]
    view.set_sources(dungeon_repo=repo, seed_library=None, save_repo=None)
    assert view.dungeon_slugs() == ["dungeon-a", "dungeon-b"]


# ---------------------------------------------------------------------------
# Cycle 3 — set_sources populates seed slugs from seed_library
# ---------------------------------------------------------------------------

def test_set_sources_seed_slugs():
    view = _make_view()
    lib = MagicMock()
    lib.list.return_value = ["seed-x", "seed-y"]
    view.set_sources(dungeon_repo=None, seed_library=lib, save_repo=None)
    assert view.seed_slugs() == ["seed-x", "seed-y"]


# ---------------------------------------------------------------------------
# Cycle 4 — set_sources populates save slugs from save_repo
# ---------------------------------------------------------------------------

def test_set_sources_save_slugs():
    view = _make_view()
    repo = MagicMock()
    repo.list_campaigns.return_value = ["save-1", "save-2"]
    view.set_sources(dungeon_repo=None, seed_library=None, save_repo=repo)
    assert view.save_slugs() == ["save-1", "save-2"]


# ---------------------------------------------------------------------------
# Cycle 5 — on_open_dungeon calls window.open_in_designer
# ---------------------------------------------------------------------------

def test_on_open_dungeon_calls_window():
    view = _view_with_window()
    view.on_open_dungeon("dungeon-a")
    view.window.open_in_designer.assert_called_once_with("dungeon-a")


# ---------------------------------------------------------------------------
# Cycle 6 — on_new_seed calls window.new_seed_from_dungeon
# ---------------------------------------------------------------------------

def test_on_new_seed_calls_window():
    view = _view_with_window()
    view.on_new_seed("dungeon-a")
    view.window.new_seed_from_dungeon.assert_called_once_with("dungeon-a")


# ---------------------------------------------------------------------------
# Cycle 7 — on_edit_seed calls window.edit_seed
# ---------------------------------------------------------------------------

def test_on_edit_seed_calls_window():
    view = _view_with_window()
    view.on_edit_seed("seed-x")
    view.window.edit_seed.assert_called_once_with("seed-x")


# ---------------------------------------------------------------------------
# Cycle 8 — on_publish calls window.publish_and_play
# ---------------------------------------------------------------------------

def test_on_publish_calls_window():
    view = _view_with_window()
    view.on_publish("seed-x")
    view.window.publish_and_play.assert_called_once_with("seed-x")


# ---------------------------------------------------------------------------
# Cycle 9 — on_play_save calls window.launch_save_game
# ---------------------------------------------------------------------------

def test_on_play_save_calls_window():
    view = _view_with_window()
    view.on_play_save("save-1")
    view.window.launch_save_game.assert_called_once_with("save-1")


# ---------------------------------------------------------------------------
# Cycle 10 — on_delete_save shows confirmation dialog before deleting
# ---------------------------------------------------------------------------

def test_on_delete_save_confirmed_calls_window():
    view = _view_with_window()
    view.window._ask_yes_no.return_value = True
    view.on_delete_save("save-1")
    view.window.delete_save.assert_called_once_with("save-1")


def test_on_delete_save_cancelled_does_not_delete():
    view = _view_with_window()
    view.window._ask_yes_no.return_value = False
    view.on_delete_save("save-1")
    view.window.delete_save.assert_not_called()


def test_on_delete_save_asks_before_deleting():
    view = _view_with_window()
    view.window._ask_yes_no.return_value = True
    view.on_delete_save("save-1")
    view.window._ask_yes_no.assert_called_once()


# ---------------------------------------------------------------------------
# Cycle 11 — on_new_dungeon calls window.new_dungeon
# ---------------------------------------------------------------------------

def test_on_new_dungeon_calls_window():
    view = _view_with_window()
    view.on_new_dungeon()
    view.window.new_dungeon.assert_called_once()


# ---------------------------------------------------------------------------
# Cycle 12 — _refresh() builds _save_meta from save_repo.get_last_played()
# ---------------------------------------------------------------------------

def test_refresh_populates_save_meta_with_last_played(tmp_path):
    from datetime import datetime
    from dungeon_daddy.data.repository import DungeonRepository
    from dungeon_daddy.data.models import SessionState

    repo = DungeonRepository(campaigns_dir=tmp_path)
    # save-a has a session, save-b does not
    repo.save_session(SessionState(dungeon_id="save-a"))
    (tmp_path / "save-b").mkdir()
    (tmp_path / "save-b" / "dungeon.json").write_text("{}", encoding="utf-8")
    (tmp_path / "save-a" / "dungeon.json").write_text("{}", encoding="utf-8")

    view = _make_view()
    view.set_sources(dungeon_repo=MagicMock(), seed_library=MagicMock(), save_repo=repo)
    view._save_list = ["save-a", "save-b"]
    view._refresh_save_meta()

    assert isinstance(view._save_meta["save-a"], datetime)
    assert view._save_meta["save-b"] is None


def test_refresh_save_meta_empty_when_no_saves():
    view = _make_view()
    repo = MagicMock()
    view.set_sources(dungeon_repo=None, seed_library=None, save_repo=repo)
    view._save_list = []
    view._refresh_save_meta()
    assert view._save_meta == {}


# ---------------------------------------------------------------------------
# Cycle 13 — on_extract_seed calls window.extract_seed
# ---------------------------------------------------------------------------

def test_on_extract_seed_calls_window():
    view = _view_with_window()
    view.on_extract_seed("save-1")
    view.window.extract_seed.assert_called_once_with("save-1")
