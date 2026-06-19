"""Tests for level-browse behavior in PlayView (Slice 0 — Phase 49).

The ▲▼ stepper arrows browse the map view only. They must not mutate
the party's canonical session fields (current_level_idx, current_room_id).
"""
from __future__ import annotations

from dungeon_daddy.data.models import Level, Loop, Room, SessionState
from tests.unit.views._factories import _dungeon, _state


def _room(id: str = "r1") -> Room:
    return Room(id=id, num=1, name=id, x=0, y=0, w=2, h=2, type="hall", note="")


def _level(level_id: int = 1) -> Level:
    return Level(
        id=level_id, name=f"Level {level_id}", summary="", ecology="", loop="",
        loops=[], width=20, height=20, entries=[], rooms=[_room()], connections=[],
    )


# ---------------------------------------------------------------------------
# Behavior A — browsing does not mutate party session state
# ---------------------------------------------------------------------------

def test_browse_does_not_change_party_level(make_play_view) -> None:
    """Stepping the map stepper must not update current_level_idx."""
    dungeon = _dungeon([_level(1), _level(2)])
    state = _state(room_id="r1")  # party on level 0

    view = make_play_view(dungeon=dungeon, state=state)
    view._viewed_level_idx = 0

    view._on_level_change(+1)

    assert view._state.current_level_idx == 0


def test_browse_does_not_clear_party_room(make_play_view) -> None:
    """Stepping the map stepper must not wipe current_room_id."""
    dungeon = _dungeon([_level(1), _level(2)])
    state = _state(room_id="r1")

    view = make_play_view(dungeon=dungeon, state=state)
    view._viewed_level_idx = 0

    view._on_level_change(+1)

    assert view._state.current_room_id == "r1"


def test_browse_advances_viewed_level_idx(make_play_view) -> None:
    """Stepping up increments the view-only viewed_level_idx."""
    dungeon = _dungeon([_level(1), _level(2)])
    state = _state(room_id="r1")

    view = make_play_view(dungeon=dungeon, state=state)
    view._viewed_level_idx = 0

    view._on_level_change(+1)

    assert view._viewed_level_idx == 1


def test_browse_clamps_at_last_level(make_play_view) -> None:
    """Stepping past the last level is a no-op."""
    dungeon = _dungeon([_level(1), _level(2)])
    state = _state(room_id="r1")

    view = make_play_view(dungeon=dungeon, state=state)
    view._viewed_level_idx = 1  # already at last level

    view._on_level_change(+1)

    assert view._viewed_level_idx == 1
    assert view._state.current_level_idx == 0
