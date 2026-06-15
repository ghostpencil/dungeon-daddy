"""Tests for DungeonDaddyWindow."""
from __future__ import annotations

from unittest.mock import MagicMock

from dungeon_daddy.window import DungeonDaddyWindow


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
