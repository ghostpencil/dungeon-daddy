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
# P4 — _attach_rpg_context reads seed persona docs into PlayView
# ---------------------------------------------------------------------------

from pathlib import Path

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy" / "data" / "migrations"
)


def _build_campaign(campaign_dir, *, voice=None, knowledge=None):
    """Create a campaign.duckdb (and optional persona docs) for save_name."""
    from dungeon_daddy.memory.repository import MemoryRepository
    from dungeon_daddy.memory.dungeon_persona import (
        write_dungeon_voice, write_dungeon_knowledge,
    )
    from dungeon_daddy.window import _slugify

    campaign_dir.mkdir(parents=True, exist_ok=True)
    campaign_id = f"campaign:{_slugify(campaign_dir.name)}"
    repo = MemoryRepository(campaign_dir / "campaign.duckdb")
    repo.initialize_schema(MIGRATIONS_DIR)

    voice_ref = knowledge_ref = None
    if voice is not None or knowledge:
        dungeon_dir = campaign_dir / "memory" / "dungeon"
        if voice is not None:
            p = write_dungeon_voice(dungeon_dir, campaign_id, voice)
            voice_ref = p.relative_to(campaign_dir).as_posix()
        if knowledge:
            p = write_dungeon_knowledge(dungeon_dir, campaign_id, knowledge)
            knowledge_ref = p.relative_to(campaign_dir).as_posix()
    repo.save_campaign(
        campaign_id, _slugify(campaign_dir.name), campaign_dir.name,
        dungeon_voice_path=voice_ref, dungeon_knowledge_path=knowledge_ref,
    )
    repo.close()


def _attach_window(tmp_path, save_name):
    win = DungeonDaddyWindow.__new__(DungeonDaddyWindow)
    win._play_view = MagicMock()
    win._repo = MagicMock()
    win._repo._dir = tmp_path
    win._attach_rpg_context(save_name)
    return win


def test_attach_rpg_context_reads_persona_docs(tmp_path):
    save_name = "The Crucible"
    _build_campaign(
        tmp_path / save_name,
        voice="cold, ancient, watchful",
        knowledge=["the heart still beats", "a way down"],
    )

    win = _attach_window(tmp_path, save_name)

    win._play_view.set_dungeon_persona.assert_called_once_with(
        "cold, ancient, watchful", ["the heart still beats", "a way down"],
    )


def test_attach_rpg_context_no_persona_refs(tmp_path):
    save_name = "The Crucible"
    _build_campaign(tmp_path / save_name)  # campaign row, no persona refs

    win = _attach_window(tmp_path, save_name)

    win._play_view.set_dungeon_persona.assert_called_once_with(None, [])


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
