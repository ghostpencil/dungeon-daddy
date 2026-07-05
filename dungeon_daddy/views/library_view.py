"""Library home screen — Phase 45 Slice 6."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import arcade

if TYPE_CHECKING:
    from dungeon_daddy.campaign.seed_library import CampaignSeedLibrary
    from dungeon_daddy.data.repository import DungeonRepository

from dungeon_daddy.ui.chrome import draw_title_bar, title_bar_mode_at
from dungeon_daddy.ui.theme import (
    BG_0,
    BG_2,
    BG_3,
    CHROME_TOTAL_HEIGHT,
    EMBER,
    FONT_MONO,
    FONT_SERIF,
    INK_1,
    INK_2,
    INK_4,
    LINE,
    PAD_MD,
    TEAL,
    TEXT_LG,
    TEXT_SM,
    VIOLET,
    draw_rounded_rect,
)

_log = logging.getLogger(__name__)

_PAD_SIDE = 24.0
_COL_GAP  = 16.0
_SECT_H   = 36.0
_CARD_H   = 68.0
_CARD_GAP =  8.0
_BTN_W    = 90.0
_BTN_H    = 20.0
_BTN_GAP  =  8.0
_TOP_PAD  = 16.0


class LibraryView(arcade.View):
    def __init__(self) -> None:
        super().__init__()
        self._init_state()

    def _init_state(self) -> None:
        self._dungeon_repo: DungeonRepository | None = None
        self._seed_library: CampaignSeedLibrary | None = None
        self._save_repo: DungeonRepository | None = None
        self._dungeon_list: list[str] = []
        self._seed_list: list[str] = []
        self._save_list: list[str] = []
        self._save_meta: dict[str, datetime | None] = {}

    # ------------------------------------------------------------------
    # Data sources
    # ------------------------------------------------------------------

    def set_sources(
        self,
        dungeon_repo: DungeonRepository,
        seed_library: CampaignSeedLibrary,
        save_repo: DungeonRepository,
    ) -> None:
        self._dungeon_repo = dungeon_repo
        self._seed_library = seed_library
        self._save_repo = save_repo

    def dungeon_slugs(self) -> list[str]:
        if self._dungeon_repo is None:
            return []
        return self._dungeon_repo.list_campaigns()

    def seed_slugs(self) -> list[str]:
        if self._seed_library is None:
            return []
        return self._seed_library.list()

    def save_slugs(self) -> list[str]:
        if self._save_repo is None:
            return []
        return self._save_repo.list_campaigns()

    def _refresh_save_meta(self) -> None:
        if self._save_repo is None:
            self._save_meta = {}
            return
        self._save_meta = {
            slug: self._save_repo.get_last_played(slug)
            for slug in self._save_list
        }

    def _refresh(self) -> None:
        self._dungeon_list = self.dungeon_slugs()
        self._seed_list = self.seed_slugs()
        self._save_list = self.save_slugs()
        self._refresh_save_meta()

    # ------------------------------------------------------------------
    # Card actions — delegate to window
    # ------------------------------------------------------------------

    def on_new_dungeon(self) -> None:
        self.window.new_dungeon()

    def on_open_dungeon(self, slug: str) -> None:
        self.window.open_in_designer(slug)

    def on_new_seed(self, slug: str) -> None:
        self.window.new_seed_from_dungeon(slug)

    def on_edit_seed(self, slug: str) -> None:
        self.window.edit_seed(slug)

    def on_publish(self, slug: str) -> None:
        self.window.publish_and_play(slug)

    def on_play_save(self, slug: str) -> None:
        self.window.launch_save_game(slug)

    def on_delete_save(self, slug: str) -> None:
        confirmed = self.window._ask_yes_no(
            "Delete Save",
            f"Delete save '{slug}'? This cannot be undone.",
        )
        if confirmed:
            self.window.delete_save(slug)

    def on_extract_seed(self, slug: str) -> None:
        self.window.extract_seed(slug)

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _col_layout(self) -> tuple[list[float], float, float]:
        """Returns (col_xs, col_w, content_top) from current window size."""
        ww = float(self.window.width)
        wh = float(self.window.height)
        col_w = (ww - 2 * _PAD_SIDE - 2 * _COL_GAP) / 3
        col_xs: list[float] = [
            _PAD_SIDE,
            _PAD_SIDE + col_w + _COL_GAP,
            _PAD_SIDE + 2 * (col_w + _COL_GAP),
        ]
        content_top = wh - CHROME_TOTAL_HEIGHT - _TOP_PAD
        return col_xs, col_w, content_top

    def _card_cy(self, content_top: float, card_i: int) -> float:
        card_top = content_top - _SECT_H - card_i * (_CARD_H + _CARD_GAP) - _CARD_GAP
        return card_top - _CARD_H / 2

    # ------------------------------------------------------------------
    # View lifecycle
    # ------------------------------------------------------------------

    def on_show_view(self) -> None:
        self.window.background_color = BG_0
        self._refresh()

    def on_draw(self) -> None:
        self.clear()
        draw_title_bar(self.window, mode="library")
        self._draw_library()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw_library(self) -> None:
        col_xs, col_w, content_top = self._col_layout()

        sections: list[tuple[Any, ...]] = [
            ("DUNGEONS",       self._dungeon_list, TEAL,   self._draw_dungeon_card,  True),
            ("CAMPAIGN SEEDS", self._seed_list,    VIOLET, self._draw_seed_card,     False),
            ("SAVES",          self._save_list,    EMBER,  self._draw_save_card,     False),
        ]

        for col_i, (label, slugs, accent, draw_fn, has_new_btn) in enumerate(sections):
            cx_left = col_xs[col_i]
            cx_right = cx_left + col_w
            cx_center = cx_left + col_w / 2
            sect_cy = content_top - _SECT_H / 2

            # Section header background
            arcade.draw_rect_filled(
                arcade.XYWH(cx_center, sect_cy, col_w, _SECT_H), BG_2
            )
            # Accent bar
            arcade.draw_rect_filled(
                arcade.XYWH(cx_left + 1.5, sect_cy, 3.0, _SECT_H - 8), accent
            )
            # Section label
            arcade.draw_text(
                label, cx_left + 12, sect_cy, INK_2,
                font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="left", anchor_y="center",
            )

            if has_new_btn:
                # "+ New" button in Dungeons header
                bw, bh = 64.0, 22.0
                bcx = cx_right - PAD_MD - bw / 2
                arcade.draw_rect_filled(arcade.XYWH(bcx, sect_cy, bw, bh), BG_2)
                arcade.draw_rect_outline(arcade.XYWH(bcx, sect_cy, bw, bh), accent, 1)
                arcade.draw_text(
                    "+ New", bcx, sect_cy, accent,
                    font_size=TEXT_SM, font_name=FONT_MONO,
                    anchor_x="center", anchor_y="center",
                )
            else:
                # Count badge
                arcade.draw_text(
                    str(len(slugs)), cx_right - PAD_MD, sect_cy, INK_4,
                    font_size=TEXT_SM, font_name=FONT_MONO,
                    anchor_x="right", anchor_y="center",
                )

            if not slugs:
                arcade.draw_text(
                    "Empty", cx_center, content_top - _SECT_H - 40, INK_4,
                    font_size=TEXT_SM, font_name=FONT_MONO,
                    anchor_x="center", anchor_y="center", italic=True,
                )
                continue

            for card_i, slug in enumerate(slugs):
                card_cy = self._card_cy(content_top, card_i)
                draw_rounded_rect(cx_center, card_cy, col_w, _CARD_H, 6, BG_2, LINE, 1)
                draw_fn(slug, cx_left, card_cy, col_w, accent)

    def _draw_dungeon_card(self, slug: str, x: float, cy: float, w: float, accent: tuple[int, int, int]) -> None:
        self._draw_card_title(slug, x, cy)
        self._draw_card_buttons(["Open in Designer", "New Seed"], x, cy, accent)

    def _draw_seed_card(self, slug: str, x: float, cy: float, w: float, accent: tuple[int, int, int]) -> None:
        self._draw_card_title(slug, x, cy)
        self._draw_card_buttons(["Edit", "Publish"], x, cy, accent)

    def _draw_save_card(self, slug: str, x: float, cy: float, w: float, accent: tuple[int, int, int]) -> None:
        dt = self._save_meta.get(slug)
        if dt is not None:
            subtitle = "Played: " + dt.strftime("%b %d, %Y")
        else:
            subtitle = "Never played"
        self._draw_card_title(slug, x, cy, subtitle=subtitle)
        self._draw_card_buttons(["Play", "Extract", "Delete"], x, cy, accent)

    def _draw_card_title(self, slug: str, x: float, cy: float, subtitle: str | None = None) -> None:
        top = cy + _CARD_H / 2
        display = slug.replace("-", " ").title()
        arcade.draw_text(
            display, x + PAD_MD, top - 18, INK_1,
            font_size=TEXT_LG, font_name=FONT_SERIF,
            anchor_x="left", anchor_y="center",
        )
        line2 = subtitle if subtitle is not None else slug
        arcade.draw_text(
            line2, x + PAD_MD, top - 36, INK_4,
            font_size=TEXT_SM, font_name=FONT_MONO,
            anchor_x="left", anchor_y="center",
        )

    def _draw_card_buttons(self, labels: list[str], x: float, cy: float, accent: tuple[int, int, int]) -> None:
        bot = cy - _CARD_H / 2
        btn_y = bot + _BTN_H / 2 + 4
        btn_x = x + PAD_MD
        for lbl in labels:
            bw = max(_BTN_W, len(lbl) * 7.0 + 16)
            bcx = btn_x + bw / 2
            arcade.draw_rect_filled(arcade.XYWH(bcx, btn_y, bw, _BTN_H), BG_3)
            arcade.draw_rect_outline(arcade.XYWH(bcx, btn_y, bw, _BTN_H), accent, 1)
            arcade.draw_text(
                lbl, bcx, btn_y, accent,
                font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="center", anchor_y="center",
            )
            btn_x += bw + _BTN_GAP

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def on_update(self, delta_time: float) -> None:
        pass

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        pill = title_bar_mode_at(x, y, self.window)
        if pill and pill != "library":
            self.window.switch_mode(pill)
            return
        self._handle_library_click(x, y)

    def _handle_library_click(self, x: float, y: float) -> None:
        col_xs, col_w, content_top = self._col_layout()

        # Check "+ New" button in Dungeons header (col 0)
        cx_right = col_xs[0] + col_w
        sect_cy = content_top - _SECT_H / 2
        bw, bh = 64.0, 22.0
        bcx = cx_right - PAD_MD - bw / 2
        if bcx - bw / 2 <= x <= bcx + bw / 2 and sect_cy - bh / 2 <= y <= sect_cy + bh / 2:
            self.on_new_dungeon()
            return

        sections: list[tuple[Any, ...]] = [
            (self._dungeon_list, ["Open in Designer", "New Seed"],
             [self.on_open_dungeon, self.on_new_seed]),
            (self._seed_list, ["Edit", "Publish"],
             [self.on_edit_seed, self.on_publish]),
            (self._save_list, ["Play", "Extract", "Delete"],
             [self.on_play_save, self.on_extract_seed, self.on_delete_save]),
        ]

        for col_i, (slugs, labels, actions) in enumerate(sections):
            cx_left = col_xs[col_i]
            if not (cx_left <= x <= cx_left + col_w):
                continue
            for card_i, slug in enumerate(slugs):
                card_cy = self._card_cy(content_top, card_i)
                bot = card_cy - _CARD_H / 2
                btn_y = bot + _BTN_H / 2 + 4
                btn_x = cx_left + PAD_MD
                for lbl, action in zip(labels, actions):
                    bw = max(_BTN_W, len(lbl) * 7.0 + 16)
                    bcx = btn_x + bw / 2
                    if (bcx - bw / 2 <= x <= bcx + bw / 2 and
                            btn_y - _BTN_H / 2 <= y <= btn_y + _BTN_H / 2):
                        action(slug)
                        return
                    btn_x += bw + _BTN_GAP
