"""
Phase 5 smoke test — verifies the Design View skeleton renders correctly.

Behaviors checked:
  1. Window opens (1400×900 ± tolerance)
  2. Left panel (tree) background ~ BG_1
  3. Centre panel (chat) background ~ BG_1
  4. No bright-red/white error regions visible
  5. App exits cleanly

Usage:
    python tools/smoke_test_phase5.py
"""
from __future__ import annotations

import sys

import dpi
from ui_harness import UITestHarness
from smoke_helpers import (
    WINDOW_W, WINDOW_H, CHROME_TOTAL_H,
    BG_1, COLOR_TOLERANCE,
    ok, fail, color_close, avg_color_region, check_no_error_dialog, os_titlebar_h,
)


def run() -> int:
    failures = 0
    print("\n=== Phase 5 Smoke Test ===\n")

    with UITestHarness(tag="phase5") as h:
        if h.window_rect is None:
            print("  FAIL  Window not found after startup timeout")
            return 1

        win_left, win_top, win_right, win_bottom = h.window_rect
        win_w = win_right - win_left
        win_h = win_bottom - win_top
        print(f"  Window at ({win_left},{win_top}), size {win_w}×{win_h}\n")

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
        # Behavior 1: window size
        # -------------------------------------------------------------------
        print("Behavior 1 — Window size 1400×900")
        if abs(win_w - WINDOW_W) <= 50 and abs(win_h - WINDOW_H) <= 80:
            ok(f"{win_w}×{win_h} ~ {WINDOW_W}×{WINDOW_H}")
        else:
            failures += fail(f"{win_w}×{win_h} does not match {WINDOW_W}×{WINDOW_H}")

        # -------------------------------------------------------------------
        # Behavior 2: left panel region ~ BG_1 (tree panel)
        # -------------------------------------------------------------------
        print("\nBehavior 2 — Left panel (tree) has dark panel background")
        left_avg = avg_color_region(
            pixels, shot_w, win_left, win_top + os_titlebar_h(),
            CHROME_TOTAL_H + 50, CHROME_TOTAL_H + 300,
            x_start=10, x_end=130,
        )
        if color_close(left_avg, BG_1, COLOR_TOLERANCE):
            ok(f"avg {tuple(round(c) for c in left_avg)} ~ BG_1 {BG_1}")
        else:
            failures += fail(f"avg {tuple(round(c) for c in left_avg)} far from BG_1 {BG_1}")

        # -------------------------------------------------------------------
        # Behavior 3: centre panel ~ BG_1 (chat panel)
        # -------------------------------------------------------------------
        print("\nBehavior 3 — Centre panel (chat) has dark panel background")
        centre_avg = avg_color_region(
            pixels, shot_w, win_left, win_top + os_titlebar_h(),
            CHROME_TOTAL_H + 50, CHROME_TOTAL_H + 300,
            x_start=350, x_end=800,
        )
        if color_close(centre_avg, BG_1, COLOR_TOLERANCE):
            ok(f"avg {tuple(round(c) for c in centre_avg)} ~ BG_1 {BG_1}")
        else:
            failures += fail(f"avg {tuple(round(c) for c in centre_avg)} far from BG_1 {BG_1}")

        # -------------------------------------------------------------------
        # Behavior 4: no bright error regions
        # -------------------------------------------------------------------
        print("\nBehavior 4 — No bright error dialog visible")
        failures += check_no_error_dialog(pixels, shot_w, *h.window_rect)

    # Behavior 5: clean exit — guaranteed by UITestHarness.__exit__
    print("\nBehavior 5 — App exits cleanly")
    ok("UITestHarness.__exit__ completed")

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"Screenshot: {shot_path}")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
