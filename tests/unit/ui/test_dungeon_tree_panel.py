"""Tests for DungeonTreePanel validation header display and loop path colouring."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from dungeon_daddy.data.models import (
    Dungeon,
    DungeonMeta,
    Level,
    Loop,
    Room,
    ValidationResult,
)
from dungeon_daddy.ui.panels.dungeon_tree_panel import DungeonTreePanel
from dungeon_daddy.ui.theme import AMBER, INDIGO, INK_3, TEAL, VIOLET


@pytest.fixture()
def panel() -> DungeonTreePanel:
    p = DungeonTreePanel()
    p.set_bounds(0, 0, 200, 600)
    return p


def _draw_text_calls(panel: DungeonTreePanel) -> list[str]:
    """Return all text strings passed to arcade.draw_text during draw()."""
    with patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line"), \
         patch("arcade.draw_text") as mock_text, \
         patch("dungeon_daddy.ui.panels.dungeon_tree_panel.draw_kicker"):
        panel.draw()
    return [c.args[0] for c in mock_text.call_args_list]


def _draw_text_call_kwargs(panel: DungeonTreePanel) -> list[dict]:
    """Return text + color (positional args 0 and 1) for each arcade.draw_text call."""
    with patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line"), \
         patch("arcade.draw_text") as mock_text, \
         patch("dungeon_daddy.ui.panels.dungeon_tree_panel.draw_kicker"):
        panel.draw()
    return [{"text": c.args[0], "color": c.args[3]} for c in mock_text.call_args_list]


# ---------------------------------------------------------------------------
# Slice 1 — valid result shows "✓ validated" in TEAL
# ---------------------------------------------------------------------------

def test_valid_result_shows_checkmark(panel: DungeonTreePanel) -> None:
    """set_validation with is_valid=True → header draws '✓ validated' in TEAL."""
    panel.set_validation(ValidationResult(is_valid=True))
    calls = _draw_text_call_kwargs(panel)
    matching = [c for c in calls if "✓ validated" in c["text"]]
    assert matching, "Expected '✓ validated' text to be drawn"
    assert matching[0]["color"] == TEAL


# ---------------------------------------------------------------------------
# Slice 2 — invalid result shows "⚠ N issues" in AMBER
# ---------------------------------------------------------------------------

def test_invalid_result_shows_issue_count(panel: DungeonTreePanel) -> None:
    """set_validation with 2 errors → header draws '⚠ 2 issues' in AMBER."""
    panel.set_validation(ValidationResult(is_valid=False, errors=["e1", "e2"]))
    calls = _draw_text_call_kwargs(panel)
    matching = [c for c in calls if "⚠" in c["text"]]
    assert matching, "Expected '⚠ N issues' text to be drawn"
    assert "2 issues" in matching[0]["text"]
    assert matching[0]["color"] == AMBER


# ---------------------------------------------------------------------------
# Slice 3 — None clears the validation display
# ---------------------------------------------------------------------------

def test_none_validation_shows_nothing(panel: DungeonTreePanel) -> None:
    """set_validation(None) → no '✓' or '⚠' text drawn."""
    panel.set_validation(None)
    texts = _draw_text_calls(panel)
    assert not any("✓" in t or "⚠" in t for t in texts)


# ---------------------------------------------------------------------------
# Helpers and fixtures for loop path colouring tests
# ---------------------------------------------------------------------------

def _make_room(room_id: str, num: int) -> Room:
    return Room(id=room_id, num=num, name=f"Room {room_id}", x=0, y=0, w=1, h=1, type="room", note="")


def _make_dungeon(rooms: list[Room], loop: Loop) -> Dungeon:
    level = Level(
        id=1, name="Test Level", summary="", ecology="", loop="",
        loops=[loop], width=10, height=10, entries=[],
        rooms=rooms, connections=[],
    )
    meta = DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q")
    return Dungeon(meta=meta, levels=[level])


def _room_text_calls(panel: DungeonTreePanel) -> list[dict]:
    """Return {text, color} for every arcade.draw_text call during draw()."""
    with patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_rect_outline"), \
         patch("arcade.draw_line"), \
         patch("arcade.draw_text") as mock_text, \
         patch("dungeon_daddy.ui.panels.dungeon_tree_panel.draw_kicker"):
        panel.draw()
    return [{"text": c.args[0], "color": c.args[3]} for c in mock_text.call_args_list]


# ---------------------------------------------------------------------------
# Slice 4 — Path A room: ▶ icon, TEAL text
# ---------------------------------------------------------------------------

def test_path_a_room_has_arrow_icon_and_teal_text() -> None:
    """Room only in path_a → drawn with ▶ icon and TEAL colour."""
    loop = Loop(id="lp1", pattern="x", note="", entry="R1", goal="R2",
                path_a=["R1", "R2"], path_b=["R3"])
    rooms = [_make_room("R1", 1), _make_room("R2", 2), _make_room("R3", 3)]
    dungeon = _make_dungeon(rooms, loop)

    p = DungeonTreePanel()
    p.set_bounds(0, 0, 200, 600)
    p.set_dungeon(dungeon, expand_all=True)
    p.set_active_loop(loop)

    calls = _room_text_calls(p)
    r1_calls = [c for c in calls if "R1" in c["text"]]
    assert r1_calls, "Expected draw_text call mentioning R1"
    assert "▶" in r1_calls[0]["text"], f"Expected ▶ icon, got: {r1_calls[0]['text']}"
    assert r1_calls[0]["color"] == TEAL, f"Expected TEAL, got: {r1_calls[0]['color']}"


# ---------------------------------------------------------------------------
# Slice 5 — Path B room: ◇ icon, VIOLET text
# ---------------------------------------------------------------------------

def test_path_b_room_has_diamond_icon_and_violet_text() -> None:
    """Room only in path_b → drawn with ◇ icon and VIOLET colour."""
    loop = Loop(id="lp1", pattern="x", note="", entry="R1", goal="R2",
                path_a=["R1"], path_b=["R3"])
    rooms = [_make_room("R1", 1), _make_room("R2", 2), _make_room("R3", 3)]
    dungeon = _make_dungeon(rooms, loop)

    p = DungeonTreePanel()
    p.set_bounds(0, 0, 200, 600)
    p.set_dungeon(dungeon, expand_all=True)
    p.set_active_loop(loop)

    calls = _room_text_calls(p)
    r3_calls = [c for c in calls if "R3" in c["text"]]
    assert r3_calls, "Expected draw_text call mentioning R3"
    assert "◇" in r3_calls[0]["text"], f"Expected ◇ icon, got: {r3_calls[0]['text']}"
    assert r3_calls[0]["color"] == VIOLET, f"Expected VIOLET, got: {r3_calls[0]['color']}"


# ---------------------------------------------------------------------------
# Slice 6 — Both paths: ◆ icon, INDIGO text
# ---------------------------------------------------------------------------

def test_both_paths_room_has_filled_diamond_and_indigo_text() -> None:
    """Room in both path_a and path_b → drawn with ◆ icon and INDIGO colour."""
    loop = Loop(id="lp1", pattern="x", note="", entry="R1", goal="R2",
                path_a=["R1", "R2"], path_b=["R2", "R3"])
    rooms = [_make_room("R1", 1), _make_room("R2", 2), _make_room("R3", 3)]
    dungeon = _make_dungeon(rooms, loop)

    p = DungeonTreePanel()
    p.set_bounds(0, 0, 200, 600)
    p.set_dungeon(dungeon, expand_all=True)
    p.set_active_loop(loop)

    calls = _room_text_calls(p)
    r2_calls = [c for c in calls if "R2" in c["text"]]
    assert r2_calls, "Expected draw_text call mentioning R2"
    assert "◆" in r2_calls[0]["text"], f"Expected ◆ icon, got: {r2_calls[0]['text']}"
    assert r2_calls[0]["color"] == INDIGO, f"Expected INDIGO, got: {r2_calls[0]['color']}"


# ---------------------------------------------------------------------------
# Slice 7 — Neither path: ▢ icon, INK_3 text
# ---------------------------------------------------------------------------

def test_neither_path_room_has_square_icon_and_ink3_text() -> None:
    """Room in neither path → drawn with ▢ icon and INK_3 colour."""
    loop = Loop(id="lp1", pattern="x", note="", entry="R1", goal="R2",
                path_a=["R1"], path_b=["R2"])
    rooms = [_make_room("R1", 1), _make_room("R2", 2), _make_room("R3", 3)]
    dungeon = _make_dungeon(rooms, loop)

    p = DungeonTreePanel()
    p.set_bounds(0, 0, 200, 600)
    p.set_dungeon(dungeon, expand_all=True)
    p.set_active_loop(loop)

    calls = _room_text_calls(p)
    r3_calls = [c for c in calls if "R3" in c["text"]]
    assert r3_calls, "Expected draw_text call mentioning R3"
    assert "▢" in r3_calls[0]["text"], f"Expected ▢ icon, got: {r3_calls[0]['text']}"
    assert r3_calls[0]["color"] == INK_3, f"Expected INK_3, got: {r3_calls[0]['color']}"


# ---------------------------------------------------------------------------
# Slice 8 — set_active_loop(None) clears all tinting
# ---------------------------------------------------------------------------

def test_no_active_loop_all_rooms_use_default_icon_and_ink3() -> None:
    """set_active_loop(None) → every room uses ▢ icon and INK_3 colour."""
    loop = Loop(id="lp1", pattern="x", note="", entry="R1", goal="R2",
                path_a=["R1"], path_b=["R2"])
    rooms = [_make_room("R1", 1), _make_room("R2", 2)]
    dungeon = _make_dungeon(rooms, loop)

    p = DungeonTreePanel()
    p.set_bounds(0, 0, 200, 600)
    p.set_dungeon(dungeon, expand_all=True)
    p.set_active_loop(None)

    calls = _room_text_calls(p)
    room_calls = [c for c in calls if "R1" in c["text"] or "R2" in c["text"]]
    assert room_calls, "Expected room text calls"
    for c in room_calls:
        assert "▢" in c["text"], f"Expected ▢ icon with no loop, got: {c['text']}"
        assert c["color"] == INK_3, f"Expected INK_3 with no loop, got: {c['color']}"


# ---------------------------------------------------------------------------
# Slice 9 — expand_level adds level index to expanded set
# ---------------------------------------------------------------------------

def _make_simple_dungeon(num_levels: int = 1) -> Dungeon:
    levels = [
        Level(id=i + 1, name=f"L{i + 1}", summary="", ecology="", loop="",
              width=10, height=10, entries=[], rooms=[], connections=[])
        for i in range(num_levels)
    ]
    meta = DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q")
    return Dungeon(meta=meta, levels=levels)


def test_expand_level_makes_level_expanded(panel: DungeonTreePanel) -> None:
    panel.set_dungeon(_make_simple_dungeon())
    assert 0 not in panel._expanded

    panel.expand_level(0)

    assert 0 in panel._expanded


def test_expand_level_does_not_clear_other_expanded(panel: DungeonTreePanel) -> None:
    panel.set_dungeon(_make_simple_dungeon(num_levels=3), expand_all=True)
    panel.expand_level(2)

    assert panel._expanded == {0, 1, 2}


# ---------------------------------------------------------------------------
# Slice 10 — handle_click toggles level row
# ---------------------------------------------------------------------------

def test_handle_click_level_row_expands_collapsed_level(panel: DungeonTreePanel) -> None:
    from dungeon_daddy.ui.panels.dungeon_tree_panel import HEADER_H, ROW_H
    panel.set_dungeon(_make_simple_dungeon())
    # panel bounds: x=0, y=0, w=200, h=600
    # tree_top = 600 - 38 = 562; first level row spans [562-26, 562] = [536, 562]
    row_y = panel._h - HEADER_H - ROW_H / 2  # centre of first row
    result = panel.handle_click(50, row_y)

    assert result is True
    assert 0 in panel._expanded


def test_handle_click_level_row_collapses_expanded_level(panel: DungeonTreePanel) -> None:
    from dungeon_daddy.ui.panels.dungeon_tree_panel import HEADER_H, ROW_H
    panel.set_dungeon(_make_simple_dungeon(), expand_all=True)
    row_y = panel._h - HEADER_H - ROW_H / 2
    result = panel.handle_click(50, row_y)

    assert result is True
    assert 0 not in panel._expanded


def test_handle_click_outside_x_bounds_returns_false(panel: DungeonTreePanel) -> None:
    from dungeon_daddy.ui.panels.dungeon_tree_panel import HEADER_H, ROW_H
    panel.set_dungeon(_make_simple_dungeon())
    row_y = panel._h - HEADER_H - ROW_H / 2

    assert panel.handle_click(300, row_y) is False  # x beyond panel width


def test_handle_click_header_area_returns_false(panel: DungeonTreePanel) -> None:
    panel.set_dungeon(_make_simple_dungeon())
    # click inside header (top 38px)
    assert panel.handle_click(50, panel._h - 10) is False


def test_handle_click_no_dungeon_returns_false(panel: DungeonTreePanel) -> None:
    assert panel.handle_click(50, 300) is False
