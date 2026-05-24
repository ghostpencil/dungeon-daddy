"""Chat bubble widget — in-map DM narration overlay."""
from __future__ import annotations

import arcade

from dungeon_daddy.ui.theme import (
    BG_2,
    FONT_UI,
    INK_1,
    PAD_SM,
    RADIUS_MD,
    TEXT_BASE,
    draw_rounded_rect,
)

_LINE_H = 18
_CHARS_PER_PX = 7


class ChatBubble:
    """
    Draw a styled speech bubble at (x, y) anchored at its bottom-left corner.

    color controls the border accent; background is BG_2.
    max_width caps the bubble width including padding.
    """

    def draw(
        self,
        x: float,
        y: float,
        text: str,
        color: tuple,
        max_width: float,
    ) -> None:
        pad = PAD_SM
        text_w = int(max_width - pad * 2)
        chars_per_line = max(1, text_w // _CHARS_PER_PX)

        line_count = 0
        for para in text.split("\n"):
            if para:
                line_count += max(1, (len(para) + chars_per_line - 1) // chars_per_line)
            else:
                line_count += 1
        line_count = max(1, line_count)

        bubble_h = line_count * _LINE_H + pad * 2
        bubble_w = max_width
        cx = x + bubble_w / 2
        cy = y + bubble_h / 2

        draw_rounded_rect(cx, cy, bubble_w, bubble_h, RADIUS_MD, BG_2, color, 1)

        arcade.draw_text(
            text,
            x + pad,
            y + bubble_h - pad,
            INK_1,
            font_size=TEXT_BASE,
            font_name=FONT_UI,
            anchor_y="top",
            width=text_w,
            multiline=True,
        )
