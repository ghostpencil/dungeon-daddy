"""
Mouse and keyboard input helpers for Dungeon Daddy UI tests.

Coordinate system note:
  Arcade places y=0 at the bottom of the content area.
  Screen coordinates place y=0 at the top-left of the monitor.
  app_to_screen() converts between them.
"""
from __future__ import annotations

import time

import dpi
import platform_host as _ph

# Windows virtual key codes
VK_CONTROL = 0x11
VK_SHIFT   = 0x10
VK_RETURN  = 0x0D
VK_BACK    = 0x08
VK_O       = 0x4F
VK_N       = 0x4E

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP   = 0x0004

WM_KEYDOWN = 0x0100
WM_KEYUP   = 0x0101

_OS_TITLEBAR_H_BASE = 32   # logical pixels at 96 DPI
_WINDOW_H_BASE      = 900  # logical pixels (must match AppConfig default)


def _px(x: float) -> int:
    """Round to nearest pixel using conventional half-up rounding."""
    return int(x + 0.5)


def app_to_screen(
    window_rect: tuple[int, int, int, int],
    app_x: float,
    app_y: float,
) -> tuple[int, int]:
    """Convert Arcade app coordinates (y=0 at bottom of content) to absolute screen pixels.

    window_rect: (left, top, right, bottom) from GetWindowRect.
    """
    s = dpi.scale()
    win_left, win_top, _, _ = window_rect
    sx = win_left + _px(app_x * s)
    sy = win_top + _px(_OS_TITLEBAR_H_BASE * s) + _px((_WINDOW_H_BASE - app_y) * s)
    return sx, sy


def click(sx: int, sy: int, delay: float = 0.05) -> None:
    """Left-click at absolute screen coordinates."""
    _ph.get_platform().send_click(sx, sy, delay)


def click_app(
    window_rect: tuple[int, int, int, int],
    app_x: float,
    app_y: float,
    delay: float = 0.05,
) -> None:
    """Left-click at arcade app coordinates."""
    sx, sy = app_to_screen(window_rect, app_x, app_y)
    click(sx, sy, delay)


def key_combo(*vks: int) -> None:
    """
    Press a key combination (modifiers first, main key last).
    All keys are pressed simultaneously then released in reverse order.
    Example: key_combo(VK_CONTROL, VK_O)
    """
    _ph.get_platform().send_key_combo(*vks)


def shift_click_app(
    window_rect: tuple[int, int, int, int],
    app_x: float,
    app_y: float,
    window_title: str = "Dungeon Daddy",
) -> None:
    """
    Shift+left-click at arcade app coordinates.

    Strategy: PostMessageW(WM_KEYDOWN/WM_KEYUP) for the SHIFT modifier — this
    goes directly into pyglet's Win32 message queue so it updates pyglet's
    internal _modifiers bitmask.  The actual click uses mouse_event (hardware
    queue), which is the only mechanism confirmed to reach on_mouse_press.
    WM_LBUTTONDOWN via PostMessage is intentionally avoided — pyglet ignores it.
    """
    plat = _ph.get_platform()
    sx, sy = app_to_screen(window_rect, app_x, app_y)

    hwnd = plat.find_window(window_title)
    if not hwnd:
        return

    kdown_lp = 0x00000001  # repeat=1
    kup_lp   = 0xC0000001  # repeat=1, prev_down=1, transition=1

    plat.post_message(hwnd, WM_KEYDOWN, VK_SHIFT, kdown_lp)
    time.sleep(0.05)
    plat.set_cursor_pos(sx, sy)
    time.sleep(0.05)
    plat.mouse_event(MOUSEEVENTF_LEFTDOWN, sx, sy, 0, 0)
    time.sleep(0.05)
    plat.mouse_event(MOUSEEVENTF_LEFTUP, sx, sy, 0, 0)
    time.sleep(0.05)
    plat.post_message(hwnd, WM_KEYUP, VK_SHIFT, kup_lp)


def scroll_at(sx: int, sy: int, clicks: int = 3) -> None:
    """Scroll the mouse wheel at absolute screen coordinates.

    Positive clicks = scroll up; negative = scroll down.
    One click = WHEEL_DELTA (120) units, matching one Windows scroll notch.
    """
    _ph.get_platform().send_scroll(sx, sy, clicks)


def type_text(text: str, delay: float = 0.02) -> None:
    """Type a Unicode string via SendInput (KEYEVENTF_UNICODE).

    Works for all characters including non-ASCII.  The focused window receives
    the keystrokes — make sure the target input widget has keyboard focus first.
    """
    _ph.get_platform().send_text(text, delay)
