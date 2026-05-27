"""Inspector Panel — Settings / Loops tabbed panel for Design Mode."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import arcade
import arcade.gui

from dungeon_daddy.data.models import ContextDocType, Dungeon, LoopPatternCatalog
from dungeon_daddy.ui.panels.loops_panel import LoopsPanel
from dungeon_daddy.ui.theme import (
    BG_1,
    BG_2,
    BG_3,
    BG_HI,
    FONT_MONO,
    FONT_SERIF,
    FONT_UI,
    FONT_UI_MED,
    INK_2,
    INK_3,
    INK_4,
    LINE,
    LINE_HI,
    PAD_MD,
    PAD_SM,
    PAD_XS,
    TEAL,
    TEAL_DIM,
    TEXT_LG,
    TEXT_SM,
    draw_chip,  # noqa: F401  # patched in tests
    draw_kicker,
    draw_rounded_rect,  # noqa: F401  # patched in tests
)


@dataclass
class ContextDocStatus:
    label: str
    doc_type: ContextDocType
    level_id: int | None
    word_count: int | None  # None = pending/empty


HEADER_H = 38
FOOTER_H = 44
TAB_H = 32
SECTION_GAP = 12


class InspectorPanel:
    """
    Right panel with Settings and Loops tabs.

    Pure arcade.draw_* for Phase 5 — no interactive widgets.
    Tab buttons are drawn as clickable-looking rectangles but
    are not wired to UIManager in this phase.
    """

    def __init__(
        self,
        on_activate_loop: Callable[[str], None] | None = None,
    ) -> None:
        self._dungeon: Dungeon | None = None
        self._active_tab = "settings"
        self._x = self._y = self._w = self._h = 0.0
        self._test_drive_rect: tuple[float, float, float, float] | None = None
        self._start_play_rect: tuple[float, float, float, float] | None = None
        self._tab_rects: dict[str, tuple[float, float, float, float]] = {}
        self._loops_panel = LoopsPanel(on_activate_loop=on_activate_loop)
        self._on_settings_change: Callable[..., Any] | None = None
        self._complexity_seg_rects: list[tuple[float, float, float, float, str]] = []
        self._context_doc_statuses: list[ContextDocStatus] = []
        self._context_doc_rects: list[tuple[float, float, float, float, ContextDocStatus]] = []
        self._on_context_doc_click: Callable[..., Any] | None = None
        self._theme_scroll_offset: int = 0
        self._theme_max_scroll: int = 0
        self._theme_area_rect: tuple[float, float, float, float] | None = None
        self._is_saved: bool = False
        self._has_session: bool = False

    def set_saved_state(self, is_saved: bool, has_session: bool) -> None:
        self._is_saved = is_saved
        self._has_session = has_session

    def setup(
        self,
        manager: arcade.gui.UIManager,
        x: float, y: float, w: float, h: float,
    ) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h
        self._loops_panel.setup(*self._content_rect())

    def teardown(self, manager: arcade.gui.UIManager) -> None:
        pass

    def resize(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h
        self._loops_panel.setup(*self._content_rect())

    def set_dungeon(self, dungeon: Dungeon | None) -> None:
        self._dungeon = dungeon
        if dungeon and dungeon.levels:
            self._loops_panel.set_levels(dungeon.levels)
            self._loops_panel.set_level(dungeon.levels[0])
            if dungeon.loop_patterns:
                patterns = list(dungeon.loop_patterns.values())
            else:
                patterns = list(LoopPatternCatalog.load_bundled().patterns.values())
            self._loops_panel.set_patterns(patterns)
        else:
            self._loops_panel.set_levels([])
            self._loops_panel.set_level(None)

    def set_active_level(self, level_idx: int) -> None:
        """Sync LoopsPanel to the level at level_idx in the current dungeon."""
        if self._dungeon and 0 <= level_idx < len(self._dungeon.levels):
            self._loops_panel.set_level(self._dungeon.levels[level_idx])
        else:
            self._loops_panel.set_level(None)

    def set_on_settings_change(self, callback: Callable[..., Any]) -> None:
        self._on_settings_change = callback

    def on_settings_field_change(self, field: str, value: str) -> None:
        if self._dungeon is None:
            return
        meta = self._dungeon.meta
        int_fields = {"party_size", "party_level", "num_levels"}
        if field in int_fields:
            try:
                setattr(meta, field, int(value))
            except (ValueError, TypeError):
                return
        else:
            setattr(meta, field, value)
        if self._on_settings_change:
            self._on_settings_change(meta)

    def set_context_doc_statuses(self, statuses: list[ContextDocStatus]) -> None:
        self._context_doc_statuses = statuses

    def set_on_context_doc_click(self, callback: Callable[..., Any]) -> None:
        self._on_context_doc_click = callback

    def on_complexity_change(self, value: str) -> None:
        if self._dungeon is None:
            return
        self._dungeon.meta.complexity = value
        if self._on_settings_change:
            self._on_settings_change(self._dungeon.meta)

    @staticmethod
    def _wrap_text(text: str, chars_per_line: int) -> list[str]:
        if not text:
            return []
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            if not current:
                current = word
            elif len(current) + 1 + len(word) <= chars_per_line:
                current += " " + word
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def on_mouse_scroll(self, x: float, y: float, scroll_y: int) -> bool:
        if not self._theme_area_rect:
            return False
        left, b, r, t = self._theme_area_rect
        if not (left <= x <= r and b <= y <= t):
            return False
        self._theme_scroll_offset = max(
            0, min(self._theme_max_scroll, self._theme_scroll_offset - scroll_y)
        )
        return True

    def _content_rect(self) -> tuple[float, float, float, float]:
        """(x, y_bot, w, h) of the tab content area."""
        tab_y = self._y + self._h - HEADER_H - TAB_H
        content_bot = self._y + FOOTER_H
        return self._x, content_bot, self._w, tab_y - content_bot

    def hit_test_drive(self, x: float, y: float) -> bool:
        if not self._test_drive_rect or not (self._dungeon and self._dungeon.levels):
            return False
        left, b, r, t = self._test_drive_rect
        return left <= x <= r and b <= y <= t

    def hit_start_play(self, x: float, y: float) -> bool:
        if not self._is_saved:
            return False
        if not self._start_play_rect or not (self._dungeon and self._dungeon.levels):
            return False
        left, b, r, t = self._start_play_rect
        return left <= x <= r and b <= y <= t

    def on_mouse_press(self, x: float, y: float, modifiers: int = 0) -> bool:
        """Handle click; returns True if consumed."""
        for tab_id, (left, b, r, t) in self._tab_rects.items():
            if left <= x <= r and b <= y <= t:
                self._active_tab = tab_id
                return True
        if self._active_tab == "settings":
            for left, b, r, t, label in self._complexity_seg_rects:
                if left <= x <= r and b <= y <= t:
                    self.on_complexity_change(label)
                    return True
            for left, b, r, t, status in self._context_doc_rects:
                if left <= x <= r and b <= y <= t:
                    if self._on_context_doc_click:
                        self._on_context_doc_click(status.doc_type, status.level_id)
                    return True
        if self._active_tab == "loops":
            return self._loops_panel.on_mouse_press(x, y, modifiers)
        return False

    def draw(self) -> None:
        x, y, w, h = self._x, self._y, self._w, self._h

        # Background
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_1)

        # Left border
        arcade.draw_line(x, y, x, y + h, LINE, 1)

        # Header
        arcade.draw_rect_filled(
            arcade.XYWH(x + w / 2, y + h - HEADER_H / 2, w, HEADER_H), BG_2
        )
        arcade.draw_line(x, y + h - HEADER_H, x + w, y + h - HEADER_H, LINE, 1)
        draw_kicker("INSPECTOR", x + PAD_MD, y + h - HEADER_H / 2)

        # Tab buttons
        tab_y = y + h - HEADER_H - TAB_H
        tab_w = w / 2
        for i, (tab_id, label) in enumerate([("settings", "Settings"), ("loops", "Loops")]):
            tab_x = x + i * tab_w
            is_active = self._active_tab == tab_id
            bg = BG_HI if is_active else BG_2
            border = TEAL if is_active else LINE
            arcade.draw_rect_filled(
                arcade.XYWH(tab_x + tab_w / 2, tab_y + TAB_H / 2, tab_w, TAB_H), bg
            )
            arcade.draw_rect_outline(
                arcade.XYWH(tab_x + tab_w / 2, tab_y + TAB_H / 2, tab_w, TAB_H), border, 1
            )
            arcade.draw_text(
                label, tab_x + tab_w / 2, tab_y + TAB_H / 2,
                TEAL if is_active else INK_3,
                font_size=TEXT_SM, font_name=FONT_UI_MED,
                anchor_x="center", anchor_y="center",
            )
            self._tab_rects[tab_id] = (tab_x, tab_y, tab_x + tab_w, tab_y + TAB_H)

        arcade.draw_line(x, tab_y, x + w, tab_y, LINE, 1)

        # Footer buttons
        footer_y = y
        arcade.draw_line(x, footer_y + FOOTER_H, x + w, footer_y + FOOTER_H, LINE, 1)
        arcade.draw_rect_filled(
            arcade.XYWH(x + w / 2, footer_y + FOOTER_H / 2, w, FOOTER_H), BG_1
        )
        # "Test Drive" ghost button — lights up when levels exist
        ghost_w, btn_h = 100, 28
        btn_cy = footer_y + FOOTER_H / 2
        has_lvls = bool(self._dungeon and self._dungeon.levels)
        ghost_border = TEAL if has_lvls else LINE
        ghost_ink = INK_2 if has_lvls else INK_3
        arcade.draw_rect_outline(
            arcade.XYWH(x + PAD_MD + ghost_w / 2, btn_cy, ghost_w, btn_h),
            ghost_border, 1,
        )
        arcade.draw_text(
            "Test Drive", x + PAD_MD + ghost_w / 2, btn_cy,
            ghost_ink, font_size=TEXT_SM, font_name=FONT_UI,
            anchor_x="center", anchor_y="center",
        )
        # store hit rect (left, bottom, right, top)
        self._test_drive_rect = (
            x + PAD_MD, btn_cy - btn_h / 2,
            x + PAD_MD + ghost_w, btn_cy + btn_h / 2,
        )
        # "Start Play →" / "Continue Play →" primary button
        primary_w = 110
        primary_x = x + w - PAD_MD - primary_w
        primary_color = TEAL if self._is_saved else TEAL_DIM
        arcade.draw_rect_filled(
            arcade.XYWH(primary_x + primary_w / 2, btn_cy, primary_w, btn_h),
            primary_color,
        )
        start_play_label = "Continue Play →" if self._has_session else "Start Play →"
        arcade.draw_text(
            start_play_label, primary_x + primary_w / 2, btn_cy,
            INK_2 if self._is_saved else INK_4, font_size=TEXT_SM, font_name=FONT_UI_MED,
            anchor_x="center", anchor_y="center",
        )
        self._start_play_rect = (
            primary_x, btn_cy - btn_h / 2,
            primary_x + primary_w, btn_cy + btn_h / 2,
        )

        # Tab content
        content_top = tab_y
        content_bot = footer_y + FOOTER_H
        if self._active_tab == "settings":
            self._draw_settings(x, content_bot, w, content_top - content_bot)
        else:
            self._draw_loops(x, content_bot, w, content_top - content_bot)

    def _draw_settings(self, x: float, y_bot: float, w: float, h: float) -> None:
        meta = self._dungeon.meta if self._dungeon else None
        cur_y = y_bot + h - SECTION_GAP

        def section_heading(label: str) -> None:
            nonlocal cur_y
            cur_y -= 22
            arcade.draw_text(
                label, x + PAD_MD, cur_y,
                INK_2, font_size=TEXT_LG, font_name=FONT_SERIF, anchor_y="center",
            )
            cur_y -= PAD_SM

        def field_row(label: str, value: str) -> None:
            nonlocal cur_y
            cur_y -= 28
            arcade.draw_text(
                label, x + PAD_MD, cur_y,
                INK_3, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
            fld_x = x + 80
            fld_w = w - 80 - PAD_SM
            arcade.draw_rect_filled(
                arcade.XYWH(fld_x + fld_w / 2, cur_y, fld_w, 22), BG_2
            )
            arcade.draw_rect_outline(
                arcade.XYWH(fld_x + fld_w / 2, cur_y, fld_w, 22), LINE, 1
            )
            ink = INK_2 if value else INK_4
            arcade.draw_text(
                value or "—", fld_x + PAD_XS, cur_y,
                ink, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
            cur_y -= PAD_XS

        party_doc_exists = any(
            s.doc_type == ContextDocType.PARTY and s.word_count is not None
            for s in self._context_doc_statuses
        )
        section_heading("Party")
        field_row("Size", str(meta.party_size) if (meta and party_doc_exists) else "0")
        field_row("Level", str(meta.party_level) if (meta and party_doc_exists) else "0")

        cur_y -= SECTION_GAP
        section_heading("Dungeon")

        # Theme — multi-line text area with scrollbar
        theme_value = meta.theme if meta else ""
        _VISIBLE_LINES = 4
        _LINE_H = 16
        _AREA_H = _VISIBLE_LINES * _LINE_H + PAD_SM
        _SCROLLBAR_W = 8
        fld_x = x + 80
        fld_w = w - 80 - PAD_SM
        text_content_w = fld_w - _SCROLLBAR_W - PAD_XS * 2
        chars_per_line = max(10, int(text_content_w / 7.0))
        wrapped = self._wrap_text(theme_value, chars_per_line)
        total_lines = len(wrapped)
        self._theme_max_scroll = max(0, total_lines - _VISIBLE_LINES)
        self._theme_scroll_offset = min(self._theme_scroll_offset, self._theme_max_scroll)

        cur_y -= PAD_SM
        area_top = cur_y
        area_bottom = area_top - _AREA_H
        area_center_y = area_top - _AREA_H / 2

        arcade.draw_text(
            "Theme", x + PAD_MD, area_top - _LINE_H / 2,
            INK_3, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
        )
        arcade.draw_rect_filled(
            arcade.XYWH(fld_x + fld_w / 2, area_center_y, fld_w, _AREA_H), BG_2
        )
        arcade.draw_rect_outline(
            arcade.XYWH(fld_x + fld_w / 2, area_center_y, fld_w, _AREA_H), LINE, 1
        )
        ink = INK_2 if theme_value else INK_4
        text_x = fld_x + PAD_XS
        if theme_value:
            for i, line in enumerate(
                wrapped[self._theme_scroll_offset:self._theme_scroll_offset + _VISIBLE_LINES]
            ):
                line_cy = area_top - PAD_XS - (i + 0.5) * _LINE_H
                arcade.draw_text(
                    line, text_x, line_cy,
                    ink, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
                )
        else:
            arcade.draw_text(
                "—", text_x, area_top - PAD_XS - _LINE_H / 2,
                INK_4, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
        if total_lines > _VISIBLE_LINES:
            sb_x = fld_x + fld_w - _SCROLLBAR_W
            sb_h = _AREA_H - 4
            sb_cy = area_center_y
            thumb_h = max(12, int(sb_h * _VISIBLE_LINES / total_lines))
            scroll_frac = self._theme_scroll_offset / self._theme_max_scroll
            thumb_cy = (area_top - 2) - scroll_frac * (sb_h - thumb_h) - thumb_h / 2
            arcade.draw_rect_filled(
                arcade.XYWH(sb_x + _SCROLLBAR_W / 2, sb_cy, _SCROLLBAR_W, sb_h), BG_3
            )
            arcade.draw_rect_filled(
                arcade.XYWH(sb_x + _SCROLLBAR_W / 2, thumb_cy, _SCROLLBAR_W - 2, thumb_h),
                LINE_HI,
            )
        self._theme_area_rect = (fld_x, area_bottom, fld_x + fld_w, area_top)
        cur_y = area_bottom - PAD_XS

        field_row("Levels", str(meta.num_levels) if meta else "3")

        # Complexity label
        cur_y -= 22
        arcade.draw_text(
            "Complexity", x + PAD_MD, cur_y,
            INK_3, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
        )
        # Complexity segmented control
        cur_y -= 26
        seg_labels = ["Light", "Moderate", "Deep"]
        seg_w = (w - PAD_MD * 2) / 3
        active_complexity = meta.complexity if meta else "Moderate"
        self._complexity_seg_rects = []
        for i, seg in enumerate(seg_labels):
            sx = x + PAD_MD + i * seg_w
            is_active = seg == active_complexity
            arcade.draw_rect_filled(
                arcade.XYWH(sx + seg_w / 2, cur_y, seg_w, 24),
                BG_HI if is_active else BG_2,
            )
            arcade.draw_rect_outline(
                arcade.XYWH(sx + seg_w / 2, cur_y, seg_w, 24), LINE, 1
            )
            arcade.draw_text(
                seg, sx + seg_w / 2, cur_y,
                TEAL if is_active else INK_3,
                font_size=TEXT_SM, font_name=FONT_UI,
                anchor_x="center", anchor_y="center",
            )
            self._complexity_seg_rects.append(
                (sx, cur_y - 12, sx + seg_w, cur_y + 12, seg)
            )

        cur_y -= 12 + SECTION_GAP

        # Context docs section
        section_heading("Context docs")
        self._context_doc_rects = []
        row_h = 22
        for status in self._context_doc_statuses:
            cur_y -= row_h
            if cur_y < y_bot:
                break
            doc_ok = status.word_count is not None
            doc_status_text = f"✓ {status.word_count} words" if doc_ok else "○ pending"
            arcade.draw_text(
                status.label, x + PAD_MD, cur_y,
                INK_2, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
            arcade.draw_text(
                doc_status_text, x + w - PAD_MD, cur_y,
                TEAL if doc_ok else INK_4,
                font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="right", anchor_y="center",
            )
            self._context_doc_rects.append(
                (x, cur_y - row_h / 2, x + w, cur_y + row_h / 2, status)
            )
            cur_y -= PAD_XS

    def _draw_loops(self, x: float, y_bot: float, w: float, h: float) -> None:
        self._loops_panel.draw()
