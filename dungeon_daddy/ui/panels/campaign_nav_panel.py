"""Campaign Nav Panel — left section navigator for Campaign Mode."""
from __future__ import annotations

import arcade

from dungeon_daddy.ui.theme import (
    BG_1,
    BG_2,
    BG_HI,
    FONT_MONO,
    FONT_SERIF,
    GOLD,
    INK_1,
    INK_4,
    LINE,
    PAD_MD,
    PAD_SM,
    TEXT_LG,
    TEXT_SM,
    draw_chip,
    draw_kicker,
)

HEADER_H: float = 38
TITLE_AREA_H: float = 56   # campaign title area between kicker and first section row
ROW_H: float = 32

_SECTION_META: dict[str, tuple[str, str]] = {
    "player_side": ("✦", "PARTY"),
    "monsters":    ("⚔", "MONSTERS"),
    "npcs":        ("◈", "NPCS"),
    "factions":    ("⬡", "FACTIONS"),
    "clocks":      ("◷", "CLOCKS"),
    "threats":     ("⚠", "THREATS"),
    "lore":        ("✦", "LORE"),
    "validation":  ("✓", "VALIDATE"),
}


class CampaignNavPanel:
    def __init__(self) -> None:
        self._x = self._y = self._w = self._h = 0.0
        self._sections: list[str] = []

    def set_bounds(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h

    def set_sections(self, sections: list[str]) -> None:
        self._sections = list(sections)

    # ------------------------------------------------------------------
    # Hit-test helpers
    # ------------------------------------------------------------------

    def section_at(self, x: float, y: float) -> str | None:
        if not self._sections:
            return None
        if not (self._x <= x <= self._x + self._w):
            return None
        top_of_sections = self._y + self._h - HEADER_H - TITLE_AREA_H
        for i, key in enumerate(self._sections):
            row_top = top_of_sections - i * ROW_H
            row_bot = row_top - ROW_H
            if row_bot <= y <= row_top:
                return key
        return None

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(
        self,
        active_section: str | None,
        title: str | None,
        counts: dict[str, int],
    ) -> None:
        px, py, pw, ph = self._x, self._y, self._w, self._h

        # Panel background
        arcade.draw_rect_filled(arcade.XYWH(px + pw / 2, py + ph / 2, pw, ph), BG_1)

        # Header strip
        header_cy = py + ph - HEADER_H / 2
        arcade.draw_rect_filled(arcade.XYWH(px + pw / 2, header_cy, pw, HEADER_H), BG_2)
        draw_kicker("CAMPAIGN", px + PAD_MD, header_cy)

        # Campaign title area
        title_cy = py + ph - HEADER_H - TITLE_AREA_H / 2
        if title:
            arcade.draw_text(
                title, px + PAD_MD, title_cy,
                INK_1, font_size=TEXT_LG, font_name=FONT_SERIF,
                anchor_x="left", anchor_y="center",
            )
        else:
            arcade.draw_text(
                "No campaign loaded", px + PAD_MD, title_cy,
                INK_4, font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="left", anchor_y="center", italic=True,
            )

        # Thin divider below title area
        divider_y = py + ph - HEADER_H - TITLE_AREA_H
        arcade.draw_line(px, divider_y, px + pw, divider_y, LINE, 1)

        # Section rows
        top_of_sections = divider_y
        for i, key in enumerate(self._sections):
            row_top = top_of_sections - i * ROW_H
            row_bot = row_top - ROW_H
            row_cy = (row_top + row_bot) / 2

            is_active = key == active_section
            bg = BG_HI if is_active else BG_1
            arcade.draw_rect_filled(
                arcade.XYWH(px + pw / 2, row_cy, pw, ROW_H), bg,
            )

            if is_active:
                # Gold left accent bar
                arcade.draw_rect_filled(
                    arcade.XYWH(px + 2, row_cy, 4, ROW_H - 2), GOLD,
                )

            glyph, label = _SECTION_META.get(key, ("?", key.upper()))
            text_color = GOLD if is_active else INK_4 if title is None else INK_1
            arcade.draw_text(
                f"{glyph}  {label}",
                px + PAD_MD + 6, row_cy,
                text_color, font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="left", anchor_y="center",
            )

            count = counts.get(key)
            if count is not None:
                draw_chip(str(count), px + pw - PAD_MD - 20, row_cy, "default", width=36)

            # Row divider
            arcade.draw_line(px, row_bot, px + pw, row_bot, LINE, 1)
