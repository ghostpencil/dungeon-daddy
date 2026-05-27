"""
Reusable UI test harness for Dungeon Daddy.

Usage:
    with UITestHarness(tag="phase6") as h:
        path = h.capture("after_load")   # → tools/screenshots/phase6_after_load_YYYYMMDD_HHMMSS.png
        # h.window_rect  — (left, top, right, bottom)
        # h.pixels       — raw BGRA bytes from last capture
        # h.shot_w       — full-screen pixel width (stride = shot_w * 4)
    # app is terminated on __exit__, even if the body raises

The harness automatically centers the window on the primary monitor after launch
so all UI elements are fully visible before any test action is taken.
Call pin_window() afterward to move it to a specific position if needed.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import mss
import platform_host as _ph
from mss.tools import to_png

WINDOW_TITLE = "Dungeon Daddy"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
_PROJECT_ROOT = Path(__file__).parent.parent

SWP_NOSIZE   = 0x0001
SWP_NOZORDER = 0x0004
WM_CLOSE     = 0x0010


class UITestHarness:
    def __init__(self, tag: str, startup_timeout: float = 8.0, render_wait: float = 4.0) -> None:
        self.tag = tag
        self.startup_timeout = startup_timeout
        self.render_wait = render_wait
        self.window_rect: tuple[int, int, int, int] | None = None
        self._monitor: dict | None = None
        self.pixels: bytes | None = None
        self.shot_w: int | None = None
        self._proc: subprocess.Popen | None = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> UITestHarness:
        _ph.get_platform().set_dpi_awareness()
        SCREENSHOTS_DIR.mkdir(exist_ok=True)
        self._proc = subprocess.Popen(
            [sys.executable, "-m", "dungeon_daddy"],
            cwd=str(_PROJECT_ROOT),
        )
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            rect = self._find_window_rect()
            if rect:
                self.window_rect = rect
                break
            time.sleep(0.25)
        if self.window_rect is not None:
            self.center_window()
            time.sleep(self.render_wait)
        return self

    def __exit__(self, *_args: object) -> None:
        self._shutdown()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def center_window(self) -> None:
        """Move the app window to the center of the primary monitor and refresh window_rect.

        Called automatically by __enter__ so all elements are fully visible before
        the first action is taken.  computer-use-mcp coordinates must be recalculated
        after this call — use self.window_rect for the updated position.
        """
        plat = _ph.get_platform()
        hwnd = plat.find_window(WINDOW_TITLE)
        if not hwnd:
            return
        rect = self._find_window_rect()
        if rect is None:
            return
        left, top, right, bottom = rect
        win_w = right - left
        win_h = bottom - top
        screen_w = plat.get_system_metrics(0)
        screen_h = plat.get_system_metrics(1)
        x = max(0, (screen_w - win_w) // 2)
        y = max(0, (screen_h - win_h) // 2)
        plat.set_window_pos(hwnd, x, y, SWP_NOSIZE | SWP_NOZORDER)
        time.sleep(0.15)
        self.refresh_window_rect()

    def pin_window(self, x: int = 0, y: int = 0) -> None:
        """Move the app window to absolute screen position (x, y) and refresh window_rect.

        Call this before using computer-use-mcp coordinates so the window is at a
        known position.  MCP uses absolute screen coords (x from left, y from top).
        """
        plat = _ph.get_platform()
        hwnd = plat.find_window(WINDOW_TITLE)
        if hwnd:
            plat.set_window_pos(hwnd, x, y, SWP_NOSIZE | SWP_NOZORDER)
            time.sleep(0.15)
        self.refresh_window_rect()

    def refresh_window_rect(self) -> None:
        """Re-query Win32 for the current window position and update self.window_rect."""
        rect = self._find_window_rect()
        if rect:
            self.window_rect = rect
            with mss.MSS() as sct:
                self._monitor = _monitor_for_rect(rect, sct)

    def capture(self, label: str = "") -> Path:
        """Grab the primary monitor, save PNG, update self.pixels / self.shot_w."""
        ts = time.strftime("%Y%m%d_%H%M%S")
        parts = [self.tag]
        if label:
            parts.append(label)
        parts.append(ts)
        filename = SCREENSHOTS_DIR / f"{'_'.join(parts)}.png"

        with mss.MSS() as sct:
            monitor = self._monitor if self._monitor is not None else sct.monitors[1]
            raw = sct.grab(monitor)
            to_png(raw.rgb, raw.size, output=str(filename))
            self.pixels = bytes(raw.raw)
            self.shot_w = raw.width

        return filename

    def capture_window(self, label: str = "") -> Path:
        """Grab only the app window region, save PNG, update self.pixels / self.shot_w.

        Produces a smaller, cleaner screenshot than capture() — no desktop or taskbar
        visible.  Pixels are window-relative (origin at top-left of the window).
        Falls back to full-screen capture if window_rect is not set.
        """
        if self.window_rect is None:
            return self.capture(label)

        self.refresh_window_rect()
        left, top, right, bottom = self.window_rect  # type: ignore[misc]

        ts = time.strftime("%Y%m%d_%H%M%S")
        parts = [self.tag, "win"]
        if label:
            parts.append(label)
        parts.append(ts)
        filename = SCREENSHOTS_DIR / f"{'_'.join(parts)}.png"

        region = {"left": left, "top": top, "width": right - left, "height": bottom - top}
        with mss.MSS() as sct:
            raw = sct.grab(region)
            to_png(raw.rgb, raw.size, output=str(filename))
            self.pixels = bytes(raw.raw)
            self.shot_w = raw.width

        return filename

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_window_rect(self) -> tuple[int, int, int, int] | None:
        plat = _ph.get_platform()
        hwnd = plat.find_window(WINDOW_TITLE)
        if not hwnd:
            return None
        return plat.get_window_rect(hwnd)

    def _shutdown(self) -> None:
        if self._proc is None:
            return
        plat = _ph.get_platform()
        hwnd = plat.find_window(WINDOW_TITLE)
        if hwnd:
            plat.post_message(hwnd, WM_CLOSE, 0, 0)
        try:
            self._proc.wait(timeout=6)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait()
        self._proc = None


def _monitor_for_rect(
    rect: tuple[int, int, int, int], sct: object
) -> dict:
    """Return the monitor from sct.monitors[1:] with greatest overlap with rect."""
    import warnings

    win_left, win_top, win_right, win_bottom = rect
    best_mon = sct.monitors[1]
    best_area = 0

    for mon in sct.monitors[1:]:
        mon_right  = mon["left"] + mon["width"]
        mon_bottom = mon["top"]  + mon["height"]
        ox = max(0, min(win_right, mon_right)  - max(win_left, mon["left"]))
        oy = max(0, min(win_bottom, mon_bottom) - max(win_top,  mon["top"]))
        area = ox * oy
        if area > best_area:
            best_area = area
            best_mon  = mon

    if best_area == 0:
        warnings.warn(
            "Window has no overlap with any monitor; falling back to monitors[1]",
            UserWarning,
            stacklevel=2,
        )

    return best_mon
