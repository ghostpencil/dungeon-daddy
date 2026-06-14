"""Tests for DungeonDaddyWindow."""
from __future__ import annotations

from unittest.mock import MagicMock

from dungeon_daddy.data.models import Dungeon, DungeonMeta
from dungeon_daddy.ui.chrome import MenuAction
from dungeon_daddy.window import DungeonDaddyWindow


def _make_window() -> DungeonDaddyWindow:
    win = DungeonDaddyWindow.__new__(DungeonDaddyWindow)
    win._play_view = MagicMock()
    win.switch_to_play = MagicMock()
    return win


def _saved_dungeon(save_name: str = "my_dungeon") -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q", save_name=save_name),
        levels=[],
    )


# ---------------------------------------------------------------------------
# set_switch_to_play_enabled
# ---------------------------------------------------------------------------

def test_set_switch_to_play_enabled_false():
    win = _make_window()
    action = MenuAction("Switch to Play", lambda: None)
    win._switch_to_play_action = action

    win.set_switch_to_play_enabled(False)

    assert action.enabled is False


def test_set_switch_to_play_enabled_true():
    win = _make_window()
    action = MenuAction("Switch to Play", lambda: None)
    action.enabled = False
    win._switch_to_play_action = action

    win.set_switch_to_play_enabled(True)

    assert action.enabled is True


# ---------------------------------------------------------------------------
# Switch to Play menu handler — mirrors Start Play button behaviour
# ---------------------------------------------------------------------------

def _make_window_with_design_view(dungeon=None) -> DungeonDaddyWindow:
    win = _make_window()
    win._design_view = MagicMock()
    win._design_view._dungeon = dungeon
    win.launch_play_session = MagicMock()
    return win


def test_menu_launch_play_calls_launch_play_session_when_saved_with_levels():
    from dungeon_daddy.data.models import Level
    dungeon = _saved_dungeon()
    dungeon.levels = [Level(id=1, name="L", summary="", ecology="", loop="", width=5, height=5, entries=[], rooms=[], connections=[])]
    win = _make_window_with_design_view(dungeon)

    win._menu_launch_play()

    win.launch_play_session.assert_called_once_with(dungeon)


def test_menu_launch_play_does_nothing_when_dungeon_is_none():
    win = _make_window_with_design_view(dungeon=None)

    win._menu_launch_play()

    win.launch_play_session.assert_not_called()


def test_menu_launch_play_does_nothing_when_not_saved():
    dungeon = Dungeon(
        meta=DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q", save_name=None),
        levels=[],
    )
    win = _make_window_with_design_view(dungeon)

    win._menu_launch_play()

    win.launch_play_session.assert_not_called()


# ---------------------------------------------------------------------------
# _attach_rpg_context passes portraits_dir
# ---------------------------------------------------------------------------

def test_attach_rpg_context_passes_portraits_dir(tmp_path):
    from unittest.mock import MagicMock
    from dungeon_daddy.window import DungeonDaddyWindow

    save_name = "The Crucible"
    campaign_dir = tmp_path / save_name
    campaign_dir.mkdir(parents=True)
    # no campaign.duckdb — so mem_repo stays None but portraits_dir still computed

    win = DungeonDaddyWindow.__new__(DungeonDaddyWindow)
    win._play_view = MagicMock()
    win._repo = MagicMock()
    win._repo._dir = tmp_path

    expected_portraits = campaign_dir / "assets" / "portraits"

    win._attach_rpg_context(save_name)

    win._play_view.set_rpg_context.assert_called_once()
    _, kwargs = win._play_view.set_rpg_context.call_args
    assert kwargs.get("portraits_dir") == expected_portraits


