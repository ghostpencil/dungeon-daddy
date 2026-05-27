"""Map panel — hosts the grid renderer, loop overlay, variant tabs, and level stepper."""
from __future__ import annotations

from collections.abc import Callable

import arcade
import arcade.gui

from dungeon_daddy.data.models import Level, SessionState
from dungeon_daddy.map.grid_renderer import GridRenderer
from dungeon_daddy.map.loop_overlay import LoopOverlay
from dungeon_daddy.ui.theme import (
    BG_0,
    BG_1,
    BG_2,
    BG_3,
    BG_HI,
    FONT_MONO,
    FONT_SERIF,
    FONT_UI,
    FONT_UI_MED,
    INK_1,
    INK_3,
    INK_4,
    LINE,
    LINE_HI,
    PAD_MD,
    PANEL_STEPPER_WIDTH,
    TEAL,
    TEXT_4XL,
    TEXT_BASE,
    TEXT_SM,
    TEXT_XS,
    draw_chip,
    draw_kicker,
)

_HEADER_H = 38   # map panel header bar
_TAB_H = 32
_TAB_W = 64
_VARIANT_TABS = ["Grid", "Tiles", "Graph"]
_PAN_TAB_GAP = 16  # extra left margin separating Pan from view-mode tabs

_ZOOM_MIN = 0.5
_ZOOM_MAX = 3.0
_ZOOM_DEFAULT = 1.0
_ZOOM_SCROLL_FACTOR = 1.1   # multiplier per scroll notch
_ZOOM_KEY_STEP = 0.25        # additive step per key press


def _tab_style(active: bool) -> dict:
    return {
        "normal": arcade.gui.UIFlatButton.UIStyle(
            font_size=TEXT_SM, font_name=FONT_UI_MED,
            font_color=(*TEAL, 255) if active else (*INK_3, 255),
            bg=(*BG_HI, 255) if active else (*BG_1, 255),
            border=(*TEAL, 255) if active else (*LINE, 255),
            border_width=1,
        ),
        "hover": arcade.gui.UIFlatButton.UIStyle(
            font_size=TEXT_SM, font_name=FONT_UI_MED,
            font_color=(*INK_1, 255), bg=(*BG_3, 255),
            border=(*LINE_HI, 255), border_width=1,
        ),
        "press": arcade.gui.UIFlatButton.UIStyle(
            font_size=TEXT_SM, font_name=FONT_UI_MED,
            font_color=(*TEAL, 255), bg=(*BG_HI, 255),
            border=(*TEAL, 255), border_width=1,
        ),
        "disabled": arcade.gui.UIFlatButton.UIStyle(
            font_size=TEXT_SM, font_name=FONT_UI_MED,
            font_color=(*INK_4, 255), bg=(*BG_1, 255),
            border=(*LINE, 255), border_width=1,
        ),
    }


class MapPanel:
    """
    Play Mode map panel (right column).

    Layout:
        - Tab bar at top: [Grid] [Tiles] [Graph]
        - GridRenderer output fills the centre
        - LevelStepper on the right rail (PANEL_STEPPER_WIDTH px)
    """

    def __init__(
        self,
        on_level_change: Callable[[int], None],
        renderer: GridRenderer | None = None,
        overlay: LoopOverlay | None = None,
        on_variant_change: Callable[[str], None] | None = None,
        on_activate_loop: Callable[[str | None], None] | None = None,
    ) -> None:
        self._on_level_change = on_level_change
        self._renderer = renderer or GridRenderer()
        self._overlay = overlay or LoopOverlay()
        self._on_variant_change = on_variant_change
        self._on_activate_loop = on_activate_loop
        self._variant_btns: list[arcade.gui.UIFlatButton] = []
        self._active_variant = "Grid"
        self._active_tool: str = "select"   # "select" | "pan"
        self._pan_offset_x: float = 0.0
        self._pan_offset_y: float = 0.0
        self._is_panning: bool = False
        self._zoom_level: float = _ZOOM_DEFAULT
        self._x = self._y = self._w = self._h = 0.0
        self._level: Level | None = None
        self._state: SessionState | None = None
        self._dungeon_title: str = ""
        self._loop_strip_rects: dict[str, tuple[float, float, float, float]] = {}
        self._active_loop_id: str | None = None

        from dungeon_daddy.ui.widgets.level_stepper import LevelStepper
        self._stepper = LevelStepper(on_level_change)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setup(
        self,
        manager: arcade.gui.UIManager,
        x: float, y: float, w: float, h: float,
    ) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h
        self._setup_tabs(manager)
        stepper_x = x + w - PANEL_STEPPER_WIDTH
        self._stepper.setup(manager, stepper_x, y, PANEL_STEPPER_WIDTH, h - _HEADER_H)

    def teardown(self, manager: arcade.gui.UIManager) -> None:
        for btn in self._variant_btns:
            manager.remove(btn)
        self._variant_btns.clear()
        self._stepper.teardown(manager)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def load(self, level: Level, state: SessionState, total_levels: int = 1) -> None:
        self._level = level
        self._state = state
        self._total_levels = total_levels
        idx = state.current_level_idx + 1
        self._stepper.set_label(f"L{idx}")
        self._stepper.set_up_enabled(idx > 1)
        self._stepper.set_down_enabled(idx < total_levels)
        self._zoom_level = _ZOOM_DEFAULT
        self._center_level()
        self._active_loop_id = state.active_loop_id
        self._build_loop_strip_rects(level)

    def update_state(self, state: SessionState, total_levels: int) -> None:
        self._state = state
        idx = state.current_level_idx + 1
        self._stepper.set_label(f"L{idx}")
        self._stepper.set_up_enabled(idx > 1)
        self._stepper.set_down_enabled(idx < total_levels)

    def _center_level(self) -> None:
        """Set pan offset so the level's room bounding box is centred in the viewport."""
        if not (self._level and self._level.rooms and self._w > 0 and self._h > 0):
            self._pan_offset_x = 0.0
            self._pan_offset_y = 0.0
            return
        map_w = self._w - PANEL_STEPPER_WIDTH
        map_h = self._h - _HEADER_H
        effective = self._renderer.cell_px * self._zoom_level
        min_gx = min(r.x for r in self._level.rooms)
        min_gy = min(r.y for r in self._level.rooms)
        max_gx = max(r.x + r.w for r in self._level.rooms)
        max_gy = max(r.y + r.h for r in self._level.rooms)
        grid_cx = (min_gx + max_gx) / 2
        grid_cy = (min_gy + max_gy) / 2
        self._pan_offset_x = map_w / 2 - PAD_MD - grid_cx * effective
        self._pan_offset_y = map_h / 2 - PAD_MD - grid_cy * effective

    def set_renderer(self, renderer: GridRenderer) -> None:
        self._renderer = renderer

    def set_dungeon_title(self, title: str) -> None:
        self._dungeon_title = title

    # ------------------------------------------------------------------
    # Pan tool properties
    # ------------------------------------------------------------------

    @property
    def active_tool(self) -> str:
        return self._active_tool

    @property
    def pan_offset(self) -> tuple[float, float]:
        return self._pan_offset_x, self._pan_offset_y

    @property
    def zoom_level(self) -> float:
        return self._zoom_level

    # ------------------------------------------------------------------
    # Zoom helpers
    # ------------------------------------------------------------------

    def _apply_zoom(self, new_zoom: float, anchor_x: float, anchor_y: float) -> None:
        """Change zoom level, adjusting pan so (anchor_x, anchor_y) stays fixed."""
        new_zoom = max(_ZOOM_MIN, min(_ZOOM_MAX, new_zoom))
        if new_zoom == self._zoom_level:
            return
        # base origin relative to panel
        base_x = self._x + PAD_MD
        base_y = self._y + PAD_MD
        # map coordinate under anchor before zoom
        inv_old = 1.0 / self._zoom_level
        map_ax = (anchor_x - base_x - self._pan_offset_x) * inv_old
        map_ay = (anchor_y - base_y - self._pan_offset_y) * inv_old
        self._zoom_level = new_zoom
        # adjust pan so anchor still maps to same map coordinate
        self._pan_offset_x = anchor_x - base_x - map_ax * new_zoom
        self._pan_offset_y = anchor_y - base_y - map_ay * new_zoom

    def handle_mouse_scroll(
        self, x: float, y: float, scroll_x: float, scroll_y: float
    ) -> None:
        if not self._in_map_viewport(x, y):
            return
        new_zoom = self._zoom_level * (_ZOOM_SCROLL_FACTOR ** scroll_y)
        self._apply_zoom(new_zoom, anchor_x=x, anchor_y=y)

    def handle_key_press(self, key: int) -> None:
        map_cx = self._x + (self._w - PAD_MD) / 2
        map_cy = self._y + (self._h - _HEADER_H) / 2
        if key in (arcade.key.NUM_ADD, arcade.key.EQUAL):
            self._apply_zoom(self._zoom_level + _ZOOM_KEY_STEP, map_cx, map_cy)
        elif key == arcade.key.MINUS:
            self._apply_zoom(self._zoom_level - _ZOOM_KEY_STEP, map_cx, map_cy)
        elif key == arcade.key.KEY_0:
            self._apply_zoom(_ZOOM_DEFAULT, map_cx, map_cy)

    # ------------------------------------------------------------------
    # Mouse interaction (delegated from PlayView)
    # ------------------------------------------------------------------

    def handle_mouse_press(self, x: float, y: float, button: int) -> bool:
        """Handle map clicks: loop strip pills first, then pan tool."""
        if button == arcade.MOUSE_BUTTON_LEFT:
            for loop_id, (x1, y1, x2, y2) in self._loop_strip_rects.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    new_id = None if loop_id == self._active_loop_id else loop_id
                    self._active_loop_id = new_id
                    if self._on_activate_loop is not None:
                        self._on_activate_loop(new_id)
                    return True
        if self._active_tool == "pan" and button == arcade.MOUSE_BUTTON_LEFT:
            if self._in_map_viewport(x, y):
                self._is_panning = True
                return True
        return False

    def handle_mouse_drag(self, x: float, y: float, dx: float, dy: float, button: int) -> None:
        if self._is_panning and self._active_tool == "pan" and button == arcade.MOUSE_BUTTON_LEFT:
            self._pan_offset_x += dx
            self._pan_offset_y += dy

    def handle_mouse_release(self, x: float, y: float, button: int) -> None:
        if button == arcade.MOUSE_BUTTON_LEFT:
            self._is_panning = False

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self) -> None:
        x, y, w, h = self._x, self._y, self._w, self._h

        # Background
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_0)

        # Map content area (below header) — scissor-clipped
        map_w = w - PANEL_STEPPER_WIDTH
        map_h = h - _HEADER_H
        ctx = arcade.get_window().ctx
        old_scissor = ctx.scissor
        ctx.scissor = (int(x), int(y), int(map_w), int(map_h))
        try:
            if self._level is not None and self._state is not None:
                origin_x = x + PAD_MD + self._pan_offset_x
                origin_y = y + PAD_MD + self._pan_offset_y
                self._renderer.draw(self._level, self._state, origin_x, origin_y, self._zoom_level)
                self._overlay.draw(self._level, self._state, self._renderer, origin_x, origin_y, self._zoom_level)
            else:
                arcade.draw_text(
                    "Load a dungeon to view the map",
                    x + map_w / 2, y + map_h / 2,
                    INK_4, font_size=TEXT_BASE, font_name=FONT_UI,
                    anchor_x="center", anchor_y="center",
                )
        finally:
            ctx.scissor = old_scissor

        # Canvas overlays (drawn on top of renderer output, inside map area)
        if self._level is not None and self._state is not None:
            self._draw_level_overlay(x, y, map_w, map_h)
            for loop_id, (x1, y1, x2, y2) in self._loop_strip_rects.items():
                active = loop_id == self._active_loop_id
                loop = next((lp for lp in self._level.loops if lp.id == loop_id), None)
                label = loop.pattern if loop else loop_id
                pw = x2 - x1
                draw_chip(label, x1 + pw / 2, (y1 + y2) / 2, "teal" if active else "default", width=int(pw))

        # Header bar — drawn on top of map so it clips any renderer overflow
        header_y = y + h - _HEADER_H
        arcade.draw_rect_filled(
            arcade.XYWH(x + w / 2, header_y + _HEADER_H / 2, w, _HEADER_H), BG_2
        )
        arcade.draw_line(x, header_y, x + w, header_y, LINE, 1)
        draw_kicker("DUNGEON VIEWER", x + PAD_MD, header_y + _HEADER_H / 2)
        if self._dungeon_title:
            _chip_w = len(self._dungeon_title) * 7 + 20
            _chip_cx = x + 155 + _chip_w // 2
            draw_chip(self._dungeon_title, _chip_cx, header_y + _HEADER_H / 2, "gold", width=_chip_w)

        # Opaque stepper rail — paint over any map overflow before drawing widgets
        rail_x = x + w - PANEL_STEPPER_WIDTH
        rail_h = h - _HEADER_H
        arcade.draw_rect_filled(
            arcade.XYWH(rail_x + PANEL_STEPPER_WIDTH / 2, y + rail_h / 2, PANEL_STEPPER_WIDTH, rail_h),
            BG_1,
        )
        arcade.draw_line(rail_x, y, rail_x, y + rail_h, LINE, 1)
        self._stepper.draw()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _draw_level_overlay(self, x: float, y: float, map_w: float, map_h: float) -> None:
        """Top-left canvas overlay: level number, name, grid dimensions."""
        lvl = self._level
        idx = (self._state.current_level_idx + 1) if self._state else 1
        ox = x + PAD_MD
        # Level number chip (teal mono)
        arcade.draw_text(
            f"L{idx}",
            ox, y + map_h - PAD_MD,
            TEAL, font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="top",
        )
        # Level name (serif 22px)
        arcade.draw_text(
            lvl.name,
            ox + 28, y + map_h - PAD_MD,
            INK_1, font_size=TEXT_4XL, font_name=FONT_SERIF, anchor_y="top",
        )
        # Grid dimensions (mono, below name)
        max_x = max((r.x + r.w for r in lvl.rooms), default=0)
        max_y = max((r.y + r.h for r in lvl.rooms), default=0)
        arcade.draw_text(
            f"{max_x} × {max_y} cells",
            ox, y + map_h - PAD_MD - 30,
            INK_3, font_size=TEXT_XS, font_name=FONT_MONO, anchor_y="top",
        )

    def _build_loop_strip_rects(self, level: Level) -> None:
        self._loop_strip_rects = {}
        if not level.loops:
            return
        _PILL_W, _PILL_H, _PILL_GAP, _PILL_PAD = 110.0, 24.0, 6.0, 8.0
        map_w = self._w - PANEL_STEPPER_WIDTH
        right_edge = self._x + map_w - _PILL_PAD
        bottom = self._y + _PILL_PAD
        for loop in reversed(level.loops):
            x1 = right_edge - _PILL_W
            y1 = bottom
            self._loop_strip_rects[loop.id] = (x1, y1, x1 + _PILL_W, y1 + _PILL_H)
            right_edge = x1 - _PILL_GAP

    def _in_map_viewport(self, x: float, y: float) -> bool:
        """True if (x, y) is inside the map content area (excludes stepper rail and tab bar)."""
        return (
            self._x <= x < self._x + self._w - PANEL_STEPPER_WIDTH
            and self._y <= y < self._y + self._h - _HEADER_H
        )

    def _handle_variant_click(self, label: str) -> None:
        self._active_variant = label
        self._active_tool = "select"
        self._refresh_tab_styles()
        if self._on_variant_change is not None:
            self._on_variant_change(label.lower())

    def _refresh_tab_styles(self) -> None:
        for i, label in enumerate(_VARIANT_TABS):
            is_active = label == self._active_variant and self._active_tool == "select"
            self._variant_btns[i].style = _tab_style(is_active)
            self._variant_btns[i].trigger_render()
        pan_btn = self._variant_btns[-1]
        pan_btn.style = _tab_style(self._active_tool == "pan")
        pan_btn.trigger_render()

    def _setup_tabs(self, manager: arcade.gui.UIManager) -> None:
        x, y, w, h = self._x, self._y, self._w, self._h
        _BTN_W = 52
        _BTN_H = 22
        _BTN_GAP = 4
        map_w = w - PANEL_STEPPER_WIDTH

        # Right-align within map area; Grid/Tiles/Graph then gap then Pan
        total_w = 3 * _BTN_W + 2 * _BTN_GAP + _PAN_TAB_GAP + _BTN_W
        tab_x = x + map_w - PAD_MD - total_w
        tab_y = y + h - _HEADER_H - PAD_MD - _BTN_H   # bottom of button, inside canvas

        # View-mode tabs: Grid / Tiles / Graph
        for label in _VARIANT_TABS:
            is_active = label == self._active_variant and self._active_tool == "select"
            btn = arcade.gui.UIFlatButton(
                x=tab_x, y=tab_y,
                width=_BTN_W, height=_BTN_H,
                text=label,
                style=_tab_style(is_active),
            )
            captured_label = label

            @btn.event
            def on_click(event: arcade.gui.UIOnClickEvent, _lbl: str = captured_label) -> None:
                self._handle_variant_click(_lbl)

            self._variant_btns.append(btn)
            manager.add(btn)
            tab_x += _BTN_W + _BTN_GAP

        # Pan tool button — visually separated by an extra gap
        tab_x += _PAN_TAB_GAP
        pan_btn = arcade.gui.UIFlatButton(
            x=tab_x, y=tab_y,
            width=_BTN_W, height=_BTN_H,
            text="Pan",
            style=_tab_style(self._active_tool == "pan"),
        )

        @pan_btn.event
        def on_click(event: arcade.gui.UIOnClickEvent) -> None:  # noqa: F811
            self._active_tool = "pan"
            self._refresh_tab_styles()

        self._variant_btns.append(pan_btn)
        manager.add(pan_btn)
