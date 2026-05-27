"""LoopsPanel — interactive Loops tab for the Inspector Panel (Design Mode)."""
from __future__ import annotations

from collections.abc import Callable

import arcade

from dungeon_daddy.data.loop_assignment import auto_assign_loop_rooms
from dungeon_daddy.data.models import Level, Loop, LoopPattern
from dungeon_daddy.ui.theme import (
    BG_1,
    BG_2,
    BG_HI,
    FONT_MONO,
    FONT_UI,
    FONT_UI_MED,
    INK_2,
    INK_3,
    INK_4,
    LINE,
    PAD_MD,
    PAD_SM,
    PAD_XS,
    RADIUS_SM,
    TEAL,
    TEXT_BASE,
    TEXT_SM,
    TEXT_XS,
    VIOLET,
    draw_rounded_rect,
)

SECTION_GAP = 12


class LoopsPanel:
    """
    Functional Loops tab content for InspectorPanel.

    Owns no arcade.gui widgets — pure arcade.draw_* rendering.
    Behavioral methods (apply_pattern, add_sub_loop, remove_sub_loop,
    activate_loop) are callable directly and from on_mouse_press hit-testing.
    """

    def __init__(
        self,
        on_activate_loop: Callable[[str], None] | None = None,
    ) -> None:
        self._on_activate_loop = on_activate_loop
        self._level: Level | None = None
        self._patterns: list[LoopPattern] = []
        self._x = self._y = self._w = self._h = 0.0
        self._levels: list[Level] = []
        self._pattern_rects: dict[str, tuple[float, ...]] = {}
        self._remove_rects: dict[str, tuple[float, ...]] = {}
        self._level_rects: dict[int, tuple[float, ...]] = {}
        self._add_rects: dict[str, tuple[float, ...]] = {}
        self._loop_rects: dict[str, tuple[float, ...]] = {}

    # ------------------------------------------------------------------
    # Setup / resize
    # ------------------------------------------------------------------

    def setup(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def set_level(self, level: Level | None) -> None:
        self._level = level

    def set_levels(self, levels: list[Level]) -> None:
        self._levels = levels

    def set_patterns(self, patterns: list[LoopPattern]) -> None:
        self._patterns = patterns

    # ------------------------------------------------------------------
    # Behavioral public API
    # ------------------------------------------------------------------

    def apply_pattern(self, pattern_id: str, patterns: list[LoopPattern]) -> None:
        """Replace the current main loop with a new one using pattern_id."""
        if self._level is None:
            return
        assignment = auto_assign_loop_rooms(self._level)
        new_loop = Loop(
            id=self._main_loop_id(),
            pattern=pattern_id,
            note="",
            entry=assignment.entry,
            goal=assignment.goal,
            path_a=list(assignment.path_a),
            path_b=list(assignment.path_b),
            type="main",
        )
        self._level.loops = [lp for lp in self._level.loops if lp.type != "main"]
        self._level.loops.insert(0, new_loop)

    def add_sub_loop(self, pattern_id: str, patterns: list[LoopPattern]) -> None:
        """Append a sub-loop with the given pattern."""
        if self._level is None:
            return
        assignment = auto_assign_loop_rooms(self._level)
        sub_n = sum(1 for lp in self._level.loops if lp.type == "sub") + 1
        new_loop = Loop(
            id=f"L{self._level.id}-sub-{sub_n}",
            pattern=pattern_id,
            note="",
            entry=assignment.entry,
            goal=assignment.goal,
            path_a=list(assignment.path_a),
            path_b=list(assignment.path_b),
            type="sub",
        )
        self._level.loops.append(new_loop)

    def remove_sub_loop(self, loop_id: str) -> None:
        """Remove the loop with the given id from level.loops."""
        if self._level is None:
            return
        self._level.loops = [lp for lp in self._level.loops if lp.id != loop_id]

    def activate_loop(self, loop_id: str) -> None:
        """Fire on_activate_loop callback with loop_id."""
        if self._on_activate_loop:
            self._on_activate_loop(loop_id)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def on_mouse_press(self, x: float, y: float, modifiers: int) -> bool:
        """Handle click; returns True if the event was consumed."""
        for idx, (left, bottom, right, top) in self._level_rects.items():
            if left <= x <= right and bottom <= y <= top:
                if 0 <= idx < len(self._levels):
                    self.set_level(self._levels[idx])
                return True
        for loop_id, (left, bottom, right, top) in self._remove_rects.items():
            if left <= x <= right and bottom <= y <= top:
                self.remove_sub_loop(loop_id)
                return True
        for loop_id, (left, bottom, right, top) in self._loop_rects.items():
            if left <= x <= right and bottom <= y <= top:
                self.activate_loop(loop_id)
                return True
        for pat_id, (left, bottom, right, top) in self._add_rects.items():
            if left <= x <= right and bottom <= y <= top:
                self.add_sub_loop(pat_id, self._patterns)
                return True
        for pat_id, (left, bottom, right, top) in self._pattern_rects.items():
            if left <= x <= right and bottom <= y <= top:
                if modifiers & arcade.key.MOD_SHIFT:
                    self.add_sub_loop(pat_id, self._patterns)
                else:
                    self.apply_pattern(pat_id, self._patterns)
                return True
        return False

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self) -> None:
        x, y, w, h = self._x, self._y, self._w, self._h
        cur_y = y + h - SECTION_GAP
        self._pattern_rects = {}
        self._remove_rects = {}
        self._level_rects = {}
        self._add_rects = {}
        self._loop_rects = {}

        # --- Level picker chips ---
        if self._levels:
            cur_y -= 18
            chip_w, chip_h = 26, 18
            chip_gap = 4
            cx = x + PAD_MD
            for idx, lvl in enumerate(self._levels):
                is_active = (lvl is self._level)
                bg = TEAL if is_active else BG_2
                border = TEAL if is_active else LINE
                ink = BG_1 if is_active else INK_3
                draw_rounded_rect(cx + chip_w / 2, cur_y, chip_w, chip_h, RADIUS_SM, bg, border)
                arcade.draw_text(
                    f"L{idx + 1}", cx + chip_w / 2, cur_y,
                    ink, font_size=TEXT_XS, font_name=FONT_MONO,
                    anchor_x="center", anchor_y="center",
                )
                self._level_rects[idx] = (cx, cur_y - chip_h / 2, cx + chip_w, cur_y + chip_h / 2)
                cx += chip_w + chip_gap
            cur_y -= PAD_XS

        # --- Assigned loops section ---
        cur_y -= 18
        arcade.draw_text(
            "ACTIVE LOOPS", x + PAD_MD, cur_y,
            INK_4, font_size=TEXT_XS, font_name=FONT_MONO, anchor_y="center",
        )
        cur_y -= PAD_XS

        if self._level is None or not self._level.loops:
            cur_y -= 20
            arcade.draw_text(
                "No loop assigned yet.",
                x + PAD_MD, cur_y,
                INK_4, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
        else:
            for loop in self._level.loops:
                cur_y -= 22
                if cur_y < y:
                    break
                color = TEAL if loop.type == "main" else VIOLET
                draw_rounded_rect(x + w / 2, cur_y, w - PAD_MD * 2, 22, RADIUS_SM, BG_2, color)
                self._loop_rects[loop.id] = (x + PAD_MD, cur_y - 11, x + w - PAD_MD, cur_y + 11)
                arcade.draw_text(
                    loop.pattern, x + PAD_MD * 2, cur_y,
                    color, font_size=TEXT_SM, font_name=FONT_UI_MED, anchor_y="center",
                )
                if loop.type == "sub":
                    btn_right = x + w - PAD_MD
                    btn_left = btn_right - 18
                    self._remove_rects[loop.id] = (btn_left, cur_y - 9, btn_right, cur_y + 9)
                    arcade.draw_text(
                        "×", (btn_left + btn_right) / 2, cur_y,
                        color, font_size=TEXT_BASE, font_name=FONT_UI,
                        anchor_x="center", anchor_y="center",
                    )
                else:
                    arcade.draw_text(
                        "MAIN", x + w - PAD_MD * 2, cur_y,
                        color, font_size=TEXT_XS, font_name=FONT_MONO,
                        anchor_x="right", anchor_y="center",
                    )
                if loop.path_a:
                    cur_y -= 16
                    arcade.draw_text(
                        f"A: {' → '.join(loop.path_a[:4])}{'…' if len(loop.path_a) > 4 else ''}",
                        x + PAD_MD * 2, cur_y,
                        TEAL, font_size=TEXT_XS, font_name=FONT_MONO, anchor_y="center",
                    )
                if loop.path_b and loop.path_b != loop.path_a:
                    cur_y -= 14
                    arcade.draw_text(
                        f"B: {' → '.join(loop.path_b[:4])}{'…' if len(loop.path_b) > 4 else ''}",
                        x + PAD_MD * 2, cur_y,
                        VIOLET, font_size=TEXT_XS, font_name=FONT_MONO, anchor_y="center",
                    )
                cur_y -= PAD_SM

        # --- Pattern library section ---
        cur_y -= PAD_MD
        if cur_y < y + 60:
            return
        arcade.draw_line(x + PAD_MD, cur_y, x + w - PAD_MD, cur_y, LINE, 1)
        cur_y -= 18
        arcade.draw_text(
            "PATTERN LIBRARY", x + PAD_MD, cur_y,
            INK_4, font_size=TEXT_XS, font_name=FONT_MONO, anchor_y="center",
        )
        cur_y -= PAD_XS

        for pat in self._patterns:
            cur_y -= 20
            if cur_y < y:
                break
            draw_rounded_rect(x + w / 2, cur_y, w - PAD_MD * 2, 18, RADIUS_SM, BG_2, LINE)
            arcade.draw_text(
                pat.name, x + PAD_MD * 2, cur_y,
                INK_2, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
            # + button at far right
            btn_right = x + w - PAD_MD
            btn_left = btn_right - 18
            btn_mid = (btn_left + btn_right) / 2
            self._add_rects[pat.key] = (btn_left, cur_y - 9, btn_right, cur_y + 9)
            draw_rounded_rect(btn_mid, cur_y, 18, 16, RADIUS_SM, BG_HI, TEAL)
            arcade.draw_text(
                "+", btn_mid, cur_y,
                TEAL, font_size=TEXT_SM, font_name=FONT_UI_MED,
                anchor_x="center", anchor_y="center",
            )
            arcade.draw_text(
                f"A:{pat.path_a_length[:3]}  B:{pat.path_b_length[:3]}",
                btn_left - PAD_XS, cur_y,
                INK_4, font_size=TEXT_XS, font_name=FONT_MONO,
                anchor_x="right", anchor_y="center",
            )
            self._pattern_rects[pat.key] = (x + PAD_MD, cur_y - 9, btn_left, cur_y + 9)
            cur_y -= PAD_XS

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _main_loop_id(self) -> str:
        return f"L{self._level.id}-main" if self._level else "main"
