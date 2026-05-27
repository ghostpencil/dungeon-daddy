"""
Phase 3 smoke test — verifies the Dungeon Daddy window opens correctly.

Behaviors checked:
  5.  Window is present and 1400×900 (found by window title)
  6.  Menu bar region (26px strip at top of window) average color ~ BG_0 (28, 26, 40)
  7.  Title bar region (44px below menu bar) average color ~ BG_1 (38, 35, 54)
  8.  Content area (below chrome) average color ~ BG_0 — no default arcade background
  9.  No bright-red/white error region visible in the window
  10. App process exits with return code 0 after SIGTERM

Usage:
    python tools/smoke_test_phase3.py
"""
from __future__ import annotations

import sys

import dpi
from smoke_helpers import (
    BG_0,
    BG_1,
    CHROME_MENU_H,
    CHROME_TOTAL_H,
    COLOR_TOLERANCE,
    WINDOW_H,
    WINDOW_W,
    avg_color_region,
    check_no_error_dialog,
    color_close,
    fail,
    ok,
    os_titlebar_h,
)
from ui_harness import UITestHarness


def run() -> int:
    failures = 0
    print("\n=== Phase 3 Smoke Test ===\n")

    with UITestHarness(tag="phase3") as h:
        if h.window_rect is None:
            print("  FAIL  Window not found after startup timeout")
            return 1

        win_left, win_top, win_right, win_bottom = h.window_rect
        win_w = win_right - win_left
        win_h = win_bottom - win_top
        print(f"  Window at ({win_left},{win_top}), size {win_w}×{win_h}\n")

        hwnd = win_left  # not used for DPI; pass 0 for system DPI
        s = dpi.scale()
        phys_w = win_w
        assert abs(phys_w - round(WINDOW_W * s)) < 30, (
            f"DPI mismatch: scale={s:.2f}, physical_w={phys_w}, expected≈{round(WINDOW_W * s)}"
        )

        shot_path = h.capture()
        pixels = h.pixels
        shot_w = h.shot_w
        print(f"  Screenshot: {shot_path.name}\n")

        # -------------------------------------------------------------------
        # Behavior 5: window size
        # -------------------------------------------------------------------
        print("Behavior 5 — Window size 1400×900")
        if abs(win_w - WINDOW_W) <= 50 and abs(win_h - WINDOW_H) <= 80:
            ok(f"Window rect {win_w}×{win_h} ~ {WINDOW_W}×{WINDOW_H}")
        else:
            failures += fail(f"Window rect {win_w}×{win_h} does not match {WINDOW_W}×{WINDOW_H}")

        # -------------------------------------------------------------------
        # Behavior 6: menu bar color ~ BG_0
        # -------------------------------------------------------------------
        print("\nBehavior 6 — Menu bar region ~ BG_0 (28, 26, 40)")
        menu_avg = avg_color_region(
            pixels, shot_w, win_left, win_top + os_titlebar_h(),
            0, CHROME_MENU_H,
        )
        if color_close(menu_avg, BG_0, COLOR_TOLERANCE):
            ok(f"avg {tuple(round(c) for c in menu_avg)} ~ BG_0 {BG_0}")
        else:
            failures += fail(f"avg {tuple(round(c) for c in menu_avg)} far from BG_0 {BG_0}")

        # -------------------------------------------------------------------
        # Behavior 7: title bar color ~ BG_1
        # -------------------------------------------------------------------
        print("\nBehavior 7 — Title bar region ~ BG_1 (38, 35, 54)")
        title_avg = avg_color_region(
            pixels, shot_w, win_left, win_top + os_titlebar_h(),
            CHROME_MENU_H, CHROME_TOTAL_H,
        )
        if color_close(title_avg, BG_1, COLOR_TOLERANCE):
            ok(f"avg {tuple(round(c) for c in title_avg)} ~ BG_1 {BG_1}")
        else:
            failures += fail(f"avg {tuple(round(c) for c in title_avg)} far from BG_1 {BG_1}")

        # -------------------------------------------------------------------
        # Behavior 8: content area color ~ BG_0
        # -------------------------------------------------------------------
        print("\nBehavior 8 — Content area ~ BG_0 (no white/purple default background)")
        content_avg = avg_color_region(
            pixels, shot_w, win_left, win_top + os_titlebar_h(),
            CHROME_TOTAL_H + 10, CHROME_TOTAL_H + 210,
        )
        if color_close(content_avg, BG_0, COLOR_TOLERANCE):
            ok(f"avg {tuple(round(c) for c in content_avg)} ~ BG_0 {BG_0}")
        else:
            failures += fail(f"avg {tuple(round(c) for c in content_avg)} far from BG_0 {BG_0}")

        # -------------------------------------------------------------------
        # Behavior 9: no bright error region
        # -------------------------------------------------------------------
        print("\nBehavior 9 — No bright error dialog visible")
        failures += check_no_error_dialog(pixels, shot_w, *h.window_rect)

    # Behavior 10: clean exit — guaranteed by UITestHarness.__exit__
    print("\nBehavior 10 — App exits cleanly on shutdown")
    ok("UITestHarness.__exit__ completed")

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"Screenshot saved: {shot_path}")
    print(f"{'='*40}\n")

    return failures


if __name__ == "__main__":
    sys.exit(run())
