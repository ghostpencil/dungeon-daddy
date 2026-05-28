"""Chat panel — message history display and input area for Design Mode."""
from __future__ import annotations

from collections.abc import Callable

import arcade
import arcade.gui

from dungeon_daddy.data.models import ChatMessage
from dungeon_daddy.ui.theme import (
    BG_0,
    BG_1,
    BG_2,
    BG_3,
    FONT_MONO,
    FONT_SERIF,
    FONT_UI,
    FONT_UI_MED,
    INK_1,
    INK_2,
    INK_3,
    INK_4,
    LINE,
    LINE_HI,
    PAD_MD,
    PAD_SM,
    PAD_XL,
    PAD_XS,
    TEAL,
    TEAL_DIM,
    TEXT_3XL,
    TEXT_BASE,
    TEXT_MD,
    TEXT_SM,
    TEXT_XS,
    VIOLET,
    draw_chip,
    draw_kicker,
)
from dungeon_daddy.ui.widgets.markdown_label import MarkdownLabel

HEADER_H = 38
ROOM_BANNER_H = 80   # play mode only: CURRENT ROOM banner below header
INPUT_AREA_H = 104   # chips (20) + gap (6) + input (62) + padding (8+8)
INPUT_H = 62         # height of the editable input box (~3 lines)
_INPUT_Y_OFF = 8     # distance from panel bottom to input box bottom
_CHIP_CY_OFF = 86    # distance from panel bottom to chip row centre
_LABEL_H = 20  # height reserved at top of each bubble for the role label
_SCROLL_SPEED = 30  # pixels per mouse wheel click
_CHIPS_DESIGN = [
    "Validate level",
    "Add a secret door",
    "Rebalance loot",
    "Generate next level",
]
_CHIPS_PLAY = [
    "Describe room",
    "Search for traps",
    "Roll initiative",
    "Listen at the door",
]


class ChatPanel:
    """
    Design Mode chat panel (centre column).

    Draws backgrounds and chat bubbles with arcade.draw_*.
    Manages UIInputText and UIFlatButton through the shared UIManager.

    Scroll model
    ------------
    _scroll_offset == 0  →  newest message anchored at the bottom of the
                             message area (standard chatbot "at bottom" view).
    _scroll_offset > 0   →  stack shifted down; older messages scroll into view.

    draw() renders messages BEFORE the header/input bars so those solid
    backgrounds act as natural clip masks — no OpenGL scissor needed.
    """

    def __init__(self, on_send: Callable[[str], None], mode: str = "design") -> None:
        self._on_send = on_send
        self._mode = mode  # "design" | "play"
        self._messages: list[ChatMessage] = []
        self._busy = False
        self._typing_frame = 0
        self._typing_elapsed = 0.0
        self._mode_label = "Wizard Mode"
        self._current_room_name: str = ""
        self._current_room_note: str = ""
        self._current_room_id: str = ""
        self._turn: int = 0
        self._input: arcade.gui.UIInputText | None = None
        self._send_btn: arcade.gui.UIFlatButton | None = None
        self._x = self._y = self._w = self._h = 0.0
        self._scroll_offset: float = 0.0
        self._chip_rects: list[tuple[float, float, float, float, str]] = []
        self._context_loaded: bool = False
        self._label_cache: dict[int, MarkdownLabel] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setup(
        self,
        manager: arcade.gui.UIManager,
        x: float, y: float, w: float, h: float,
    ) -> None:
        """Create and register UIManager widgets for this panel."""
        self._x, self._y, self._w, self._h = x, y, w, h
        # input_w leaves room for: left-pad + gap + button + right-pad
        input_w = w - PAD_SM - 4 - 76 - PAD_SM
        input_x = x + PAD_SM
        btn_x = input_x + input_w + 4

        _input_style_normal = arcade.gui.UIInputText.UIStyle(
            bg=(*BG_2, 255),
            border=(*LINE, 255),
            border_width=1,
        )
        _input_style_hover = arcade.gui.UIInputText.UIStyle(
            bg=(*BG_2, 255),
            border=(*LINE_HI, 255),
            border_width=1,
        )
        _input_style_press = arcade.gui.UIInputText.UIStyle(
            bg=(*BG_2, 255),
            border=(*TEAL, 255),
            border_width=1,
        )
        _input_style_disabled = arcade.gui.UIInputText.UIStyle(
            bg=(*BG_1, 255),
            border=(*LINE, 255),
            border_width=1,
        )
        self._input = arcade.gui.UIInputText(
            x=input_x,
            y=y + _INPUT_Y_OFF,
            width=input_w,
            height=INPUT_H,
            font_name=FONT_UI,
            font_size=TEXT_MD,
            text_color=(*INK_1, 255),
            multiline=True,
            border_color=(*LINE, 255),  # type: ignore[arg-type]
            border_width=1,
            style={
                "normal":   _input_style_normal,
                "hover":    _input_style_hover,
                "press":    _input_style_press,
                "disabled": _input_style_disabled,
                "invalid":  _input_style_normal,
            },
        )
        # Pyglet's Caret only handles Ctrl+C/V when it has a window reference.
        # UIInputText doesn't pass one, so we inject it here.
        self._input.caret._window = arcade.get_window()
        manager.add(self._input)

        self._send_btn = arcade.gui.UIFlatButton(
            x=btn_x,
            y=y + _INPUT_Y_OFF,
            width=76,
            height=38,
            text="Ask" if self._mode == "play" else "Send",
            style={
                "normal": arcade.gui.UIFlatButton.UIStyle(
                    font_size=TEXT_SM,
                    font_name=FONT_UI_MED,
                    font_color=(*TEAL, 255),
                    bg=(*BG_2, 255),
                    border=(*TEAL_DIM, 255),
                    border_width=1,
                ),
                "hover": arcade.gui.UIFlatButton.UIStyle(
                    font_size=TEXT_SM,
                    font_name=FONT_UI_MED,
                    font_color=(*TEAL, 255),
                    bg=(*BG_3, 255),
                    border=(*TEAL, 255),
                    border_width=1,
                ),
                "press": arcade.gui.UIFlatButton.UIStyle(
                    font_size=TEXT_SM,
                    font_name=FONT_UI_MED,
                    font_color=(*BG_0, 255),
                    bg=(*TEAL_DIM, 255),
                    border=(*TEAL, 255),
                    border_width=1,
                ),
                "disabled": arcade.gui.UIFlatButton.UIStyle(
                    font_size=TEXT_SM,
                    font_name=FONT_UI_MED,
                    font_color=(*INK_4, 255),
                    bg=(*BG_1, 255),
                    border=(*LINE, 255),
                    border_width=1,
                ),
            },
        )

        @self._send_btn.event
        def on_click(event: arcade.gui.UIOnClickEvent) -> None:
            self._do_send()

        manager.add(self._send_btn)

    def teardown(self, manager: arcade.gui.UIManager) -> None:
        """Remove UIManager widgets on view hide or rebuild."""
        if self._input is not None:
            manager.remove(self._input)
            self._input = None
        if self._send_btn is not None:
            manager.remove(self._send_btn)
            self._send_btn = None
        self._label_cache.clear()

    def resize(self, x: float, y: float, w: float, h: float) -> None:
        """Reposition widgets after a window resize."""
        self._x, self._y, self._w, self._h = x, y, w, h
        self._label_cache.clear()
        input_w = w - PAD_SM - 4 - 76 - PAD_SM
        if self._input is not None:
            self._input.rect = arcade.LRBT(
                x + PAD_SM, x + PAD_SM + input_w,
                y + _INPUT_Y_OFF, y + _INPUT_Y_OFF + INPUT_H,
            )
        if self._send_btn is not None:
            btn_x = x + PAD_SM + input_w + 4
            self._send_btn.rect = arcade.LRBT(btn_x, btn_x + 76, y + _INPUT_Y_OFF, y + _INPUT_Y_OFF + 38)

    # ------------------------------------------------------------------
    # Data / state
    # ------------------------------------------------------------------

    def add_message(self, role: str, content: str) -> None:
        self._messages.append(ChatMessage(role=role, content=content))  # type: ignore[arg-type]
        self._scroll_to_bottom()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._typing_elapsed = 0.0
        if self._send_btn is not None:
            self._send_btn.disabled = busy

    def set_mode_label(self, label: str) -> None:
        self._mode_label = label

    def set_context_loaded(self, loaded: bool) -> None:
        self._context_loaded = loaded

    def set_current_room(self, name: str, note: str = "", room_id: str = "") -> None:
        self._current_room_name = name
        self._current_room_note = note
        self._current_room_id = room_id
        self._turn += 1

    def update(self, delta_time: float) -> None:
        if self._busy:
            self._typing_elapsed += delta_time
            if self._typing_elapsed >= 0.5:
                self._typing_elapsed = 0.0
                self._typing_frame = (self._typing_frame + 1) % 3

    def on_mouse_press(self, x: float, y: float) -> bool:
        if self._busy:
            return False
        for left, bot, right, top, text in self._chip_rects:
            if left <= x <= right and bot <= y <= top:
                self._on_send(text)
                return True
        return False

    def on_mouse_scroll(self, x: float, y: float, scroll_y: float) -> None:
        """Handle mouse wheel scroll over the message area."""
        chat_y_bot = self._y + INPUT_AREA_H
        chat_y_top = self._y + self._h - HEADER_H
        if not (self._x <= x <= self._x + self._w and chat_y_bot <= y <= chat_y_top):
            return
        area_h = chat_y_top - chat_y_bot
        bubble_w = self._w - PAD_XL * 2
        total_h = self._total_stack_height(bubble_w)
        max_scroll = max(0.0, total_h - area_h + PAD_SM)
        self._scroll_offset = max(0.0, min(self._scroll_offset + scroll_y * _SCROLL_SPEED, max_scroll))

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self) -> None:
        x, y, w, h = self._x, self._y, self._w, self._h

        # Panel background
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_1)

        # Vertical borders
        arcade.draw_line(x, y, x, y + h, LINE, 1)
        arcade.draw_line(x + w, y, x + w, y + h, LINE, 1)

        # Chat messages drawn FIRST so header/input backgrounds clip any overflow
        _banner_h = ROOM_BANNER_H if self._mode == "play" else 0
        self._draw_messages(x, y + INPUT_AREA_H, w, h - HEADER_H - _banner_h - INPUT_AREA_H)

        # Header bar — drawn on top to hide any message overflow at the top
        arcade.draw_rect_filled(
            arcade.XYWH(x + w / 2, y + h - HEADER_H / 2, w, HEADER_H), BG_2
        )
        arcade.draw_line(x, y + h - HEADER_H, x + w, y + h - HEADER_H, LINE, 1)
        _kicker = "DUNGEON CHAT" if self._mode == "play" else "DESIGN CHAT"
        draw_kicker(_kicker, x + PAD_MD, y + h - HEADER_H / 2)
        if self._mode == "play":
            _cy = y + h - HEADER_H / 2
            draw_chip(f"Turn {self._turn}", x + 148, _cy, "teal")
            if self._current_room_id:
                draw_chip(self._current_room_id, x + 240, _cy, "violet")
        else:
            _cy = y + h - HEADER_H / 2
            arcade.draw_text(
                f"·  {self._mode_label}",
                x + 148, _cy,
                INK_4, font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="center",
            )
            if self._context_loaded:
                draw_chip("✦ context", x + w - 90, _cy, "teal")

        # Current Room banner (play mode only)
        if self._mode == "play":
            banner_y = y + h - HEADER_H - ROOM_BANNER_H
            arcade.draw_rect_filled(
                arcade.XYWH(x + w / 2, banner_y + ROOM_BANNER_H / 2, w, ROOM_BANNER_H), BG_1
            )
            # violet left-edge accent
            arcade.draw_line(x, banner_y, x, banner_y + ROOM_BANNER_H, VIOLET, 3)
            arcade.draw_line(x, banner_y, x + w, banner_y, LINE, 1)
            draw_kicker("CURRENT ROOM", x + PAD_MD + 6, banner_y + ROOM_BANNER_H - 12)
            room_label = self._current_room_name or "No room selected"
            arcade.draw_text(
                room_label,
                x + PAD_MD + 6, banner_y + ROOM_BANNER_H - 26,
                INK_1, font_size=TEXT_3XL, font_name=FONT_SERIF, anchor_y="top",
            )
            if self._current_room_note:
                arcade.draw_text(
                    self._current_room_note,
                    x + PAD_MD + 6, banner_y + 12,
                    INK_3, font_size=TEXT_BASE, font_name=FONT_UI, anchor_y="bottom",
                )

        # Input area — drawn on top to hide any message overflow at the bottom
        arcade.draw_rect_filled(
            arcade.XYWH(x + w / 2, y + INPUT_AREA_H / 2, w, INPUT_AREA_H), BG_1
        )
        arcade.draw_line(x, y + INPUT_AREA_H, x + w, y + INPUT_AREA_H, LINE, 1)

        # Quick chips (row above input field) — width sized to text
        _CHIP_CHAR_W = 7  # approx px per char for FONT_MONO TEXT_SM
        _CHIP_GAP = 8
        self._chip_rects = []
        chip_x = x + PAD_SM
        _chips = _CHIPS_PLAY if self._mode == "play" else _CHIPS_DESIGN
        for chip in _chips:
            chip_w = len(chip) * _CHIP_CHAR_W + PAD_SM * 2
            cy = y + _CHIP_CY_OFF
            draw_chip(chip, chip_x + chip_w / 2, cy, "default", width=chip_w)
            self._chip_rects.append((chip_x, cy - 10, chip_x + chip_w, cy + 10, chip))
            chip_x += chip_w + _CHIP_GAP

    def _draw_messages(self, x: float, y_bot: float, w: float, area_h: float) -> None:
        pad = PAD_SM
        bubble_w = w - PAD_XL * 2
        bx = x + PAD_XL
        y_top = y_bot + area_h

        heights = self._compute_heights(bubble_w)
        n = len(self._messages)

        # Clamp scroll to valid range
        total_h = self._total_stack_height(bubble_w)
        max_scroll = max(0.0, total_h - area_h + pad)
        self._scroll_offset = max(0.0, min(self._scroll_offset, max_scroll))
        off = self._scroll_offset

        # Scissor-clip to the message area so bubbles never bleed into the
        # header bar above or the input area below.
        ctx = arcade.get_window().ctx
        old_scissor = ctx.scissor
        ctx.scissor = (int(x), int(y_bot), int(w), int(area_h))
        try:
            self._draw_messages_inner(
                bx, y_bot, y_top, bubble_w, pad, heights, n, off
            )
        finally:
            ctx.scissor = old_scissor

    def _draw_messages_inner(
        self,
        bx: float, y_bot: float, y_top: float,
        bubble_w: float, pad: float,
        heights: list[int], n: int, off: float,
    ) -> None:
        # When messages fit in the area, top-anchor the stack so the first
        # message appears near the top rather than leaving a dead zone above.
        # When content overflows, fall back to bottom-anchored (scroll up for older).
        area_h = y_top - y_bot
        total_h = sum(heights) + n * pad
        if self._busy:
            total_h += 36 + pad
        if total_h < area_h:
            pos = y_bot + area_h - total_h
        else:
            pos = y_bot + pad

        # Typing indicator sits at the bottom (newest activity)
        if self._busy:
            b_h = 36
            draw_y = pos - off
            if draw_y < y_top and draw_y + b_h > y_bot:
                dots = ["·  ·  ·", "■  ·  ·", "■  ■  ·"][self._typing_frame]
                arcade.draw_rect_filled(
                    arcade.XYWH(bx + bubble_w / 2, draw_y + b_h / 2, bubble_w, b_h), BG_2
                )
                arcade.draw_rect_outline(
                    arcade.XYWH(bx + bubble_w / 2, draw_y + b_h / 2, bubble_w, b_h), VIOLET, 1
                )
                arcade.draw_text(
                    f"◆ {dots}", bx + PAD_SM, draw_y + b_h / 2,
                    VIOLET, font_size=TEXT_BASE, font_name=FONT_MONO, anchor_y="center",
                )
            pos += b_h + pad

        # Messages newest-first, stacked upward from the bottom
        for i, msg in enumerate(reversed(self._messages)):
            b_h = heights[n - 1 - i]
            draw_y = pos - off

            if draw_y >= y_top:
                break  # above viewport; older messages are even higher

            if draw_y + b_h > y_bot:  # at least partially in the viewport
                is_gm = msg.role == "gm"
                fill = (20, 50, 55) if is_gm else BG_2
                stroke = TEAL if is_gm else VIOLET

                arcade.draw_rect_filled(
                    arcade.XYWH(bx + bubble_w / 2, draw_y + b_h / 2, bubble_w, b_h), fill
                )
                arcade.draw_rect_outline(
                    arcade.XYWH(bx + bubble_w / 2, draw_y + b_h / 2, bubble_w, b_h), stroke, 1
                )
                label_color = TEAL if is_gm else VIOLET
                arcade.draw_text(
                    "GM" if is_gm else "◆ Dungeon",
                    bx + PAD_SM, draw_y + b_h - PAD_XS,
                    label_color, font_size=TEXT_XS, font_name=FONT_MONO, anchor_y="top",
                )
                label = self._get_or_build_label(n - 1 - i, msg, bubble_w)
                label.update_position(bx + PAD_SM, draw_y + b_h - _LABEL_H)
                label.draw()

            pos += b_h + pad

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_build_label(self, index: int, msg: ChatMessage, bubble_w: float) -> MarkdownLabel:
        if index not in self._label_cache:
            text_w = int(bubble_w - PAD_SM * 2)
            color = INK_2 if msg.role == "gm" else INK_1
            self._label_cache[index] = MarkdownLabel(
                msg.content,
                x=0, y=0,
                width=text_w,
                color=color,
                font_name=FONT_UI,
                font_size=TEXT_BASE,
            )
        return self._label_cache[index]

    def _bubble_height(self, index: int, msg: ChatMessage, bubble_w: float) -> int:
        label = self._get_or_build_label(index, msg, bubble_w)
        return max(40, label.content_height + int(PAD_SM) * 2 + _LABEL_H)

    def _compute_heights(self, bubble_w: float) -> list[int]:
        return [self._bubble_height(i, msg, bubble_w) for i, msg in enumerate(self._messages)]

    def _total_stack_height(self, bubble_w: float) -> float:
        pad = PAD_SM
        total = sum(h + pad for h in self._compute_heights(bubble_w))
        if self._busy:
            total += 36 + pad
        return total

    def _scroll_to_bottom(self) -> None:
        self._scroll_offset = 0.0

    def handle_key_press(self, key: int, modifiers: int) -> bool:
        """Handle a key press. Returns True if the event was consumed."""
        if key == arcade.key.ENTER and (modifiers & arcade.key.MOD_CTRL):
            self._do_send()
            return True
        return False

    def _do_send(self) -> None:
        if self._busy or self._input is None:
            return
        text = self._input.text.strip()
        if text:
            self._on_send(text)
            self._input.text = ""
