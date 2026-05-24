"""Unit tests for ChatPanel.on_mouse_press chip click handling and handle_key_press."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

import arcade

from dungeon_daddy.ui.panels.chat_panel import ChatPanel


@pytest.fixture
def panel():
    return ChatPanel(on_send=MagicMock())


def _with_chip_rects(panel: ChatPanel) -> ChatPanel:
    """Populate chip rects as draw() would — bypasses arcade rendering."""
    panel._chip_rects = [
        (0.0, 4.0, 110.0, 24.0, "Validate level"),
        (118.0, 4.0, 253.0, 24.0, "Add a secret door"),
    ]
    return panel


def test_chip_click_sends_chip_text(panel):
    _with_chip_rects(panel)
    result = panel.on_mouse_press(55.0, 14.0)
    assert result is True
    panel._on_send.assert_called_once_with("Validate level")


def test_chip_click_second_chip(panel):
    _with_chip_rects(panel)
    panel.on_mouse_press(185.0, 14.0)
    panel._on_send.assert_called_once_with("Add a secret door")


def test_chip_miss_returns_false(panel):
    _with_chip_rects(panel)
    result = panel.on_mouse_press(500.0, 14.0)
    assert result is False
    panel._on_send.assert_not_called()


def test_chip_click_ignored_when_busy(panel):
    _with_chip_rects(panel)
    panel._busy = True
    result = panel.on_mouse_press(55.0, 14.0)
    assert result is False
    panel._on_send.assert_not_called()


def test_chip_click_at_edge(panel):
    _with_chip_rects(panel)
    panel.on_mouse_press(0.0, 4.0)
    panel._on_send.assert_called_once_with("Validate level")


def test_no_chip_rects_returns_false(panel):
    result = panel.on_mouse_press(55.0, 14.0)
    assert result is False


# ---------------------------------------------------------------------------
# handle_key_press — F-12 keyboard shortcuts
# ---------------------------------------------------------------------------

def _with_input(panel: ChatPanel, text: str = "Hello") -> MagicMock:
    """Attach a fake input widget so handle_key_press can read/clear text."""
    fake = MagicMock()
    fake.text = text
    panel._input = fake
    return fake


def test_ctrl_enter_sends_message(panel):
    inp = _with_input(panel, "Hello world")
    result = panel.handle_key_press(arcade.key.ENTER, arcade.key.MOD_CTRL)
    assert result is True
    panel._on_send.assert_called_once_with("Hello world")
    assert inp.text == ""


def test_ctrl_enter_whitespace_no_send(panel):
    _with_input(panel, "   ")
    result = panel.handle_key_press(arcade.key.ENTER, arcade.key.MOD_CTRL)
    assert result is True
    panel._on_send.assert_not_called()


def test_ctrl_enter_when_busy_no_send(panel):
    _with_input(panel, "Hello")
    panel._busy = True
    result = panel.handle_key_press(arcade.key.ENTER, arcade.key.MOD_CTRL)
    assert result is True
    panel._on_send.assert_not_called()


def test_plain_enter_not_consumed(panel):
    _with_input(panel, "Hello")
    result = panel.handle_key_press(arcade.key.ENTER, 0)
    assert result is False
    panel._on_send.assert_not_called()


def test_other_key_not_consumed(panel):
    _with_input(panel, "Hello")
    result = panel.handle_key_press(arcade.key.Z, arcade.key.MOD_CTRL)
    assert result is False
    panel._on_send.assert_not_called()


# ---------------------------------------------------------------------------
# CE-5 — context_loaded chip state
# ---------------------------------------------------------------------------


def test_set_context_loaded_true(panel):
    panel.set_context_loaded(True)
    assert panel._context_loaded is True


def test_set_context_loaded_false_clears(panel):
    panel.set_context_loaded(True)
    panel.set_context_loaded(False)
    assert panel._context_loaded is False
