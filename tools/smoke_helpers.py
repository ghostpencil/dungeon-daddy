"""
Shared helpers and constants for Dungeon Daddy smoke tests.

Import in any smoke test to avoid re-implementing color checks, pixel math,
and app-layout coordinate helpers.
"""
from __future__ import annotations

from dpi import scale as _s

# ---------------------------------------------------------------------------
# Window / layout constants — match dungeon_daddy/ui/theme.py and AppConfig
# ---------------------------------------------------------------------------

WINDOW_W: int = 1400
WINDOW_H: int = 900
CHROME_MENU_H: int = 26
CHROME_TITLE_H: int = 44
CHROME_TOTAL_H: int = CHROME_MENU_H + CHROME_TITLE_H  # 70
PAD_MD: int = 12
PAD_SM: int = 8
CELL_PX: int = 48              # map grid cell size in pixels

_OS_TITLEBAR_H_BASE = 32   # logical pixels at 96 DPI
_CHAR_W_BASE        = 7    # logical pixels at 96 DPI


def os_titlebar_h() -> int:
    """OS title bar height in physical pixels at the current DPI."""
    return int(_OS_TITLEBAR_H_BASE * _s() + 0.5)


_os_titlebar_h = os_titlebar_h  # internal alias used by pixel helpers


def _char_w() -> float:
    return _CHAR_W_BASE * _s()


def _px(x: float) -> int:
    return int(x + 0.5)

# Design-system colors
BG_0: tuple[int, int, int] = (28, 26, 40)
BG_1: tuple[int, int, int] = (38, 35, 54)
TEAL: tuple[int, int, int] = (60, 210, 195)
COLOR_TOLERANCE: int = 40

# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def fail(msg: str) -> int:
    """Print a failure message and return 1 for use in ``failures += fail(...)``."""
    print(f"  FAIL  {msg}")
    return 1


# ---------------------------------------------------------------------------
# Pixel helpers  (full-screen capture, Arcade coordinates)
# ---------------------------------------------------------------------------

def color_close(
    actual: tuple[int, int, int],
    expected: tuple[int, int, int],
    tol: int = COLOR_TOLERANCE,
) -> bool:
    return all(abs(a - e) <= tol for a, e in zip(actual, expected))


def avg_color_region(
    pixels: bytes,
    shot_w: int,
    win_left: int,
    win_top: int,
    y_start: int,
    y_end: int,
    x_start: int = 0,
    x_end: int | None = None,
) -> tuple[float, float, float]:
    """Average RGB of a region inside a full-screen pixel buffer.

    Pass ``win_top + OS_TITLEBAR_H`` when you want y_start=0 to mean the
    top of the app content area (below the OS caption bar).
    Region y/x coordinates are relative to (win_left, win_top).
    """
    if x_end is None:
        x_end = WINDOW_W
    r_sum = g_sum = b_sum = count = 0
    for row in range(y_start, y_end):
        abs_row = win_top + row
        for col in range(x_start, x_end):
            offset = (abs_row * shot_w + win_left + col) * 4
            b_sum += pixels[offset]
            g_sum += pixels[offset + 1]
            r_sum += pixels[offset + 2]
            count += 1
    if count == 0:
        return 0.0, 0.0, 0.0
    return r_sum / count, g_sum / count, b_sum / count


def pixel_rgb(
    pixels: bytes,
    shot_w: int,
    win_left: int,
    win_top: int,
    arcade_x: float,
    arcade_y: float,
) -> tuple[int, int, int]:
    """Return (R, G, B) at an Arcade app coordinate (y=0 at bottom of content area)."""
    s = _s()
    sx = win_left + _px(arcade_x * s)
    sy = win_top + _os_titlebar_h() + _px((WINDOW_H - arcade_y) * s)
    offset = (sy * shot_w + sx) * 4
    return pixels[offset + 2], pixels[offset + 1], pixels[offset]


def scan_for_high_green(
    pixels: bytes,
    shot_w: int,
    win_left: int,
    win_top: int,
    arcade_x: float,
    arcade_y: float,
    radius: int,
    green_threshold: int = 180,
) -> bool:
    """Return True if any pixel within radius of (arcade_x, arcade_y) has G > green_threshold."""
    s = _s()
    cx = win_left + _px(arcade_x * s)
    cy = win_top + _os_titlebar_h() + _px((WINDOW_H - arcade_y) * s)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            offset = ((cy + dy) * shot_w + (cx + dx)) * 4
            if pixels[offset + 1] > green_threshold:
                return True
    return False


def check_no_error_dialog(
    pixels: bytes,
    shot_w: int,
    win_left: int,
    win_top: int,
    win_right: int,
    win_bottom: int,
    border: int = 12,
    block: int = 30,
) -> int:
    """Scan the app window for bright-white or bright-red error regions.

    Prints a pass or fail message.  Returns 1 on failure, 0 on pass — use as
    ``failures += check_no_error_dialog(pixels, shot_w, *h.window_rect)``.
    """
    stride = shot_w * 4
    y_start = win_top + _os_titlebar_h() + border
    y_limit = win_bottom - border
    x_start = win_left + border
    x_limit = win_right - border
    for row in range(y_start, y_limit - block, block):
        for col in range(x_start, x_limit - block, block):
            r_s = g_s = b_s = 0
            for dr in range(block):
                for dc in range(block):
                    offset = (row + dr) * stride + (col + dc) * 4
                    b_s += pixels[offset]
                    g_s += pixels[offset + 1]
                    r_s += pixels[offset + 2]
            n = block * block
            r_a, g_a, b_a = r_s / n, g_s / n, b_s / n
            if (r_a > 200 and g_a > 200 and b_a > 200) or (r_a > 180 and g_a < 60 and b_a < 60):
                return fail(
                    f"Bright {block}×{block} block at ({col},{row}): "
                    f"RGB=({round(r_a)},{round(g_a)},{round(b_a)})"
                )
    ok("No error dialog regions detected")
    return 0


# ---------------------------------------------------------------------------
# App menu coordinate helpers  (Arcade coordinate system)
# ---------------------------------------------------------------------------

_MENU_LABELS = ["File", "Edit", "Dungeon", "Play", "View", "Window", "Help"]


def menu_slot_x(label: str) -> float:
    """Arcade x of the left edge of a top-menu label's clickable slot.

    Approximate — depends on font metrics. Prefer MCP left_click with pinned window
    for DPI-stable click targets.
    """
    cw = _char_w()
    x = float(PAD_MD)
    for lbl in _MENU_LABELS:
        slot_w = len(lbl) * cw + PAD_MD * 2
        if lbl == label:
            return x
        x += slot_w
    raise ValueError(f"Unknown menu label: {label!r}")


def menu_slot_center_x(label: str) -> float:
    """Arcade x of the centre of a top-menu label's clickable slot.

    Approximate — depends on font metrics. Prefer MCP left_click with pinned window
    for DPI-stable click targets.
    """
    x = menu_slot_x(label)
    slot_w = len(label) * _char_w() + PAD_MD * 2
    return x + slot_w / 2


def menu_bar_center_y() -> float:
    """Arcade y of the centre of the menu bar strip."""
    return WINDOW_H - CHROME_MENU_H / 2


def dropdown_item_center_y(item_index: int) -> float:
    """Arcade y of a dropdown menu item's centre (0-based index, top to bottom)."""
    drop_top_y = WINDOW_H - CHROME_MENU_H
    item_h = 22
    return drop_top_y - PAD_SM - item_index * item_h - item_h / 2


# ---------------------------------------------------------------------------
# Grid map coordinate helper
# ---------------------------------------------------------------------------

def room_center(
    room_x: int,
    room_y: int,
    room_w: int,
    room_h: int,
    origin_x: float,
    origin_y: float,
) -> tuple[float, float]:
    """Arcade (x, y) of a grid room's centre pixel."""
    cx = origin_x + (room_x + room_w / 2) * CELL_PX
    cy = origin_y + (room_y + room_h / 2) * CELL_PX
    return cx, cy
