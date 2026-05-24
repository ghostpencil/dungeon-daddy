"""Tests for ChatBubble.draw() — text wrapping, height estimation, draw calls."""
from __future__ import annotations

from unittest.mock import MagicMock

import arcade
import pytest

import dungeon_daddy.ui.widgets.chat_bubble as _mod
from dungeon_daddy.ui.widgets.chat_bubble import ChatBubble, _LINE_H
from dungeon_daddy.ui.theme import BG_2, FONT_UI, INK_1, PAD_SM, RADIUS_MD, TEXT_BASE

_COLOR = (100, 200, 255, 255)
_MAX_W = 200.0
# text_w = 200 - 8*2 = 184; chars_per_line = 184 // 7 = 26


@pytest.fixture
def bubble():
    return ChatBubble()


@pytest.fixture
def draw_mocks(monkeypatch):
    """Replace arcade draw calls with mocks; return (rect_mock, text_mock)."""
    rect_mock = MagicMock()
    text_mock = MagicMock()
    monkeypatch.setattr(_mod, "draw_rounded_rect", rect_mock)
    monkeypatch.setattr(arcade, "draw_text", text_mock)
    return rect_mock, text_mock


def _bubble_h(line_count: int) -> int:
    return line_count * _LINE_H + PAD_SM * 2


def _drawn_h(rect_mock: MagicMock) -> int:
    _, _, _, h, *_ = rect_mock.call_args.args
    return h


# ---------------------------------------------------------------------------
# Line count / height estimation
# ---------------------------------------------------------------------------

class TestLineCount:
    def test_short_text_is_single_line(self, bubble, draw_mocks):
        rect_mock, _ = draw_mocks
        bubble.draw(0.0, 0.0, "Hello", _COLOR, _MAX_W)
        assert _drawn_h(rect_mock) == _bubble_h(1)

    def test_long_text_wraps_to_multiple_lines(self, bubble, draw_mocks):
        # 53 chars; chars_per_line=26 → ceil(53/26) = 3
        rect_mock, _ = draw_mocks
        bubble.draw(0.0, 0.0, "A" * 53, _COLOR, _MAX_W)
        assert _drawn_h(rect_mock) == _bubble_h(3)

    def test_explicit_newline_adds_paragraph_line(self, bubble, draw_mocks):
        rect_mock, _ = draw_mocks
        bubble.draw(0.0, 0.0, "Hello\nWorld", _COLOR, _MAX_W)
        assert _drawn_h(rect_mock) == _bubble_h(2)

    def test_blank_line_counts_as_one_line(self, bubble, draw_mocks):
        # "Hello\n\nWorld" → ["Hello", "", "World"] → 1 + 1 + 1 = 3
        rect_mock, _ = draw_mocks
        bubble.draw(0.0, 0.0, "Hello\n\nWorld", _COLOR, _MAX_W)
        assert _drawn_h(rect_mock) == _bubble_h(3)

    def test_empty_text_has_minimum_height(self, bubble, draw_mocks):
        rect_mock, _ = draw_mocks
        bubble.draw(0.0, 0.0, "", _COLOR, _MAX_W)
        assert _drawn_h(rect_mock) == _bubble_h(1)


# ---------------------------------------------------------------------------
# Draw call geometry
# ---------------------------------------------------------------------------

class TestDrawCalls:
    def test_rounded_rect_centred_at_bubble_midpoint(self, bubble, draw_mocks):
        rect_mock, _ = draw_mocks
        x, y = 10.0, 5.0
        bubble.draw(x, y, "Hello", _COLOR, _MAX_W)
        h = _bubble_h(1)
        cx = x + _MAX_W / 2
        cy = y + h / 2
        rect_mock.assert_called_once_with(cx, cy, _MAX_W, h, RADIUS_MD, BG_2, _COLOR, 1)

    def test_draw_text_anchored_at_top_left_with_padding(self, bubble, draw_mocks):
        _, text_mock = draw_mocks
        x, y = 10.0, 5.0
        bubble.draw(x, y, "Hello", _COLOR, _MAX_W)
        h = _bubble_h(1)
        text_w = int(_MAX_W - PAD_SM * 2)
        text_mock.assert_called_once_with(
            "Hello",
            x + PAD_SM,
            y + h - PAD_SM,
            INK_1,
            font_size=TEXT_BASE,
            font_name=FONT_UI,
            anchor_y="top",
            width=text_w,
            multiline=True,
        )
