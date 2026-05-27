"""Phase 17 — PlayView: loop activation system message tests."""
from __future__ import annotations

from dungeon_daddy.data.models import (
    Dungeon,
    DungeonMeta,
    Level,
    Loop,
    Room,
    SessionState,
)

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _room(id: str, name: str | None = None) -> Room:
    return Room(id=id, num=1, name=name or id, x=0, y=0, w=2, h=2, type="hall", note="")


def _loop(
    id: str = "loop1",
    pattern: str = "lock_key",
    explanation: str = "Find the key to unlock the door.",
    entry: str = "r_entry",
    goal: str = "r_goal",
    path_a: list[str] | None = None,
    path_b: list[str] | None = None,
) -> Loop:
    return Loop(
        id=id,
        pattern=pattern,
        note="",
        entry=entry,
        goal=goal,
        path_a=path_a or ["r_a1", "r_a2"],
        path_b=path_b or ["r_b1"],
        explanation=explanation,
    )


def _level(rooms: list[Room], loops: list[Loop]) -> Level:
    return Level(
        id=1, name="L1", summary="", ecology="", loop="",
        loops=loops,
        width=20, height=20, entries=[], rooms=rooms, connections=[],
    )


def _dungeon(levels: list[Level]) -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="Test", theme="t", setting="s", party="p", quest="q"),
        levels=levels,
    )


def _state() -> SessionState:
    return SessionState(
        dungeon_id="test", current_level_idx=0,
        visited_rooms=[], current_room_id=None,
    )


# ---------------------------------------------------------------------------
# Slice 1 — activate loop posts a system message
# ---------------------------------------------------------------------------

def test_activate_loop_posts_system_message(make_play_view):
    rooms = [
        _room("r_entry", "Entry Hall"),
        _room("r_goal", "Boss Chamber"),
        _room("r_a1", "Room A1"),
        _room("r_a2", "Room A2"),
        _room("r_b1", "Room B1"),
    ]
    lp = _loop()
    view = make_play_view(dungeon=_dungeon([_level(rooms, [lp])]), state=_state())

    view.on_activate_loop("loop1")

    view._chat.add_message.assert_called_once()
    role, _ = view._chat.add_message.call_args.args
    assert role == "system"


# ---------------------------------------------------------------------------
# Slice 2 — message contains the loop explanation
# ---------------------------------------------------------------------------

def test_system_message_contains_explanation(make_play_view):
    rooms = [
        _room("r_entry", "Entry Hall"), _room("r_goal", "Boss Chamber"),
        _room("r_a1", "Room A1"), _room("r_a2", "Room A2"), _room("r_b1", "Room B1"),
    ]
    lp = _loop(explanation="Locate the key and unlock the final door.")
    view = make_play_view(dungeon=_dungeon([_level(rooms, [lp])]), state=_state())

    view.on_activate_loop("loop1")

    _, text = view._chat.add_message.call_args.args
    assert "Locate the key and unlock the final door." in text


# ---------------------------------------------------------------------------
# Slice 3 — message contains entry and goal room names
# ---------------------------------------------------------------------------

def test_system_message_contains_entry_and_goal_names(make_play_view):
    rooms = [
        _room("r_entry", "Entry Hall"), _room("r_goal", "Boss Chamber"),
        _room("r_a1", "Room A1"), _room("r_a2", "Room A2"), _room("r_b1", "Room B1"),
    ]
    lp = _loop()
    view = make_play_view(dungeon=_dungeon([_level(rooms, [lp])]), state=_state())

    view.on_activate_loop("loop1")

    _, text = view._chat.add_message.call_args.args
    assert "Entry Hall" in text
    assert "Boss Chamber" in text


# ---------------------------------------------------------------------------
# Slice 4 — message contains path A as room names
# ---------------------------------------------------------------------------

def test_system_message_contains_path_a_as_room_names(make_play_view):
    rooms = [
        _room("r_entry", "Entry Hall"), _room("r_goal", "Boss Chamber"),
        _room("r_a1", "Armory"), _room("r_a2", "Trophy Room"), _room("r_b1", "Room B1"),
    ]
    lp = _loop(path_a=["r_a1", "r_a2"])
    view = make_play_view(dungeon=_dungeon([_level(rooms, [lp])]), state=_state())

    view.on_activate_loop("loop1")

    _, text = view._chat.add_message.call_args.args
    assert "Armory" in text
    assert "Trophy Room" in text


# ---------------------------------------------------------------------------
# Slice 5 — message contains path B as room names
# ---------------------------------------------------------------------------

def test_system_message_contains_path_b_as_room_names(make_play_view):
    rooms = [
        _room("r_entry", "Entry Hall"), _room("r_goal", "Boss Chamber"),
        _room("r_a1", "Room A1"), _room("r_a2", "Room A2"), _room("r_b1", "Catacombs"),
    ]
    lp = _loop(path_b=["r_b1"])
    view = make_play_view(dungeon=_dungeon([_level(rooms, [lp])]), state=_state())

    view.on_activate_loop("loop1")

    _, text = view._chat.add_message.call_args.args
    assert "Catacombs" in text


# ---------------------------------------------------------------------------
# Slice 6 — deactivate (None) posts a cleared message
# ---------------------------------------------------------------------------

def test_deactivate_loop_posts_cleared_message(make_play_view):
    view = make_play_view(dungeon=_dungeon([_level([], [])]), state=_state())

    view.on_activate_loop(None)

    view._chat.add_message.assert_called_once()
    role, text = view._chat.add_message.call_args.args
    assert role == "system"
    assert "cleared" in text.lower()


# ---------------------------------------------------------------------------
# Slice 7 — unknown room ID shown as the raw ID
# ---------------------------------------------------------------------------

def test_unknown_room_id_shown_as_id(make_play_view):
    rooms = [
        _room("r_entry", "Entry Hall"), _room("r_goal", "Boss Chamber"),
    ]
    lp = _loop(path_a=["unknown_room"], path_b=["also_unknown"])
    view = make_play_view(dungeon=_dungeon([_level(rooms, [lp])]), state=_state())

    view.on_activate_loop("loop1")

    _, text = view._chat.add_message.call_args.args
    assert "unknown_room" in text
    assert "also_unknown" in text


# ---------------------------------------------------------------------------
# Slice 8 — activate updates session state so LoopOverlay responds
# ---------------------------------------------------------------------------

def test_activate_loop_updates_session_state(make_play_view):
    rooms = [_room("r_entry", "Entry Hall"), _room("r_goal", "Boss Chamber")]
    lp = _loop()
    state = _state()
    view = make_play_view(dungeon=_dungeon([_level(rooms, [lp])]), state=state)

    view.on_activate_loop("loop1")

    assert state.active_loop_id == "loop1"


def test_deactivate_loop_clears_session_state(make_play_view):
    rooms = [_room("r_entry", "Entry Hall"), _room("r_goal", "Boss Chamber")]
    lp = _loop()
    state = _state()
    state.active_loop_id = "loop1"
    view = make_play_view(dungeon=_dungeon([_level(rooms, [lp])]), state=state)

    view.on_activate_loop(None)

    assert state.active_loop_id is None
