"""Tests for LoopsPanel behavioral logic — no display required."""
from __future__ import annotations

import importlib.resources
import json

import pytest

from dungeon_daddy.data.models import Dungeon, Level, LoopPattern
from dungeon_daddy.ui.panels.loops_panel import LoopsPanel

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tomb() -> Dungeon:
    pkg = importlib.resources.files("dungeon_daddy.data")
    raw = (pkg / "samples" / "tomb_of_the_forgotten_king.json").read_text(encoding="utf-8")
    return Dungeon.model_validate(json.loads(raw))


@pytest.fixture(scope="module")
def patterns(tomb: Dungeon) -> list[LoopPattern]:
    return list(tomb.loop_patterns.values())


@pytest.fixture()
def level1(tomb: Dungeon) -> Level:
    """Fresh deep copy of Level 1 so each test starts clean."""
    lvl = tomb.levels[0].model_copy(deep=True)
    lvl.loops = []
    return lvl


@pytest.fixture()
def panel() -> LoopsPanel:
    return LoopsPanel()


# ---------------------------------------------------------------------------
# Slice 2 — apply_pattern
# ---------------------------------------------------------------------------

def test_apply_pattern_creates_main_loop_on_level(
    panel: LoopsPanel, level1: Level, patterns: list[LoopPattern]
) -> None:
    """apply_pattern adds exactly one Loop with type='main' to level.loops."""
    panel.set_level(level1)
    panel.apply_pattern("lock_key", patterns)
    assert len(level1.loops) == 1
    assert level1.loops[0].pattern == "lock_key"
    assert level1.loops[0].type == "main"


def test_apply_pattern_auto_assigns_paths(
    panel: LoopsPanel, level1: Level, patterns: list[LoopPattern]
) -> None:
    """apply_pattern populates path_a and path_b via auto_assign_loop_rooms."""
    panel.set_level(level1)
    panel.apply_pattern("gambit", patterns)
    loop = level1.loops[0]
    assert loop.path_a != []
    assert loop.path_b != []
    assert loop.entry == loop.path_a[0]
    assert loop.goal == loop.path_a[-1]


# ---------------------------------------------------------------------------
# Slice 2 — add_sub_loop
# ---------------------------------------------------------------------------

def test_add_sub_loop_appends_sub_type_loop(
    panel: LoopsPanel, level1: Level, patterns: list[LoopPattern]
) -> None:
    """add_sub_loop appends a Loop with type='sub' without removing the main loop."""
    panel.set_level(level1)
    panel.apply_pattern("lock_key", patterns)
    panel.add_sub_loop("gambit", patterns)
    assert len(level1.loops) == 2
    assert level1.loops[1].type == "sub"
    assert level1.loops[1].pattern == "gambit"


# ---------------------------------------------------------------------------
# Slice 2 — remove_sub_loop
# ---------------------------------------------------------------------------

def test_remove_sub_loop_removes_loop_by_id(
    panel: LoopsPanel, level1: Level, patterns: list[LoopPattern]
) -> None:
    """remove_sub_loop deletes the loop with the matching id from level.loops."""
    panel.set_level(level1)
    panel.apply_pattern("lock_key", patterns)
    panel.add_sub_loop("gambit", patterns)
    sub_id = level1.loops[1].id
    panel.remove_sub_loop(sub_id)
    assert len(level1.loops) == 1
    assert all(lp.id != sub_id for lp in level1.loops)


# ---------------------------------------------------------------------------
# Slice 2 — on_activate_loop callback
# ---------------------------------------------------------------------------

def test_activate_loop_fires_callback(
    level1: Level, patterns: list[LoopPattern]
) -> None:
    """activate_loop calls on_activate_loop with the correct loop_id."""
    fired: list[str] = []
    panel = LoopsPanel(on_activate_loop=fired.append)
    panel.set_level(level1)
    panel.apply_pattern("lock_key", patterns)
    loop_id = level1.loops[0].id
    panel.activate_loop(loop_id)
    assert fired == [loop_id]


# ---------------------------------------------------------------------------
# Slice 3 — on_mouse_press hit-testing
# ---------------------------------------------------------------------------

def test_on_mouse_press_click_calls_apply_pattern(
    panel: LoopsPanel, level1: Level, patterns: list[LoopPattern],
) -> None:
    """Click inside a pattern rect calls apply_pattern and returns True."""
    panel.set_level(level1)
    panel.set_patterns(patterns)
    panel._pattern_rects = {"lock_key": (10, 90, 200, 110)}
    consumed = panel.on_mouse_press(100, 100, 0)
    assert consumed is True
    assert len(level1.loops) == 1
    assert level1.loops[0].pattern == "lock_key"


def test_on_mouse_press_shift_click_calls_add_sub_loop(
    panel: LoopsPanel, level1: Level, patterns: list[LoopPattern],
) -> None:
    """Shift-click inside a pattern rect calls add_sub_loop and returns True."""
    panel.set_level(level1)
    panel.set_patterns(patterns)
    panel.apply_pattern("lock_key", patterns)  # ensure a main loop exists
    panel._pattern_rects = {"gambit": (10, 90, 200, 110)}
    MOD_SHIFT = 1
    consumed = panel.on_mouse_press(100, 100, MOD_SHIFT)
    assert consumed is True
    assert len(level1.loops) == 2
    assert level1.loops[1].pattern == "gambit"
    assert level1.loops[1].type == "sub"


def test_on_mouse_press_miss_returns_false(
    panel: LoopsPanel,
) -> None:
    """Click outside all pattern rects returns False."""
    panel._pattern_rects = {"lock_key": (10, 90, 200, 110)}
    consumed = panel.on_mouse_press(500, 500, 0)
    assert consumed is False


# ---------------------------------------------------------------------------
# Slice 4 — × remove button hit-testing
# ---------------------------------------------------------------------------

def test_on_mouse_press_remove_rect_removes_sub_loop(
    panel: LoopsPanel, level1: Level, patterns: list[LoopPattern],
) -> None:
    """Click inside a _remove_rects entry removes that sub-loop and returns True."""
    panel.set_level(level1)
    panel.set_patterns(patterns)
    panel.apply_pattern("lock_key", patterns)
    panel.add_sub_loop("gambit", patterns)
    sub_id = level1.loops[1].id
    panel._remove_rects = {sub_id: (180, 90, 200, 110)}
    consumed = panel.on_mouse_press(190, 100, 0)
    assert consumed is True
    assert len(level1.loops) == 1
    assert all(lp.id != sub_id for lp in level1.loops)


# ---------------------------------------------------------------------------
# Slice 6 — + button (add sub-loop without shift)
# ---------------------------------------------------------------------------

def test_on_mouse_press_add_rect_calls_add_sub_loop(
    panel: LoopsPanel, level1: Level, patterns: list[LoopPattern],
) -> None:
    """Click inside _add_rects[pat_key] calls add_sub_loop and returns True."""
    panel.set_level(level1)
    panel.set_patterns(patterns)
    panel.apply_pattern("lock_key", patterns)
    panel._add_rects = {"gambit": (180, 90, 200, 110)}
    consumed = panel.on_mouse_press(190, 100, 0)
    assert consumed is True
    assert len(level1.loops) == 2
    assert level1.loops[1].pattern == "gambit"
    assert level1.loops[1].type == "sub"


def test_on_mouse_press_add_rect_does_not_call_apply_pattern(
    panel: LoopsPanel, level1: Level, patterns: list[LoopPattern],
) -> None:
    """Click on + button does not replace the main loop."""
    panel.set_level(level1)
    panel.set_patterns(patterns)
    panel.apply_pattern("lock_key", patterns)
    panel._pattern_rects = {"gambit": (10, 90, 200, 110)}
    panel._add_rects = {"gambit": (180, 90, 200, 110)}
    consumed = panel.on_mouse_press(190, 100, 0)
    assert consumed is True
    assert level1.loops[0].pattern == "lock_key"  # main loop unchanged


# ---------------------------------------------------------------------------
# Slice 5 — level picker
# ---------------------------------------------------------------------------

def test_on_mouse_press_level_rect_sets_level(
    tomb: Dungeon,
) -> None:
    """Click inside _level_rects[1] switches the active level and returns True."""
    panel = LoopsPanel()
    levels = tomb.levels
    panel.set_levels(levels)
    panel._level_rects = {0: (10, 90, 40, 110), 1: (50, 90, 80, 110)}
    consumed = panel.on_mouse_press(60, 100, 0)
    assert consumed is True
    assert panel._level is levels[1]


# ---------------------------------------------------------------------------
# Slice 7 — loop row click activates loop
# ---------------------------------------------------------------------------

def test_on_mouse_press_loop_rect_calls_activate_loop(
    level1: Level, patterns: list[LoopPattern],
) -> None:
    """Click inside a loop row rect fires on_activate_loop with that loop's id."""
    fired: list[str] = []
    panel = LoopsPanel(on_activate_loop=fired.append)
    panel.set_level(level1)
    panel.apply_pattern("lock_key", patterns)
    loop_id = level1.loops[0].id
    panel._loop_rects = {loop_id: (10, 90, 200, 110)}
    consumed = panel.on_mouse_press(100, 100, 0)
    assert consumed is True
    assert fired == [loop_id]
