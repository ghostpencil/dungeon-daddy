"""Level stepper widget — ▲/▼ buttons to navigate between dungeon levels."""
from __future__ import annotations

from collections.abc import Callable

import arcade
import arcade.gui

from dungeon_daddy.ui.theme import (
    BG_2,
    BG_3,
    FONT_MONO,
    FONT_SERIF,
    FONT_UI_MED,
    INK_1,
    INK_2,
    INK_3,
    INK_4,
    LINE,
    LINE_HI,
    PAD_SM,
    TEAL,
    TEAL_DIM,
    TEXT_BASE,
    TEXT_SM,
)

_BTN_H = 28
_BTN_W = 44


class LevelStepper:
    """
    Vertical widget with ▲/▼ buttons and a level label between them.

    Calls on_level_change(-1) for ▲ and on_level_change(+1) for ▼.
    Bounds checking is the caller's responsibility.
    """

    def __init__(self, on_level_change: Callable[[int], None]) -> None:
        self._on_level_change = on_level_change
        self._up_btn: arcade.gui.UIFlatButton | None = None
        self._down_btn: arcade.gui.UIFlatButton | None = None
        self._x = self._y = self._w = self._h = 0.0
        self._label = "Level 1"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setup(
        self,
        manager: arcade.gui.UIManager,
        x: float, y: float, w: float, h: float,
    ) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h
        cx = x + w / 2
        btn_x = cx - _BTN_W / 2

        style_normal = arcade.gui.UIFlatButton.UIStyle(
            font_size=TEXT_SM,
            font_name=FONT_UI_MED,
            font_color=(*INK_2, 255),
            bg=(*BG_2, 255),
            border=(*LINE, 255),
            border_width=1,
        )
        style_hover = arcade.gui.UIFlatButton.UIStyle(
            font_size=TEXT_SM,
            font_name=FONT_UI_MED,
            font_color=(*INK_1, 255),
            bg=(*BG_3, 255),
            border=(*LINE_HI, 255),
            border_width=1,
        )
        style_press = arcade.gui.UIFlatButton.UIStyle(
            font_size=TEXT_SM,
            font_name=FONT_UI_MED,
            font_color=(*TEAL, 255),
            bg=(*TEAL_DIM, 255),
            border=(*TEAL, 255),
            border_width=1,
        )
        style_disabled = arcade.gui.UIFlatButton.UIStyle(
            font_size=TEXT_SM,
            font_name=FONT_UI_MED,
            font_color=(*INK_4, 255),
            bg=(*BG_2, 255),
            border=(*LINE, 255),
            border_width=1,
        )
        btn_style = {
            "normal": style_normal,
            "hover": style_hover,
            "press": style_press,
            "disabled": style_disabled,
        }

        up_y = y + h - _BTN_H - PAD_SM
        self._up_btn = arcade.gui.UIFlatButton(
            x=btn_x, y=up_y,
            width=_BTN_W, height=_BTN_H,
            text="▲",
            style=btn_style,
        )

        @self._up_btn.event
        def on_click(event: arcade.gui.UIOnClickEvent) -> None:
            self._on_level_change(-1)

        manager.add(self._up_btn)

        _COMPASS_H = 48   # space reserved at bottom for compass rose
        down_y = y + _COMPASS_H
        self._down_btn = arcade.gui.UIFlatButton(
            x=btn_x, y=down_y,
            width=_BTN_W, height=_BTN_H,
            text="▼",
            style=btn_style,
        )

        @self._down_btn.event  # type: ignore[no-redef]
        def on_click(event: arcade.gui.UIOnClickEvent) -> None:  # noqa: F811
            self._on_level_change(+1)

        manager.add(self._down_btn)

    def teardown(self, manager: arcade.gui.UIManager) -> None:
        for btn in (self._up_btn, self._down_btn):
            if btn is not None:
                manager.remove(btn)
        self._up_btn = None
        self._down_btn = None

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def set_label(self, label: str) -> None:
        self._label = label

    def set_up_enabled(self, enabled: bool) -> None:
        if self._up_btn:
            self._up_btn.disabled = not enabled

    def set_down_enabled(self, enabled: bool) -> None:
        if self._down_btn:
            self._down_btn.disabled = not enabled

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self) -> None:
        cx = self._x + self._w / 2
        label_y = self._y + self._h / 2
        arcade.draw_text(
            self._label,
            cx, label_y,
            INK_3,
            font_size=TEXT_BASE,
            font_name=FONT_MONO,
            anchor_x="center",
            anchor_y="center",
        )
        # Compass rose — bottom of stepper rail
        rose_cy = self._y + 22
        arcade.draw_circle_outline(cx, rose_cy, 18, LINE, 1)
        arcade.draw_text(
            "N", cx, rose_cy,
            INK_2,
            font_size=TEXT_SM,
            font_name=FONT_SERIF,
            anchor_x="center",
            anchor_y="center",
        )
