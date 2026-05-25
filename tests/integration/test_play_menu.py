"""Integration tests — Switch to Play menu item wiring.

Verifies the end-to-end path from dungeon save-state through
DesignView._refresh_play_button_state to the real MenuAction.enabled flag
on the real window, without mocking the intermediary window or view.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.views.design_view import DesignView
from dungeon_daddy.window import DungeonDaddyWindow


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _level() -> Level:
    return Level(
        id=1, name="Level 1", summary=".", ecology=".", loop="lock_key",
        width=5, height=5, entries=[], rooms=[], connections=[],
    )


def _dungeon(save_name: str | None = None, with_levels: bool = False) -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q", save_name=save_name),
        levels=[_level()] if with_levels else [],
    )


def _make_window(repo: DungeonRepository) -> DungeonDaddyWindow:
    """Real window with real menu — Arcade init bypassed."""
    win = DungeonDaddyWindow.__new__(DungeonDaddyWindow)
    win._repo = repo
    win._design_view = MagicMock()
    win._play_view = MagicMock()
    win._menu = win._build_menu()
    return win


def _make_design_view(repo: DungeonRepository, window: DungeonDaddyWindow, dungeon: Dungeon) -> DesignView:
    """Real DesignView wired to the real window — Arcade/UI rendering mocked."""
    view = DesignView.__new__(DesignView)
    view._repo = repo
    view._dungeon = dungeon
    view._inspector = MagicMock()
    view.window = window
    return view


# ---------------------------------------------------------------------------
# Behavior 1 (tracer): saved dungeon → real menu action is enabled
# ---------------------------------------------------------------------------

def test_saved_dungeon_enables_switch_to_play_menu_action(tmp_path):
    repo = DungeonRepository(tmp_path)
    dungeon = _dungeon(save_name="crypt")
    repo.save(dungeon, "crypt")

    win = _make_window(repo)
    view = _make_design_view(repo, win, dungeon)

    view._refresh_play_button_state()

    assert win._switch_to_play_action.enabled is True


# ---------------------------------------------------------------------------
# Behavior 2: unsaved dungeon → real menu action is disabled
# ---------------------------------------------------------------------------

def test_unsaved_dungeon_disables_switch_to_play_menu_action(tmp_path):
    repo = DungeonRepository(tmp_path)
    dungeon = _dungeon(save_name=None)

    win = _make_window(repo)
    view = _make_design_view(repo, win, dungeon)

    view._refresh_play_button_state()

    assert win._switch_to_play_action.enabled is False


# ---------------------------------------------------------------------------
# Behavior 3: real menu handler launches play session for saved dungeon
# ---------------------------------------------------------------------------

def test_menu_handler_launches_session_for_saved_dungeon_with_levels(tmp_path):
    repo = DungeonRepository(tmp_path)
    dungeon = _dungeon(save_name="crypt", with_levels=True)
    repo.save(dungeon, "crypt")

    win = _make_window(repo)
    win._design_view._dungeon = dungeon
    win.launch_play_session = MagicMock()

    win._menu_launch_play()

    win.launch_play_session.assert_called_once_with(dungeon)


# ---------------------------------------------------------------------------
# Behavior 4: save cycle — disabled before save, enabled after
# ---------------------------------------------------------------------------

def test_save_then_refresh_flips_action_from_disabled_to_enabled(tmp_path):
    repo = DungeonRepository(tmp_path)
    dungeon = _dungeon(save_name=None)

    win = _make_window(repo)
    view = _make_design_view(repo, win, dungeon)

    view._refresh_play_button_state()
    assert win._switch_to_play_action.enabled is False

    dungeon.meta.save_name = "crypt"
    repo.save(dungeon, "crypt")

    view._refresh_play_button_state()
    assert win._switch_to_play_action.enabled is True
