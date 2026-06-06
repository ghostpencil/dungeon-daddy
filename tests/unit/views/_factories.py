"""Shared model factories for play_view unit tests."""
from __future__ import annotations

from dungeon_daddy.data.models import Dungeon, DungeonMeta, SessionState


def _dungeon(levels: list) -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="Test", theme="t", setting="s", party="p", quest="q"),
        levels=levels,
    )


def _state(room_id: str | None = None) -> SessionState:
    return SessionState(
        dungeon_id="test", current_level_idx=0,
        visited_rooms=[], current_room_id=room_id,
    )
