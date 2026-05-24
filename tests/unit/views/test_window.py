"""Tests for DungeonDaddyWindow."""
from __future__ import annotations

from unittest.mock import MagicMock

from dungeon_daddy.data.models import Dungeon, DungeonMeta
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


