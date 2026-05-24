"""Integration tests — window open-dungeon and view-transition seams."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

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
from dungeon_daddy.views.play_view import PlayView
from dungeon_daddy.window import DungeonDaddyWindow


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _make_dungeon(save_name: str = "test_dungeon") -> Dungeon:
    room = Room(id="R1", num=1, name="Entry", x=0, y=0, w=2, h=2, type="hall", note="")
    level = Level(
        id=1, name="Test Level", summary=".", ecology="None",
        loop="lock_key", loops=[], width=10, height=5, entries=[],
        rooms=[room], connections=[],
    )
    return Dungeon(
        meta=DungeonMeta(
            title="Seam Test Dungeon", theme="Test", setting=".", party="4", quest=".",
            save_name=save_name,
        ),
        levels=[level],
    )


def _make_window(repo: DungeonRepository) -> DungeonDaddyWindow:
    win = DungeonDaddyWindow.__new__(DungeonDaddyWindow)
    win._repo = repo
    win._design_view = MagicMock()
    win._play_view = MagicMock()
    win.switch_mode = MagicMock()
    return win


def _make_play_view(repo: DungeonRepository) -> PlayView:
    view = PlayView.__new__(PlayView)
    view._repo = repo
    view._is_test_drive = False
    view._dungeon = None
    view._state = None
    view._has_memory = False
    view._map = MagicMock()
    view._chat = MagicMock()
    return view


# ---------------------------------------------------------------------------
# Behavior 1: both views receive same dungeon object after open (tracer)
# ---------------------------------------------------------------------------

def test_both_views_share_same_dungeon_reference_after_open(tmp_path):
    repo = DungeonRepository(tmp_path)
    dungeon = _make_dungeon()
    repo.save(dungeon, "test_dungeon")

    win = _make_window(repo)
    win.open_dungeon(_pick_fn=lambda: "test_dungeon")

    design_arg = win._design_view.load_dungeon.call_args[0][0]
    play_arg = win._play_view.load_dungeon.call_args[0][0]

    assert design_arg is play_arg
    assert design_arg.meta.title == "Seam Test Dungeon"


# ---------------------------------------------------------------------------
# Behavior 2: missing session file → load_dungeon_session creates fresh state
# ---------------------------------------------------------------------------

def test_missing_session_creates_fresh_state(tmp_path):
    repo = DungeonRepository(tmp_path)
    dungeon = _make_dungeon(save_name="no_session")

    view = _make_play_view(repo)
    view.load_dungeon_session(dungeon)

    assert view._dungeon is dungeon
    assert view._state is not None
    assert view._state.dungeon_id == "no_session"


# ---------------------------------------------------------------------------
# Behavior 3: corrupt session file → load_dungeon_session does not crash
# ---------------------------------------------------------------------------

def test_corrupt_session_does_not_crash(tmp_path):
    repo = DungeonRepository(tmp_path)
    dungeon = _make_dungeon(save_name="corrupt_session")

    session_dir = tmp_path / "corrupt_session"
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "session.json").write_text("not valid json {{", encoding="utf-8")

    view = _make_play_view(repo)
    view.load_dungeon_session(dungeon)

    assert view._dungeon is dungeon
    assert view._state is not None
