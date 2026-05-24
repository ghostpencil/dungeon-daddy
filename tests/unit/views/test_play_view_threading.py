"""Thread lifecycle contract for PlayView.

Tests that the _llm_busy guard works with real threads (not mocked threading).
"""
from __future__ import annotations

import queue
import time
from unittest.mock import MagicMock

from dungeon_daddy.data.models import (
    Connection,
    Dungeon,
    DungeonMeta,
    Level,
    Room,
    SessionState,
)
from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
from dungeon_daddy.llm.provider import LLMMessage
from dungeon_daddy.views.play_view import PlayView


# ---------------------------------------------------------------------------
# Stub providers
# ---------------------------------------------------------------------------

class _SlowProvider:
    """Blocks for 100 ms then returns a fixed string. Counts calls."""

    def __init__(self) -> None:
        self.call_count = 0

    def complete(self, messages: list[LLMMessage], system: str = "", max_tokens: int = 1024) -> str:
        self.call_count += 1
        time.sleep(0.1)
        return "You see a door."

    def stream(self, messages, system="", max_tokens=1024):
        yield "You see a door."

    @property
    def model_id(self) -> str:
        return "slow-stub"


class _FastProvider:
    """Returns immediately. Counts calls."""

    def __init__(self) -> None:
        self.call_count = 0

    def complete(self, messages: list[LLMMessage], system: str = "", max_tokens: int = 1024) -> str:
        self.call_count += 1
        return "All clear."

    def stream(self, messages, system="", max_tokens=1024):
        yield "All clear."

    @property
    def model_id(self) -> str:
        return "fast-stub"


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _room(id: str = "r1") -> Room:
    return Room(id=id, num=1, name=id, x=0, y=0, w=2, h=2, type="hall", note="")


def _level(room: Room) -> Level:
    return Level(
        id=1, name="L1", summary="", ecology="", loop="",
        loops=[], width=20, height=20, entries=[],
        rooms=[room], connections=[],
    )


def _dungeon(level: Level) -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q"),
        levels=[level],
    )


def _make_view(provider: object) -> PlayView:
    room = _room()
    level = _level(room)
    dungeon = _dungeon(level)

    view = PlayView.__new__(PlayView)
    view._dungeon = dungeon
    view._state = SessionState(
        dungeon_id="test", current_level_idx=0,
        visited_rooms=[], current_room_id="r1",
    )
    view.window = MagicMock()
    view._menu_bar = MagicMock()
    view._map = MagicMock()
    view._chat = MagicMock()
    view._renderer = MagicMock()
    view._repo = MagicMock()
    view._repo.load_room_memory.return_value = ""
    view._result_queue = queue.Queue()
    view._llm_busy = False
    view._active_thread = None
    view._dm_history = []
    view._dm_agent = DungeonMasterAgent(provider)
    return view


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_busy_flag_cleared_after_thread_completes():
    """_llm_busy is False after the thread finishes — cleared in the thread itself."""
    provider = _FastProvider()
    view = _make_view(provider)
    room = view._dungeon.levels[0].rooms[0]
    level = view._dungeon.levels[0]

    view._spawn_dm_thread(room, level)
    assert view._active_thread is not None
    view._active_thread.join(timeout=5.0)

    # No on_update call — the thread must clear the flag itself
    assert view._llm_busy is False


def test_second_send_while_thread_running_is_dropped():
    """A second _spawn_dm_thread call while the first thread runs is silently dropped."""
    provider = _SlowProvider()
    view = _make_view(provider)
    room = view._dungeon.levels[0].rooms[0]
    level = view._dungeon.levels[0]

    view._spawn_dm_thread(room, level)   # first — thread starts, _llm_busy = True
    view._spawn_dm_thread(room, level)   # second — dropped because busy
    view._active_thread.join(timeout=5.0)

    assert provider.call_count == 1
