"""Phase 16 — PlayView: [REMEMBER] tag extraction and auto-remember tests."""
from __future__ import annotations

from dungeon_daddy.data.models import (
    Dungeon,
    DungeonMeta,
    Level,
    Room,
    SessionState,
)
from dungeon_daddy.views.play_view import DMResult


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _room(id: str, name: str | None = None) -> Room:
    return Room(id=id, num=1, name=name or id, x=0, y=0, w=2, h=2, type="hall", note="")


def _level(rooms: list[Room], level_id: int = 1) -> Level:
    return Level(
        id=level_id, name="L1", summary="", ecology="", loop="",
        loops=[], width=20, height=20, entries=[], rooms=rooms, connections=[],
    )


def _dungeon(levels: list[Level]) -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="Test", theme="t", setting="s", party="p", quest="q"),
        levels=levels,
    )


def _state(room_id: str | None = None) -> SessionState:
    return SessionState(
        dungeon_id="test", current_level_idx=0,
        visited_rooms=[], current_room_id=room_id,
    )


# ---------------------------------------------------------------------------
# Slice 7 — _extract_remember: tag found
# ---------------------------------------------------------------------------

def test_extract_remember_found(make_play_view):
    view = make_play_view()
    text = "The shadows deepen. [REMEMBER: The party found the secret door.]"

    remembered, cleaned = view._extract_remember(text)

    assert remembered == "The party found the secret door."
    assert "[REMEMBER" not in cleaned


# ---------------------------------------------------------------------------
# Slice 8 — _extract_remember: tag absent
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Slice 8b — tag stripped cleanly from response
# ---------------------------------------------------------------------------

def test_extract_remember_strips_tag_from_response(make_play_view):
    view = make_play_view()
    text = "The rogue disarms the trap. [REMEMBER: Trap disarmed in Guard Post.] Well done."

    _, cleaned = view._extract_remember(text)

    assert "[REMEMBER" not in cleaned
    assert "rogue disarms" in cleaned


# ---------------------------------------------------------------------------
# Slice 9 — auto-remember writes repo event
# ---------------------------------------------------------------------------

def test_auto_remember_writes_room_event(make_play_view):
    room = _room("r1", name="Guard Post")
    level = _level(rooms=[room], level_id=3)
    st = _state(room_id="r1")
    st.dungeon_id = "crypt"
    view = make_play_view(dungeon=_dungeon([level]), state=st)

    response = "Well done. [REMEMBER: The party disarmed the pressure plate.]"
    view._result_queue.put(DMResult(content=response))
    view.on_update(0)

    view._repo.append_room_event.assert_called_once_with(
        "crypt", 3, "r1", "Guard Post", "The party disarmed the pressure plate."
    )


# ---------------------------------------------------------------------------
# Slice 10 — auto-remember posts system message
# ---------------------------------------------------------------------------

def test_auto_remember_posts_system_message(make_play_view):
    room = _room("r1", name="Guard Post")
    level = _level(rooms=[room], level_id=1)
    st = _state(room_id="r1")
    view = make_play_view(dungeon=_dungeon([level]), state=st)

    response = "The shadows shift. [REMEMBER: The party found a hidden lever.]"
    view._result_queue.put(DMResult(content=response))
    view.on_update(0)

    msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
    assert any(
        "system" in role and "Noted" in text and "hidden lever" in text
        for role, text in msgs
    )


# ---------------------------------------------------------------------------
# No-tag response is unchanged
# ---------------------------------------------------------------------------

def test_no_tag_response_displayed_as_is(make_play_view):
    room = _room("r1")
    level = _level(rooms=[room])
    st = _state(room_id="r1")
    view = make_play_view(dungeon=_dungeon([level]), state=st)

    response = "The guards stir in their sleep."
    view._result_queue.put(DMResult(content=response))
    view.on_update(0)

    view._repo.append_room_event.assert_not_called()
    dm_msgs = [c.args[1] for c in view._chat.add_message.call_args_list if c.args[0] == "dm"]
    assert dm_msgs == ["The guards stir in their sleep."]
