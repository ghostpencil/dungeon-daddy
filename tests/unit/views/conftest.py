from __future__ import annotations

import queue
from unittest.mock import MagicMock

import pytest

from dungeon_daddy.data.models import Dungeon, SessionState
from dungeon_daddy.views.play_view import PlayView


@pytest.fixture
def make_play_view():
    def _factory(dungeon: Dungeon | None = None, state: SessionState | None = None) -> PlayView:
        view = PlayView.__new__(PlayView)
        view._dungeon = dungeon
        view._state = state
        view.window = MagicMock()
        view._menu_bar = MagicMock()
        view._menu_bar.handle_click.return_value = False
        view._map = MagicMock()
        view._map.pan_offset = (0, 0)
        view._map.zoom_level = 1.0
        view._map.handle_mouse_press.return_value = False
        view._chat = MagicMock()
        view._renderer = MagicMock()
        view._dm_agent = MagicMock()
        view._repo = MagicMock()
        view._repo.load_room_memory.return_value = ""
        view._result_queue = queue.Queue()
        view._llm_busy = False
        view._active_thread = None
        view._dm_history = []
        view._has_memory = False
        view._edit_memory_rect = None
        view._overlay_open = False
        view._overlay_widgets = []
        view._overlay_input = None
        view._overlay_level_id = None
        view._overlay_content = None
        view._is_test_drive = False
        return view
    return _factory
