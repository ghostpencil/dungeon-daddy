from __future__ import annotations


def _label(**kw):
    from dungeon_daddy.ui.fog_of_war import fog_of_war_label
    return fog_of_war_label(**kw)


# ---------------------------------------------------------------------------
# Visited destination shows its real name; unvisited shows "?"
# ---------------------------------------------------------------------------

def test_visited_room_shows_name():
    assert _label(room_id="r1", room_name="Cargo Bay", visited_rooms=["r1"]) == "Cargo Bay"


def test_unvisited_room_shows_question_mark():
    assert _label(room_id="r2", room_name="Cargo Bay", visited_rooms=["r1"]) == "?"
