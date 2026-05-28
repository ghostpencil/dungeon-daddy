"""Unit tests for ChatPanel.on_mouse_press chip click handling and handle_key_press."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import arcade
import pytest

from dungeon_daddy.data.models import ChatMessage
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


# ---------------------------------------------------------------------------
# MC-1 Step 4 — label cache
# ---------------------------------------------------------------------------

def _mock_pyglet_html_label():
    mock_inner = MagicMock()
    mock_inner.content_height = 50
    return mock_inner


def test_label_cache_starts_empty(panel):
    assert panel._label_cache == {}


def test_get_or_build_label_creates_on_miss(panel):
    msg = ChatMessage(role="dm", content="hello")
    with patch("pyglet.text.HTMLLabel", return_value=_mock_pyglet_html_label()):
        label = panel._get_or_build_label(0, msg, 300.0)
    assert label is not None
    assert 0 in panel._label_cache


def test_get_or_build_label_returns_same_on_hit(panel):
    msg = ChatMessage(role="dm", content="hello")
    mock_inner = _mock_pyglet_html_label()
    with patch("pyglet.text.HTMLLabel", return_value=mock_inner):
        label1 = panel._get_or_build_label(0, msg, 300.0)
        label2 = panel._get_or_build_label(0, msg, 300.0)
    assert label1 is label2


def test_resize_clears_label_cache(panel):
    msg = ChatMessage(role="dm", content="hello")
    with patch("pyglet.text.HTMLLabel", return_value=_mock_pyglet_html_label()):
        panel._get_or_build_label(0, msg, 300.0)
    assert 0 in panel._label_cache
    panel.resize(0.0, 0.0, 400.0, 600.0)
    assert panel._label_cache == {}


def test_teardown_clears_label_cache(panel):
    msg = ChatMessage(role="dm", content="hello")
    with patch("pyglet.text.HTMLLabel", return_value=_mock_pyglet_html_label()):
        panel._get_or_build_label(0, msg, 300.0)
    assert 0 in panel._label_cache
    panel.teardown(MagicMock())
    assert panel._label_cache == {}


# ---------------------------------------------------------------------------
# MC-1 Step 5 — _bubble_height uses label content_height
# ---------------------------------------------------------------------------


def test_bubble_height_uses_label_content_height(panel):
    msg = ChatMessage(role="dm", content="hello")
    mock_inner = _mock_pyglet_html_label()
    mock_inner.content_height = 80
    with patch("pyglet.text.HTMLLabel", return_value=mock_inner):
        h = panel._bubble_height(0, msg, 300.0)
    assert h == 116  # max(40, 80 + 8*2 + 20)


def test_bubble_height_clamps_to_minimum_40(panel):
    msg = ChatMessage(role="dm", content="")
    mock_inner = _mock_pyglet_html_label()
    mock_inner.content_height = 0
    with patch("pyglet.text.HTMLLabel", return_value=mock_inner):
        h = panel._bubble_height(0, msg, 300.0)
    assert h == 40


def test_compute_heights_uses_label_content_height(panel):
    panel._messages = [
        ChatMessage(role="dm", content="hello"),
        ChatMessage(role="gm", content="world"),
    ]
    mock_inner = _mock_pyglet_html_label()
    mock_inner.content_height = 60
    with patch("pyglet.text.HTMLLabel", return_value=mock_inner):
        heights = panel._compute_heights(300.0)
    assert len(heights) == 2
    assert all(h == 96 for h in heights)  # max(40, 60 + 16 + 20)


# ---------------------------------------------------------------------------
# MC-1 Step 6 — _draw_messages_inner uses label.draw()
# ---------------------------------------------------------------------------


def test_draw_messages_inner_calls_label_draw(panel):
    msg = ChatMessage(role="dm", content="hello")
    panel._messages = [msg]
    mock_label = MagicMock()
    panel._label_cache[0] = mock_label
    with patch("dungeon_daddy.ui.panels.chat_panel.arcade"):
        panel._draw_messages_inner(
            bx=10.0, y_bot=0.0, y_top=600.0,
            bubble_w=300.0, pad=8.0,
            heights=[80], n=1, off=0.0,
        )
    mock_label.update_position.assert_called_once()
    mock_label.draw.assert_called_once()
