"""Phase 16 — PlayView: DM conversation history tests."""
from __future__ import annotations

from unittest.mock import patch

from dungeon_daddy.data.models import (
    Connection,
    Dungeon,
    DungeonMeta,
    Level,
    Room,
    SessionState,
)
from dungeon_daddy.views.play_view import DMResult

# ---------------------------------------------------------------------------
# Factories (mirrors test_play_view.py)
# ---------------------------------------------------------------------------

def _room(id: str, x: int = 0, y: int = 0, name: str | None = None) -> Room:
    return Room(id=id, num=1, name=name or id, x=x, y=y, w=2, h=2, type="hall", note="")


def _conn(from_id: str, to_id: str) -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": "door", "note": ""})


def _level(rooms: list[Room], connections: list[Connection], level_id: int = 1) -> Level:
    return Level(
        id=level_id, name="L1", summary="", ecology="", loop="",
        loops=[],
        width=20, height=20, entries=[], rooms=rooms, connections=connections,
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
# Slice 3 — history accumulates across turns
# ---------------------------------------------------------------------------

def test_history_accumulates_across_turns(make_play_view):

    room = _room("r1", name="Guard Post")
    level = _level(rooms=[room], connections=[])
    st = _state(room_id="r1")
    view = make_play_view(dungeon=_dungeon([level]), state=st)

    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread_cls:
        mock_thread_cls.return_value.daemon = True
        view._on_chat_send("What traps are here?")

    assert len(view._dm_history) == 1
    assert view._dm_history[0].role == "user"
    assert view._dm_history[0].content == "What traps are here?"

    view._result_queue.put(DMResult(content="The pressure plate near the north door."))
    view.on_update(0)

    assert len(view._dm_history) == 2
    assert view._dm_history[1].role == "assistant"
    assert view._dm_history[1].content == "The pressure plate near the north door."

    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread_cls:
        mock_thread_cls.return_value.daemon = True
        view._on_chat_send("We disarm the trap.")

    assert len(view._dm_history) == 3
    assert view._dm_history[2].role == "user"

    view._result_queue.put(DMResult(content="The rogue steps forward carefully."))
    view.on_update(0)

    assert len(view._dm_history) == 4
    assert view._dm_history[3].role == "assistant"


# ---------------------------------------------------------------------------
# Slice 4 — oldest turn pair dropped when history exceeds 2 000 tokens
# ---------------------------------------------------------------------------

def test_history_compacted_when_over_budget(make_play_view):
    from dungeon_daddy.llm.provider import LLMMessage

    room = _room("r1", name="Guard Post")
    level = _level(rooms=[room], connections=[])
    st = _state(room_id="r1")
    view = make_play_view(dungeon=_dungeon([level]), state=st)

    # Pre-load history with two turn pairs that together exceed 2 000 tokens.
    # Each message content is 1 000 characters ≈ 250 tokens (len // 4).
    # Two pairs = 4 messages = ~1 000 tokens, still under budget.
    # Add a third pair to push it over 2 000.
    big = "x" * 1_200  # 1 200 chars → 300 tokens per message, 600 per pair
    view._dm_history = [
        LLMMessage(role="user",      content=big),  # pair A
        LLMMessage(role="assistant", content=big),
        LLMMessage(role="user",      content=big),  # pair B
        LLMMessage(role="assistant", content=big),
        LLMMessage(role="user",      content=big),  # pair C
        LLMMessage(role="assistant", content=big),
    ]
    # 6 × 300 tokens = 1 800 tokens — still under budget.
    # Add one more pair to push over 2 000 tokens.
    view._dm_history += [
        LLMMessage(role="user",      content=big),  # pair D
        LLMMessage(role="assistant", content=big),
    ]
    # 8 × 300 = 2 400 tokens — over budget.

    # Sending a new message should trigger compaction before the DM call.
    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread_cls:
        mock_thread_cls.return_value.daemon = True
        view._on_chat_send("New message.")

    # Oldest pair (A) should have been dropped; newer pairs preserved.
    # The new user message is appended last; history must not start with pair A.
    # Pair A was: index 0 (user big) and index 1 (assistant big) from the original.
    # After compaction, the first two messages should be pair B or later.
    assert len(view._dm_history) <= 7  # at most 6 old + 1 new user msg (pair A dropped)


# ---------------------------------------------------------------------------
# Slice 5 — history cleared on level change
# ---------------------------------------------------------------------------

def test_history_cleared_on_level_change(make_play_view):
    from dungeon_daddy.llm.provider import LLMMessage

    level1 = _level(rooms=[], connections=[], level_id=1)
    level2 = _level(rooms=[], connections=[], level_id=2)
    dungeon = _dungeon([level1, level2])
    st = _state()
    view = make_play_view(dungeon=dungeon, state=st)
    view._dm_history = [
        LLMMessage(role="user", content="Hello"),
        LLMMessage(role="assistant", content="Welcome."),
    ]

    view._on_level_change(+1)

    assert view._dm_history == []


# ---------------------------------------------------------------------------
# Slice 6 — /clear command resets history and confirms in chat
# ---------------------------------------------------------------------------

def test_clear_command_resets_history(make_play_view):
    from dungeon_daddy.llm.provider import LLMMessage

    room = _room("r1")
    level = _level(rooms=[room], connections=[])
    st = _state(room_id="r1")
    view = make_play_view(dungeon=_dungeon([level]), state=st)
    view._dm_history = [
        LLMMessage(role="user", content="Hello"),
        LLMMessage(role="assistant", content="Welcome."),
    ]

    view._on_chat_send("/clear")

    assert view._dm_history == []
    msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
    assert any("system" in role and "Conversation cleared" in text for role, text in msgs)


# ---------------------------------------------------------------------------
# Bug fix — room click must add user entry message to history
# ---------------------------------------------------------------------------

def test_room_click_adds_user_entry_message_to_history(make_play_view):
    """
    Clicking a room appends a user turn 'We enter <room>.' to _dm_history
    before spawning the DM thread.  This ensures proper user/assistant
    alternation and prevents the DM from continuing previous room context.
    """
    import arcade

    room = _room("r1", x=0, y=0, name="Guard Post")
    level = _level(rooms=[room], connections=[])
    st = _state()
    view = make_play_view(dungeon=_dungeon([level]), state=st)

    # Room r1 occupies cells (0,0)–(1,1).
    # origin_x = PANEL_CHAT_WIDTH(440) + PAD_MD(12) = 452
    # origin_y = PAD_MD(12)
    # cell_x = int((500 - 452) / 48) = 1  → in room (x=0, w=2) ✓
    # cell_y = int((60 - 12) / 48)  = 1  → in room (y=0, h=2) ✓
    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread_cls:
        mock_thread_cls.return_value.daemon = True
        view.on_mouse_press(500, 60, arcade.MOUSE_BUTTON_LEFT, 0)

    assert len(view._dm_history) == 1
    assert view._dm_history[0].role == "user"
    assert "Guard Post" in view._dm_history[0].content


def test_room_click_entry_message_precedes_dm_response(make_play_view):
    """
    After a full room-click cycle (click → DM response), the history has
    alternating user/assistant messages starting with the entry user turn.
    """
    import arcade

    room = _room("r1", x=0, y=0, name="Guard Post")
    level = _level(rooms=[room], connections=[])
    st = _state()
    view = make_play_view(dungeon=_dungeon([level]), state=st)

    with patch("dungeon_daddy.views.play_view.threading.Thread") as mock_thread_cls:
        mock_thread_cls.return_value.daemon = True
        view.on_mouse_press(500, 60, arcade.MOUSE_BUTTON_LEFT, 0)

    view._result_queue.put(DMResult(content="You step into the Guard Post."))
    view.on_update(0)

    assert len(view._dm_history) == 2
    assert view._dm_history[0].role == "user"
    assert view._dm_history[1].role == "assistant"
    assert view._dm_history[1].content == "You step into the Guard Post."
