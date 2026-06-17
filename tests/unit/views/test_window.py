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


# ---------------------------------------------------------------------------
# extract_seed — loads campaign.json from save dir, saves to seed library
# ---------------------------------------------------------------------------

def test_extract_seed_saves_manifest_to_seed_library(tmp_path):
    import json

    save_dir = tmp_path / "my-run"
    save_dir.mkdir()
    manifest_data = {"slug": "my-run", "title": "My Run", "dungeon_slug": "bone-cathedral"}
    (save_dir / "campaign.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    win = DungeonDaddyWindow.__new__(DungeonDaddyWindow)
    win._save_repo = MagicMock()
    win._save_repo._dir = tmp_path
    win._seed_library = MagicMock()
    win._show_info = MagicMock()

    win.extract_seed("my-run")

    win._seed_library.save.assert_called_once()
    saved = win._seed_library.save.call_args[0][0]
    assert saved.slug == "my-run"
    assert saved.dungeon_slug == "bone-cathedral"


def test_extract_seed_noop_when_campaign_json_missing(tmp_path):
    win = DungeonDaddyWindow.__new__(DungeonDaddyWindow)
    win._save_repo = MagicMock()
    win._save_repo._dir = tmp_path
    win._seed_library = MagicMock()
    win._show_info = MagicMock()

    win.extract_seed("nonexistent")

    win._seed_library.save.assert_not_called()
