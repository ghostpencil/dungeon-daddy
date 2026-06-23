"""Tests for Phase 50 visual-verify fix — disambiguated exit noun labels.

Same-type exits ('Door' x2) are disambiguated without leaking undiscovered
rooms: an unexplored exit shows a compass direction; once the destination is
visited the label upgrades to the room name.
"""
from __future__ import annotations

from dungeon_daddy.data.models import Room
from dungeon_daddy.rpg.exit_labels import compass_direction, exit_noun_label


def _room(rid: str, name: str, x: int, y: int, w: int = 2, h: int = 2) -> Room:
    return Room(id=rid, num=1, name=name, x=x, y=y, w=w, h=h, type="room", note="")


# ---------------------------------------------------------------------------
# compass_direction — grid convention: +x = east, +y = south (north is up)
# ---------------------------------------------------------------------------

class TestCompassDirection:
    def test_east(self):
        assert compass_direction(_room("a", "A", 0, 0), _room("b", "B", 10, 0)) == "east"

    def test_west(self):
        assert compass_direction(_room("a", "A", 10, 0), _room("b", "B", 0, 0)) == "west"

    def test_north(self):
        assert compass_direction(_room("a", "A", 0, 10), _room("b", "B", 0, 0)) == "north"

    def test_south(self):
        assert compass_direction(_room("a", "A", 0, 0), _room("b", "B", 0, 10)) == "south"

    def test_dominant_axis_wins(self):
        # Larger horizontal delta than vertical -> east, not south.
        assert compass_direction(_room("a", "A", 0, 0), _room("b", "B", 10, 3)) == "east"

    def test_coincident_centers_returns_none(self):
        assert compass_direction(_room("a", "A", 0, 0), _room("b", "B", 0, 0)) is None


# ---------------------------------------------------------------------------
# exit_noun_label — visited -> room name; unexplored -> compass direction
# ---------------------------------------------------------------------------

_FROM = _room("r1", "Forge Floor", 0, 0)
_DEST = _room("r2", "Sand-Choked Gearworks", 10, 0)
_ROOMS = {"r1": _FROM, "r2": _DEST}


def _exit(**kw) -> dict:
    e = {"exit_id": "e1", "label": "Door", "status": "open", "to_room_id": "r2"}
    e.update(kw)
    return e


class TestExitNounLabel:
    def test_unexplored_destination_shows_compass_direction(self):
        label = exit_noun_label(
            _exit(), from_room=_FROM, rooms_by_id=_ROOMS, visited_rooms=set()
        )
        assert label == "Door East"

    def test_visited_destination_shows_room_name(self):
        label = exit_noun_label(
            _exit(), from_room=_FROM, rooms_by_id=_ROOMS, visited_rooms={"r2"}
        )
        assert label == "Door -> Sand-Choked Gearworks"

    def test_missing_destination_geometry_falls_back_to_base_label(self):
        # Cross-level exit: destination not in the current level's room map.
        label = exit_noun_label(
            _exit(to_room_id="other-level-room"),
            from_room=_FROM, rooms_by_id=_ROOMS, visited_rooms=set(),
        )
        assert label == "Door"

    def test_no_from_room_falls_back_to_base_label(self):
        label = exit_noun_label(
            _exit(), from_room=None, rooms_by_id=_ROOMS, visited_rooms=set()
        )
        assert label == "Door"


# ---------------------------------------------------------------------------
# Revealed lock state — a locked/blocked exit is marked with a lock glyph
# ---------------------------------------------------------------------------

class TestLockedExitMarker:
    def test_locked_visited_exit_is_prefixed_with_lock_glyph(self):
        from dungeon_daddy.rpg.exit_labels import LOCK_PREFIX

        label = exit_noun_label(
            _exit(status="locked"),
            from_room=_FROM, rooms_by_id=_ROOMS, visited_rooms={"r2"},
        )
        assert label == f"{LOCK_PREFIX}Door -> Sand-Choked Gearworks"

    def test_locked_unvisited_exit_keeps_direction_under_lock_glyph(self):
        from dungeon_daddy.rpg.exit_labels import LOCK_PREFIX

        label = exit_noun_label(
            _exit(status="locked"),
            from_room=_FROM, rooms_by_id=_ROOMS, visited_rooms=set(),
        )
        assert label == f"{LOCK_PREFIX}Door East"

    def test_open_exit_has_no_lock_glyph(self):
        from dungeon_daddy.rpg.exit_labels import LOCK_PREFIX

        label = exit_noun_label(
            _exit(status="open"),
            from_room=_FROM, rooms_by_id=_ROOMS, visited_rooms={"r2"},
        )
        assert LOCK_PREFIX not in label

    def test_one_way_exit_is_not_marked_locked(self):
        from dungeon_daddy.rpg.exit_labels import LOCK_PREFIX

        label = exit_noun_label(
            _exit(status="one_way"),
            from_room=_FROM, rooms_by_id=_ROOMS, visited_rooms={"r2"},
        )
        assert LOCK_PREFIX not in label
