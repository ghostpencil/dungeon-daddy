"""
Chrome drawing helpers — menu bar, title bar, dropdown renderer.
Called at the start of every on_draw() in both views, before UIManager.draw().
Uses arcade.draw_* primitives directly (not part of the UIManager tree).
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

import arcade

from dungeon_daddy.ui.theme import (
    BG_0,
    BG_1,
    BG_2,
    CHROME_MENUBAR_HEIGHT,
    CHROME_TITLEBAR_HEIGHT,
    FONT_SIGIL,
    FONT_UI,
    FONT_UI_MED,
    INK_1,
    INK_2,
    INK_4,
    LINE,
    PAD_MD,
    PAD_SM,
    TEAL,
    TEXT_BASE,
    TEXT_MD,
    TEXT_SM,
    VIOLET,
)

_log = logging.getLogger(__name__)

# px width per character used to estimate label hit regions (matches draw_menu_bar)
_CHAR_W = 7
_DROP_W = 160
_ITEM_H = 22

# ---------------------------------------------------------------------------
# MenuAction — every menu item is wired, nothing is decorative
# ---------------------------------------------------------------------------

@dataclass
class MenuAction:
    """A single item in the application menu."""
    label: str
    handler: Callable[[], None]
    enabled: bool = True
    implemented: bool = True


# ---------------------------------------------------------------------------
# Menu bar  (top 26 px)
# ---------------------------------------------------------------------------

def draw_menu_bar(window: object) -> None:
    """
    Draw the application menu bar across the top of the window.
    window must have .width and .height attributes.
    """
    w: int = window.width  # type: ignore[attr-defined]
    h: int = window.height  # type: ignore[attr-defined]
    bar_y = h - CHROME_MENUBAR_HEIGHT / 2

    # Background strip
    arcade.draw_rect_filled(
        arcade.XYWH(w / 2, h - CHROME_MENUBAR_HEIGHT / 2, w, CHROME_MENUBAR_HEIGHT),
        BG_0,
    )

    # Bottom border line
    arcade.draw_line(0, h - CHROME_MENUBAR_HEIGHT, w, h - CHROME_MENUBAR_HEIGHT, LINE, 1)

    # Menu labels — use window._menu keys if available, else default set
    _default_labels = ["File", "Edit", "Dungeon", "Play", "View", "Window", "Help"]
    menu_labels = list(getattr(window, "_menu", {}).keys()) or _default_labels
    x = PAD_MD
    for label in menu_labels:
        arcade.draw_text(
            label,
            x, bar_y,
            INK_2,
            font_size=TEXT_SM,
            font_name=FONT_UI,
            anchor_x="left",
            anchor_y="center",
        )
        x += len(label) * 7 + PAD_MD * 2

    # Right-side sigil decoration
    arcade.draw_text(
        "✦",
        w - PAD_MD, bar_y,
        VIOLET,
        font_size=TEXT_SM,
        font_name=FONT_SIGIL,
        anchor_x="right",
        anchor_y="center",
    )


# ---------------------------------------------------------------------------
# Title bar  (44 px below menu bar)
# ---------------------------------------------------------------------------

def draw_title_bar(
    window: object,
    mode: str,
    on_mode: Callable[[str], None],
) -> None:
    """
    Draw the title bar showing the app name, current mode, and mode toggle.
    mode: "design" | "play"
    on_mode: called with "design" or "play" when the toggle is clicked.
    (Click handling is done by UIManager widgets — this function only draws.)
    """
    w: int = window.width  # type: ignore[attr-defined]
    h: int = window.height  # type: ignore[attr-defined]
    bar_top = h - CHROME_MENUBAR_HEIGHT
    bar_mid = bar_top - CHROME_TITLEBAR_HEIGHT / 2

    # Background
    arcade.draw_rect_filled(
        arcade.XYWH(w / 2, bar_mid, w, CHROME_TITLEBAR_HEIGHT),
        BG_1,
    )

    # Bottom border
    arcade.draw_line(
        0, bar_top - CHROME_TITLEBAR_HEIGHT,
        w, bar_top - CHROME_TITLEBAR_HEIGHT,
        LINE, 1,
    )

    # App title
    arcade.draw_text(
        "DUNGEON DADDY",
        PAD_MD, bar_mid,
        TEAL,
        font_size=TEXT_MD,
        font_name=FONT_UI_MED,
        anchor_x="left",
        anchor_y="center",
    )

    # Mode indicator badge (right side)
    mode_label = "DESIGN MODE" if mode == "design" else "PLAY MODE"
    mode_color = VIOLET if mode == "design" else TEAL
    badge_w, badge_h = 100, 22
    badge_cx = w - PAD_MD - badge_w / 2
    arcade.draw_rect_filled(arcade.XYWH(badge_cx, bar_mid, badge_w, badge_h), BG_2)
    arcade.draw_rect_outline(arcade.XYWH(badge_cx, bar_mid, badge_w, badge_h), mode_color, 1)
    arcade.draw_text(
        mode_label,
        badge_cx, bar_mid,
        mode_color,
        font_size=TEXT_SM,
        font_name=FONT_UI_MED,
        anchor_x="center",
        anchor_y="center",
    )


# ---------------------------------------------------------------------------
# Dropdown renderer  (called when a menu is open)
# ---------------------------------------------------------------------------

def draw_dropdown(
    actions: list[MenuAction],
    x: float,
    y: float,
) -> None:
    """
    Draw a dropdown panel for a list of MenuActions.
    x, y: top-left corner of the dropdown.
    Items with implemented=False are dimmed (INK_4) but still clickable —
    their handler will be called (typically _nyi which logs and returns).
    Closes when the user clicks outside (handled by the view, not here).
    """
    item_h = 22
    pad = PAD_SM
    width = 160
    total_h = len(actions) * item_h + pad * 2

    # Background panel
    arcade.draw_rect_filled(
        arcade.XYWH(x + width / 2, y - total_h / 2, width, total_h),
        BG_2,
    )
    arcade.draw_rect_outline(
        arcade.XYWH(x + width / 2, y - total_h / 2, width, total_h),
        LINE, 1,
    )

    # Items
    item_y = y - pad - item_h / 2
    for action in actions:
        color = INK_4 if not action.implemented else (INK_1 if action.enabled else INK_4)
        arcade.draw_text(
            action.label,
            x + pad, item_y,
            color,
            font_size=TEXT_BASE,
            font_name=FONT_UI,
            anchor_x="left",
            anchor_y="center",
        )
        item_y -= item_h


# ---------------------------------------------------------------------------
# MenuBar — stateful wrapper that owns dropdown open/close state
# ---------------------------------------------------------------------------

class MenuBar:
    """
    Wraps the application menu dict with click handling and dropdown state.

    Usage:
        bar = MenuBar(menu_dict)
        # in on_draw:
        bar.draw(window)
        # in on_mouse_press:
        if bar.handle_click(x, y, window):
            return
    """

    def __init__(self, menu: dict[str, list[MenuAction]]) -> None:
        self._menu = menu
        self._open: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def draw(self, window: object) -> None:
        draw_menu_bar(window)
        if self._open and self._open in self._menu:
            ox, oy = self._drop_origin(window, self._open)
            draw_dropdown(self._menu[self._open], ox, oy)

    def handle_click(self, x: float, y: float, window: object) -> bool:
        """Return True if click was consumed by the menu bar or an open dropdown."""
        h: int = window.height  # type: ignore[attr-defined]

        # Click inside the menu bar strip?
        if y >= h - CHROME_MENUBAR_HEIGHT:
            hit = self._label_at(x, window)
            # Toggle: clicking the open menu closes it; clicking another opens it
            self._open = None if self._open == hit else hit
            return True

        # Click while a dropdown is open?
        if self._open:
            action = self._item_at(x, y, window)
            self._open = None
            if action is not None and action.enabled:
                action.handler()
            return True  # close menu on any click outside items too

        return False

    # ------------------------------------------------------------------
    # Hit-test helpers
    # ------------------------------------------------------------------

    def _label_slots(self, window: object) -> list[tuple[str, float, float]]:
        """(label, x_start, x_end) for each menu label."""
        slots: list[tuple[str, float, float]] = []
        x = float(PAD_MD)
        for label in self._menu:
            slot_w = len(label) * _CHAR_W + PAD_MD * 2
            slots.append((label, x, x + slot_w))
            x += slot_w
        return slots

    def _label_at(self, x: float, window: object) -> str | None:
        for label, x1, x2 in self._label_slots(window):
            if x1 <= x <= x2:
                return label
        return None

    def _drop_origin(self, window: object, label: str) -> tuple[float, float]:
        h: int = window.height  # type: ignore[attr-defined]
        for lbl, x1, _ in self._label_slots(window):
            if lbl == label:
                return x1, float(h - CHROME_MENUBAR_HEIGHT)
        return 0.0, float(h - CHROME_MENUBAR_HEIGHT)

    def _item_at(self, x: float, y: float, window: object) -> MenuAction | None:
        if not self._open:
            return None
        ox, oy = self._drop_origin(window, self._open)
        if not (ox <= x <= ox + _DROP_W):
            return None
        actions = self._menu[self._open]
        for i, action in enumerate(actions):
            y_top = oy - PAD_SM - i * _ITEM_H
            y_bot = y_top - _ITEM_H
            if y_bot <= y <= y_top:
                return action
        return None
