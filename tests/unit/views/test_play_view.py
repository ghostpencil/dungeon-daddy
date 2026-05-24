"""Tests for PlayView — DM threading and connection click behavior."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import arcade

from dungeon_daddy.data.models import (
    Connection,
    Dungeon,
    DungeonMeta,
    Entry,
    Level,
    Loop,
    Room,
    SessionState,
)
from dungeon_daddy.views.play_view import DMResult


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _room(id: str, x: int = 0, y: int = 0, name: str | None = None) -> Room:
    return Room(id=id, num=1, name=name or id, x=x, y=y, w=2, h=2, type="hall", note="")


def _conn(from_id: str, to_id: str, type: str = "door", note: str = "") -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": type, "note": note})


def _level(rooms: list[Room], connections: list[Connection], loops: list[Loop] | None = None, level_id: int = 1) -> Level:
    return Level(
        id=level_id, name="L1", summary="", ecology="", loop="",
        loops=loops or [],
        width=20, height=20, entries=[], rooms=rooms, connections=connections,
    )


def _dungeon(levels: list[Level]) -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="Test", theme="t", setting="s", party="p", quest="q"),
        levels=levels,
    )


def _saved_dungeon(levels: list[Level], save_name: str = "my_dungeon") -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="Test", theme="t", setting="s", party="p", quest="q", save_name=save_name),
        levels=levels,
    )


def _state(room_id: str | None = None) -> SessionState:
    return SessionState(dungeon_id="test", current_level_idx=0, visited_rooms=[], current_room_id=room_id)


# ---------------------------------------------------------------------------
# DM threading — on_update queue drain
# ---------------------------------------------------------------------------

def test_dm_result_appears_in_chat(make_play_view):
    view = make_play_view()
    view._result_queue.put(DMResult(content="Shadows shift around you."))
    view._llm_busy = True

    view.on_update(0)

    view._chat.add_message.assert_called_once_with("dm", "Shadows shift around you.")
    assert view._llm_busy is False


def test_dm_error_result_shows_error_bubble(make_play_view):
    view = make_play_view()
    view._result_queue.put(DMResult(content="", error="API timeout"))
    view._llm_busy = True

    view.on_update(0)

    msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
    assert any("system" in role and "API timeout" in text for role, text in msgs)
    assert view._llm_busy is False


def test_dm_error_result_shows_canonical_error_bubble(make_play_view):
    view = make_play_view()
    view._result_queue.put(DMResult(content="", error="API timeout"))
    view._llm_busy = True

    view.on_update(0)

    view._chat.add_message.assert_called_once_with(
        "system", "⚠ The dungeon is silent. (API timeout)"
    )
    assert view._llm_busy is False


def test_dm_error_result_clears_busy_flag(make_play_view):
    view = make_play_view()
    view._result_queue.put(DMResult(content="", error="any error"))
    view._llm_busy = True

    view.on_update(0)

    assert view._llm_busy is False


# ---------------------------------------------------------------------------
# DM threading — room click wiring
# ---------------------------------------------------------------------------

def test_room_click_spawns_dm_thread(make_play_view):
    room = _room("r1", x=0, y=0)
    level = _level(rooms=[room], connections=[])
    view = make_play_view(dungeon=_dungeon([level]), state=_state())
    view._renderer.hit_test_connection.return_value = None

    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread_cls:
        mock_thread_cls.return_value.daemon = True
        view.on_mouse_press(500, 10, arcade.MOUSE_BUTTON_LEFT, 0)

    mock_thread_cls.assert_called_once()
    assert view._llm_busy is True


def test_room_click_loads_room_memory_before_dm(make_play_view):
    room = _room("r1", x=0, y=0)
    level = _level(rooms=[room], connections=[], level_id=2)
    st = _state()
    st.dungeon_id = "my_dungeon"
    view = make_play_view(dungeon=_dungeon([level]), state=st)
    view._renderer.hit_test_connection.return_value = None

    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread_cls:
        mock_thread_cls.return_value.daemon = True
        view.on_mouse_press(500, 10, arcade.MOUSE_BUTTON_LEFT, 0)

    view._repo.load_room_memory.assert_called_once_with("my_dungeon", 2)


def test_llm_busy_guard_ignores_second_room_click(make_play_view):
    room = _room("r1", x=0, y=0)
    level = _level(rooms=[room], connections=[])
    view = make_play_view(dungeon=_dungeon([level]), state=_state())
    view._llm_busy = True
    view._renderer.hit_test_connection.return_value = None

    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread_cls:
        view.on_mouse_press(500, 10, arcade.MOUSE_BUTTON_LEFT, 0)

    mock_thread_cls.assert_not_called()


def test_room_click_with_empty_memory_still_spawns_dm_thread(make_play_view):
    """Contract: empty memory string does not block DM thread (SI-4)."""
    room = _room("r1", x=0, y=0)
    level = _level(rooms=[room], connections=[])
    view = make_play_view(dungeon=_dungeon([level]), state=_state())
    view._repo.load_room_memory.return_value = ""
    view._renderer.hit_test_connection.return_value = None

    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread_cls:
        mock_thread_cls.return_value.daemon = True
        view.on_mouse_press(500, 10, arcade.MOUSE_BUTTON_LEFT, 0)

    assert view._llm_busy is True
    mock_thread_cls.assert_called_once()


# ---------------------------------------------------------------------------
# /remember command
# ---------------------------------------------------------------------------

def test_remember_calls_append_room_event(make_play_view):
    room = _room("r1", name="Guard Post")
    level = _level(rooms=[room], connections=[], level_id=3)
    st = _state(room_id="r1")
    st.dungeon_id = "crypt"
    view = make_play_view(dungeon=_dungeon([level]), state=st)

    view._on_chat_send("/remember The party found a hidden door.")

    view._repo.append_room_event.assert_called_once_with(
        "crypt", 3, "r1", "Guard Post", "The party found a hidden door."
    )


def test_remember_does_not_set_llm_busy(make_play_view):
    room = _room("r1")
    level = _level(rooms=[room], connections=[])
    st = _state(room_id="r1")
    view = make_play_view(dungeon=_dungeon([level]), state=st)

    view._on_chat_send("/remember Something happened.")

    assert view._llm_busy is False


def test_remember_adds_system_confirmation_bubble(make_play_view):
    room = _room("r1")
    level = _level(rooms=[room], connections=[])
    st = _state(room_id="r1")
    view = make_play_view(dungeon=_dungeon([level]), state=st)

    view._on_chat_send("/remember Found a key.")

    msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
    assert any("system" in role for role, _ in msgs)


def test_remember_with_no_room_selected_shows_error(make_play_view):
    room = _room("r1")
    level = _level(rooms=[room], connections=[])
    st = _state(room_id=None)
    view = make_play_view(dungeon=_dungeon([level]), state=st)

    view._on_chat_send("/remember Nothing.")

    view._repo.append_room_event.assert_not_called()
    msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
    assert any("system" in role for role, _ in msgs)


# ---------------------------------------------------------------------------
# Map variant switcher
# ---------------------------------------------------------------------------

def test_set_map_renderer_updates_map_panel(make_play_view):
    from dungeon_daddy.map.tiles_renderer import TilesRenderer
    view = make_play_view()
    new_renderer = TilesRenderer(cell_px=48)

    view.set_map_renderer(new_renderer)

    assert view._renderer is new_renderer
    view._map.set_renderer.assert_called_once_with(new_renderer)


# ---------------------------------------------------------------------------
# on_hide_view — thread join
# ---------------------------------------------------------------------------

def test_on_hide_view_joins_active_thread(make_play_view):
    view = make_play_view()
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = True
    view._active_thread = mock_thread
    view._manager = MagicMock()

    view.on_hide_view()

    mock_thread.join.assert_called_once_with(timeout=3.0)


# ---------------------------------------------------------------------------
# E12 — connection click
# ---------------------------------------------------------------------------

def test_connection_click_logs_source_target_type_note(make_play_view):
    conn = _conn("room-a", "room-b", type="door", note="heavy oak")
    level = _level(rooms=[], connections=[conn])
    view = make_play_view(dungeon=_dungeon([level]), state=_state())
    view._renderer.hit_test_connection.return_value = conn

    view.on_mouse_press(500, 100, arcade.MOUSE_BUTTON_LEFT, 0)

    dm_msgs = [
        str(c.args[1])
        for c in view._chat.add_message.call_args_list
        if c.args[0] == "dm"
    ]
    # All connection details must appear in the same message
    assert any("room-a" in m and "room-b" in m and "door" in m and "heavy oak" in m for m in dm_msgs)


def test_connection_click_includes_loop_participation(make_play_view):
    conn = _conn("room-a", "room-b", type="corridor", note="")
    loop = Loop(
        id="L1", pattern="gauntlet", note="", entry="room-a", goal="room-b",
        path_a=[], path_b=[], rooms=["room-a", "room-b"],
    )
    level = _level(rooms=[], connections=[conn], loops=[loop])
    view = make_play_view(dungeon=_dungeon([level]), state=_state())
    view._renderer.hit_test_connection.return_value = conn

    view.on_mouse_press(500, 100, arcade.MOUSE_BUTTON_LEFT, 0)

    dm_msgs = [
        str(c.args[1])
        for c in view._chat.add_message.call_args_list
        if c.args[0] == "dm"
    ]
    assert any("L1" in m for m in dm_msgs)


def test_miss_on_everything_logs_nothing(make_play_view):
    conn = _conn("room-a", "room-b")
    level = _level(rooms=[], connections=[conn])
    view = make_play_view(dungeon=_dungeon([level]), state=_state())
    view._renderer.hit_test_connection.return_value = None

    view.on_mouse_press(500, 100, arcade.MOUSE_BUTTON_LEFT, 0)

    assert view._chat.add_message.call_count == 0


# ---------------------------------------------------------------------------
# Phase 9 — Edit Memory Overlay
# ---------------------------------------------------------------------------

def test_has_level_memory_false_when_repo_returns_empty(make_play_view):
    level = _level(rooms=[], connections=[], level_id=1)
    st = _state()
    st.dungeon_id = "test_dungeon"
    view = make_play_view(dungeon=_dungeon([level]), state=st)
    view._repo.load_room_memory.return_value = ""

    assert view.has_level_memory() is False


def test_has_level_memory_true_when_repo_returns_content(make_play_view):
    level = _level(rooms=[], connections=[], level_id=2)
    st = _state()
    st.dungeon_id = "test_dungeon"
    view = make_play_view(dungeon=_dungeon([level]), state=st)
    view._repo.load_room_memory.return_value = "The party found a secret door."

    assert view.has_level_memory() is True


def test_open_memory_overlay_loads_correct_memory(make_play_view):
    level = _level(rooms=[], connections=[], level_id=3)
    st = _state()
    st.dungeon_id = "my_dungeon"
    view = make_play_view(dungeon=_dungeon([level]), state=st)
    view._repo.load_room_memory.return_value = "Some memory text."

    view.open_memory_overlay()

    view._repo.load_room_memory.assert_called_with("my_dungeon", 3)


def test_save_memory_overlay_writes_content_and_closes(make_play_view):
    level = _level(rooms=[], connections=[], level_id=4)
    st = _state()
    st.dungeon_id = "castle"
    view = make_play_view(dungeon=_dungeon([level]), state=st)
    view._repo.load_room_memory.return_value = "Old memory."
    view.open_memory_overlay()
    view._overlay_content = "Updated memory."

    view.save_memory_overlay()

    view._repo.save_room_memory.assert_called_once_with("castle", 4, "Updated memory.")


def test_close_memory_overlay_does_not_save(make_play_view):
    level = _level(rooms=[], connections=[], level_id=5)
    st = _state()
    st.dungeon_id = "tower"
    view = make_play_view(dungeon=_dungeon([level]), state=st)
    view._repo.load_room_memory.return_value = "Memory content."
    view.open_memory_overlay()

    view.close_memory_overlay()

    view._repo.save_room_memory.assert_not_called()


# ---------------------------------------------------------------------------
# Stabilisation — memory button available on all floors
# ---------------------------------------------------------------------------

def test_memory_button_click_opens_overlay_on_floor_with_no_stored_memory(make_play_view):
    """Button click reaches open_memory_overlay even when the floor has no stored memory."""
    level1 = _level(rooms=[], connections=[], level_id=1)
    level2 = _level(rooms=[], connections=[], level_id=2)
    st = _state()
    st.dungeon_id = "my_dungeon"
    view = make_play_view(dungeon=_dungeon([level1, level2]), state=st)
    view._repo.load_room_memory.return_value = ""
    view._edit_memory_rect = (100.0, 100.0, 100.0, 24.0)

    view._on_level_change(+1)
    view._repo.load_room_memory.reset_mock()

    # Click inside the button rect (x=150, y=112 is inside (100,100,100,24))
    view.on_mouse_press(150.0, 112.0, arcade.MOUSE_BUTTON_LEFT, 0)

    # open_memory_overlay should have been called — it queries the repo for floor 2
    view._repo.load_room_memory.assert_called_once_with("my_dungeon", 2)


def test_memory_button_click_opens_overlay_on_first_floor_with_no_stored_memory(make_play_view):
    """Button click works on floor 1 even before any memory has been saved."""
    level = _level(rooms=[], connections=[], level_id=1)
    st = _state()
    st.dungeon_id = "dungeon_a"
    view = make_play_view(dungeon=_dungeon([level]), state=st)
    view._repo.load_room_memory.return_value = ""
    view._edit_memory_rect = (100.0, 100.0, 100.0, 24.0)

    view.on_mouse_press(150.0, 112.0, arcade.MOUSE_BUTTON_LEFT, 0)

    view._repo.load_room_memory.assert_called_once_with("dungeon_a", 1)


# ---------------------------------------------------------------------------
# F-31 — load_dungeon_transient / load_dungeon_session / _save_session
# ---------------------------------------------------------------------------

def test_load_dungeon_transient_sets_flag(make_play_view):
    level = _level(rooms=[], connections=[])
    view = make_play_view()

    view.load_dungeon_transient(_dungeon([level]))

    assert view._is_test_drive is True


def test_load_dungeon_transient_does_not_save_session(make_play_view):
    room = _room("r1", x=0, y=0)
    level = _level(rooms=[room], connections=[], level_id=1)
    dungeon = _dungeon([level])
    view = make_play_view()
    view._renderer.hit_test_connection.return_value = None
    view.load_dungeon_transient(dungeon)
    view._repo.reset_mock()

    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread_cls:
        mock_thread_cls.return_value.daemon = True
        view.on_mouse_press(500, 10, arcade.MOUSE_BUTTON_LEFT, 0)

    view.on_activate_loop("loop1")

    view._overlay_level_id = 1
    view._overlay_content = "some memory"
    view.save_memory_overlay()

    view._repo.save_session.assert_not_called()
    view._repo.save_room_memory.assert_called_once()


def test_load_dungeon_session_fresh_creates_state(make_play_view):
    level = _level(rooms=[], connections=[])
    dungeon = _saved_dungeon([level])
    view = make_play_view()
    view._repo.load_session.return_value = None

    view.load_dungeon_session(dungeon)

    assert view._state.dungeon_id == "my_dungeon"
    assert view._is_test_drive is False


def test_load_dungeon_session_resumes_existing(make_play_view):
    level1 = _level(rooms=[], connections=[], level_id=1)
    level2 = _level(rooms=[], connections=[], level_id=2)
    dungeon = _saved_dungeon([level1, level2])
    existing = SessionState(
        dungeon_id="my_dungeon",
        current_level_idx=1,
        current_room_id="r2",
        visited_rooms=["r1", "r2"],
    )
    view = make_play_view()
    view._repo.load_session.return_value = existing

    view.load_dungeon_session(dungeon)

    assert view._state.current_level_idx == 1
    assert view._state.current_room_id == "r2"
    assert "r1" in view._state.visited_rooms


def test_load_dungeon_session_saves_on_room_click(make_play_view):
    room = _room("r1", x=0, y=0)
    level = _level(rooms=[room], connections=[], level_id=1)
    dungeon = _saved_dungeon([level])
    view = make_play_view()
    view._repo.load_session.return_value = None
    view._renderer.hit_test_connection.return_value = None

    view.load_dungeon_session(dungeon)
    view._repo.reset_mock()

    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread_cls:
        mock_thread_cls.return_value.daemon = True
        view.on_mouse_press(500, 10, arcade.MOUSE_BUTTON_LEFT, 0)

    view._repo.save_session.assert_called()


def test_load_dungeon_session_saves_on_hide(make_play_view):
    level = _level(rooms=[], connections=[])
    dungeon = _saved_dungeon([level])
    view = make_play_view()
    view._repo.load_session.return_value = None
    view._manager = MagicMock()

    view.load_dungeon_session(dungeon)
    view._repo.reset_mock()
    view.on_hide_view()

    view._repo.save_session.assert_called()


# ---------------------------------------------------------------------------
# SI-3 — View state mutations (assert fields directly, not just mock calls)
# ---------------------------------------------------------------------------

def test_on_chat_send_appends_to_dm_history(make_play_view):
    room = _room("r1", x=0, y=0)
    level = _level(rooms=[room], connections=[])
    st = _state(room_id="r1")
    view = make_play_view(dungeon=_dungeon([level]), state=st)
    view._dm_history = []

    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread:
        mock_thread.return_value.daemon = True
        view._on_chat_send("hello from GM")

    assert len(view._dm_history) == 1
    assert view._dm_history[0].role == "user"
    assert view._dm_history[0].content == "hello from GM"


def test_on_chat_send_sets_llm_busy(make_play_view):
    room = _room("r1", x=0, y=0)
    level = _level(rooms=[room], connections=[])
    st = _state(room_id="r1")
    view = make_play_view(dungeon=_dungeon([level]), state=st)
    view._llm_busy = False

    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread:
        mock_thread.return_value.daemon = True
        view._on_chat_send("hello")

    assert view._llm_busy is True


def test_on_chat_send_while_busy_active_thread_unchanged(make_play_view):
    room = _room("r1", x=0, y=0)
    level = _level(rooms=[room], connections=[])
    st = _state(room_id="r1")
    view = make_play_view(dungeon=_dungeon([level]), state=st)
    existing_thread = MagicMock()
    view._active_thread = existing_thread
    view._llm_busy = True

    view._on_chat_send("second message")

    assert view._active_thread is existing_thread


def test_dm_result_appends_to_dm_history(make_play_view):
    view = make_play_view()
    view._dm_history = []
    view._result_queue.put(DMResult(content="You see a door."))
    view._llm_busy = True

    view.on_update(0)

    assert len(view._dm_history) == 1
    assert view._dm_history[0].role == "assistant"
    assert view._dm_history[0].content == "You see a door."
