"""Dungeon Tree Panel — collapsible level / room tree for Design Mode."""
from __future__ import annotations

import arcade

from dungeon_daddy.data.models import Dungeon, Loop, ValidationResult
from dungeon_daddy.ui.theme import (
    AMBER,
    BG_1,
    BG_2,
    BG_HI,
    FONT_MONO,
    FONT_UI,
    INDIGO,
    INK_1,
    INK_3,
    INK_4,
    LINE,
    PAD_MD,
    PAD_SM,
    TEAL,
    TEXT_BASE,
    TEXT_SM,
    VIOLET,
    draw_kicker,
)

HEADER_H = 38
ROW_H = 26
INDENT = 22


class DungeonTreePanel:
    """
    Left panel showing the dungeon structure as a collapsible tree.

    Pure arcade.draw_* — no UIManager widgets.
    """

    def __init__(self) -> None:
        self._dungeon: Dungeon | None = None
        self._expanded: set[int] = set()
        self._selected_room_id: str | None = None
        self._x = self._y = self._w = self._h = 0.0
        self._validation: ValidationResult | None = None
        self._path_a_rooms: set[str] = set()
        self._path_b_rooms: set[str] = set()

    def set_active_loop(self, loop: Loop | None) -> None:
        self._path_a_rooms = set(loop.path_a) if loop else set()
        self._path_b_rooms = set(loop.path_b) if loop else set()

    def set_validation(self, result: ValidationResult | None) -> None:
        self._validation = result

    def set_bounds(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h

    def set_dungeon(self, dungeon: Dungeon | None, expand_all: bool = False) -> None:
        self._dungeon = dungeon
        if expand_all and dungeon is not None:
            self._expanded = set(range(len(dungeon.levels)))
        else:
            self._expanded = set()

    def select_room(self, room_id: str | None) -> None:
        self._selected_room_id = room_id

    def expand_level(self, level_idx: int) -> None:
        self._expanded.add(level_idx)

    def toggle_level(self, level_idx: int) -> None:
        if level_idx in self._expanded:
            self._expanded.discard(level_idx)
        else:
            self._expanded.add(level_idx)

    def handle_click(self, x: float, y: float) -> bool:
        if self._dungeon is None:
            return False
        px, py, pw, ph = self._x, self._y, self._w, self._h
        if not (px <= x <= px + pw):
            return False
        tree_top = py + ph - HEADER_H
        tree_bot = py
        if not (tree_bot <= y <= tree_top):
            return False
        current_y = tree_top
        for i, level in enumerate(self._dungeon.levels):
            if current_y - ROW_H < tree_bot:
                break
            current_y -= ROW_H
            if current_y <= y <= current_y + ROW_H:
                self.toggle_level(i)
                return True
            if i in self._expanded:
                for _room in level.rooms:
                    if current_y - ROW_H < tree_bot:
                        break
                    current_y -= ROW_H
        return False

    def draw(self) -> None:
        x, y, w, h = self._x, self._y, self._w, self._h

        # Background
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_1)

        # Left and right borders
        arcade.draw_line(x, y, x, y + h, LINE, 1)
        arcade.draw_line(x + w, y, x + w, y + h, LINE, 1)

        # Header
        arcade.draw_rect_filled(
            arcade.XYWH(x + w / 2, y + h - HEADER_H / 2, w, HEADER_H), BG_2
        )
        arcade.draw_line(x, y + h - HEADER_H, x + w, y + h - HEADER_H, LINE, 1)
        draw_kicker("DUNGEON", x + PAD_MD, y + h - HEADER_H / 2)
        if self._validation is not None:
            if self._validation.is_valid:
                val_text, val_color = "✓ validated", TEAL
            else:
                n = len(self._validation.errors)
                val_text, val_color = f"⚠ {n} issues", AMBER
            arcade.draw_text(
                val_text, x + w - PAD_MD, y + h - HEADER_H / 2,
                val_color, font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="right", anchor_y="center",
            )

        # Tree body
        tree_top = y + h - HEADER_H
        tree_bot = y
        if self._dungeon is not None:
            self._draw_tree(x, tree_bot, w, tree_top - tree_bot)
        else:
            cx = x + w / 2
            cy = (tree_top + tree_bot) / 2
            arcade.draw_text(
                "⬡",
                cx, cy + 28,
                INK_4, font_size=28, font_name=FONT_UI,
                anchor_x="center", anchor_y="center",
            )
            arcade.draw_text(
                "No dungeon yet",
                cx, cy,
                INK_3, font_size=TEXT_BASE, font_name=FONT_UI,
                anchor_x="center", anchor_y="center",
            )
            arcade.draw_text(
                "Describe one in the chat →",
                cx, cy - 20,
                INK_4, font_size=TEXT_SM, font_name=FONT_UI,
                anchor_x="center", anchor_y="center",
            )

    def _draw_tree(self, x: float, y_bot: float, w: float, h: float) -> None:
        current_y = y_bot + h  # work top-down

        for i, level in enumerate(self._dungeon.levels):  # type: ignore[union-attr]
            if current_y - ROW_H < y_bot:
                break
            current_y -= ROW_H
            is_expanded = i in self._expanded
            arrow = "▾" if is_expanded else "▸"

            arcade.draw_text(
                f"{arrow}  L{i + 1} · {level.name}",
                x + PAD_SM, current_y + ROW_H / 2,
                TEAL, font_size=TEXT_BASE, font_name=FONT_UI, anchor_y="center",
            )

            if is_expanded:
                for room in level.rooms:
                    if current_y - ROW_H < y_bot:
                        break
                    current_y -= ROW_H
                    is_selected = room.id == self._selected_room_id
                    in_a = room.id in self._path_a_rooms
                    in_b = room.id in self._path_b_rooms

                    if is_selected:
                        arcade.draw_rect_filled(
                            arcade.XYWH(x + w / 2, current_y + ROW_H / 2, w, ROW_H), BG_HI
                        )

                    if in_a and in_b:
                        icon, color = "◆", INDIGO
                    elif in_a:
                        icon, color = "▶", TEAL
                    elif in_b:
                        icon, color = "◇", VIOLET
                    else:
                        icon, color = "▢", INK_3

                    if is_selected:
                        color = INK_1

                    arcade.draw_text(
                        f"  {icon} {room.id} · {room.name}",
                        x + INDENT, current_y + ROW_H / 2,
                        color,
                        font_size=TEXT_BASE, font_name=FONT_UI, anchor_y="center",
                    )
