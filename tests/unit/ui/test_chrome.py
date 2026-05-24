"""Tests for MenuBar.handle_click() — hit-test, dropdown dispatch, handler invocation."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from dungeon_daddy.ui.chrome import MenuAction, MenuBar

# Window stub: 1280 × 800
_WIN = SimpleNamespace(width=1280, height=800)

# CHROME_MENUBAR_HEIGHT=26 → bar strip: y >= 774
# PAD_MD=12, _CHAR_W=7
# "File" (4 chars): slot_w = 4*7 + 12*2 = 52  → x ∈ [12, 64]
# "Edit" (4 chars): slot_w = 52               → x ∈ [64, 116]
_BAR_Y = 790      # inside bar strip
_BELOW_BAR_Y = 500  # outside bar strip

_FILE_X = 20   # inside "File" slot [12, 64]
_EDIT_X = 80   # inside "Edit" slot [64, 116]
_EMPTY_X = 5   # left of all labels (< PAD_MD=12)

# Dropdown "File" origin = (12, 774); PAD_SM=8, _ITEM_H=22, _DROP_W=160
# Item 0: y_top=766, y_bot=744  → (80, 755)
# Item 1: y_top=744, y_bot=722  → (80, 730)
_ITEM0_X, _ITEM0_Y = 80, 755
_ITEM1_X, _ITEM1_Y = 80, 730
_OUTSIDE_X, _OUTSIDE_Y = 500, 500  # x > 172, outside dropdown


@pytest.fixture
def handler1():
    return MagicMock()


@pytest.fixture
def handler2():
    return MagicMock()


@pytest.fixture
def bar(handler1, handler2):
    menu = {
        "File": [
            MenuAction("New", handler1),
            MenuAction("Open", handler2, enabled=False),
        ],
        "Edit": [],
    }
    return MenuBar(menu)


# ---------------------------------------------------------------------------
# Menu bar strip hit tests
# ---------------------------------------------------------------------------

class TestMenuBarStripClick:
    def test_click_on_label_opens_menu_and_returns_true(self, bar):
        result = bar.handle_click(_FILE_X, _BAR_Y, _WIN)
        assert result is True
        assert bar._open == "File"

    def test_click_on_open_label_closes_menu_and_returns_true(self, bar):
        bar._open = "File"
        result = bar.handle_click(_FILE_X, _BAR_Y, _WIN)
        assert result is True
        assert bar._open is None

    def test_click_on_different_label_switches_menu_and_returns_true(self, bar):
        bar._open = "File"
        result = bar.handle_click(_EDIT_X, _BAR_Y, _WIN)
        assert result is True
        assert bar._open == "Edit"

    def test_click_on_empty_area_sets_open_none_and_returns_true(self, bar):
        result = bar.handle_click(_EMPTY_X, _BAR_Y, _WIN)
        assert result is True
        assert bar._open is None

    def test_click_below_bar_with_no_open_menu_returns_false(self, bar):
        result = bar.handle_click(100, _BELOW_BAR_Y, _WIN)
        assert result is False


# ---------------------------------------------------------------------------
# Dropdown dispatch tests
# ---------------------------------------------------------------------------

class TestDropdownDispatch:
    def test_click_enabled_item_calls_handler_and_closes_menu(self, bar, handler1):
        bar._open = "File"
        result = bar.handle_click(_ITEM0_X, _ITEM0_Y, _WIN)
        assert result is True
        assert bar._open is None
        handler1.assert_called_once()

    def test_click_disabled_item_does_not_call_handler_and_closes_menu(self, bar, handler2):
        bar._open = "File"
        result = bar.handle_click(_ITEM1_X, _ITEM1_Y, _WIN)
        assert result is True
        assert bar._open is None
        handler2.assert_not_called()

    def test_click_outside_dropdown_closes_menu_and_returns_true(self, bar, handler1):
        bar._open = "File"
        result = bar.handle_click(_OUTSIDE_X, _OUTSIDE_Y, _WIN)
        assert result is True
        assert bar._open is None
        handler1.assert_not_called()
