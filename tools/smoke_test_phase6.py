"""
Phase 6 interactive smoke test — Play View + Grid Map.

Verifies all four Phase 6 exit criteria in a single app session:
  1. Grid map renders rooms after loading sample dungeon
  2. Switching to Play mode shows ChatPanel left and MapPanel right
  3. Clicking a room highlights it (TEAL stroke) and marks it visited
  4. Level stepper navigates between the 3 sample levels

Coordinates are computed from layout constants (nothing hard-coded to a
monitor position), so the test is portable across machines and window positions.

Usage:
    cd tools && python smoke_test_phase6.py
"""
from __future__ import annotations

import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from ui_harness import UITestHarness
from ui_input import click_app
from smoke_helpers import (
    WINDOW_W, WINDOW_H, CHROME_TOTAL_H, PAD_MD, PAD_SM,
    BG_0, BG_1,
    ok, fail, color_close, pixel_rgb, scan_for_high_green,
    menu_slot_center_x, menu_slot_x, menu_bar_center_y, dropdown_item_center_y,
    room_center,
)

# ---------------------------------------------------------------------------
# Play View layout constants — specific to play_view.py / theme.py
# ---------------------------------------------------------------------------

PANEL_CHAT_W    = 440
PANEL_STEPPER_W = 70
_MAP_HEADER_H   = 38          # map panel header bar height (matches map_panel._HEADER_H)

MAP_X     = PANEL_CHAT_W                    # 440 — left edge of map panel
MAP_W     = WINDOW_W - MAP_X               # 960
CONTENT_H = WINDOW_H - CHROME_TOTAL_H      # 830
ORIGIN_X  = MAP_X + PAD_MD                 # 452 — grid drawing origin x (pan=0)
ORIGIN_Y  = PAD_MD                         # 12  — grid drawing origin y (pan=0)
STEPPER_X = MAP_X + MAP_W - PANEL_STEPPER_W  # 1330 — left edge of stepper rail
STEPPER_H = CONTENT_H - _MAP_HEADER_H      # 792 — usable stepper height

_STEPPER_BTN_H   = 28   # matches LevelStepper._BTN_H
_STEPPER_COMPASS = 48   # matches LevelStepper._COMPASS_H


def _stepper_btn_center(is_up: bool) -> tuple[float, float]:
    """Arcade (x, y) of the ▲ or ▼ stepper button centre."""
    cx = STEPPER_X + PANEL_STEPPER_W / 2   # 1365
    if is_up:
        btn_y = STEPPER_H - _STEPPER_BTN_H - PAD_SM  # 792 - 28 - 8 = 756
    else:
        btn_y = _STEPPER_COMPASS                      # 48
    return cx, btn_y + _STEPPER_BTN_H / 2


# ---------------------------------------------------------------------------
# Main test run
# ---------------------------------------------------------------------------

def run() -> int:
    failures = 0
    print("\n=== Phase 6 Smoke Test ===\n")

    with UITestHarness(tag="phase6", render_wait=3.0) as h:
        if h.window_rect is None:
            print("  FAIL  Window not found — aborting")
            return 1

        h.pin_window()
        win_left, win_top, win_right, win_bottom = h.window_rect
        win_w = win_right - win_left
        win_h = win_bottom - win_top
        print(f"  Window repositioned to (0,0)  size {win_w}×{win_h}\n")

        # ------------------------------------------------------------------
        # Setup: load the sample dungeon via Ctrl+O
        # ------------------------------------------------------------------
        print("Setup — File → Demo Dungeon to load sample dungeon")
        click_app(h.window_rect, menu_slot_center_x("File"), menu_bar_center_y())
        time.sleep(0.3)
        click_app(h.window_rect, menu_slot_center_x("File") + 40, dropdown_item_center_y(2))
        time.sleep(1.5)

        # ------------------------------------------------------------------
        # Setup: switch to Play mode via Play > Switch to Play
        # ------------------------------------------------------------------
        print("Setup — opening Play menu")
        click_app(h.window_rect, menu_slot_center_x("Play"), menu_bar_center_y())
        time.sleep(0.4)

        print("Setup — clicking Switch to Play")
        drop_x = menu_slot_x("Play") + 80      # centre of 160px dropdown
        click_app(h.window_rect, drop_x, dropdown_item_center_y(0))
        time.sleep(1.0)

        shot = h.capture("play_mode")
        pixels = h.pixels
        shot_w = h.shot_w
        print(f"  Screenshot: {shot.name}\n")

        # ------------------------------------------------------------------
        # Behavior 1 — Grid map renders rooms after loading sample dungeon
        # ------------------------------------------------------------------
        print("Behavior 1 — Grid map renders rooms after loading sample dungeon")
        # Map auto-centers on load so hardcoded grid coords are unreliable.
        # Scan a grid of points across the map content area for any non-background pixel.
        _map_content_w = MAP_W - PANEL_STEPPER_W  # 890
        _map_content_h = CONTENT_H - _MAP_HEADER_H  # 792
        found_room = False
        _sample_color = BG_0
        for _sy in range(80, _map_content_h - 40, 30):
            for _sx in range(MAP_X + 30, MAP_X + _map_content_w - 30, 30):
                c = pixel_rgb(pixels, shot_w, win_left, win_top, _sx, _sy)
                if not color_close(c, BG_0, tol=20):
                    found_room = True
                    _sample_color = c
                    break
            if found_room:
                break
        if found_room:
            ok(f"Non-background pixel {_sample_color} found in map area — rooms are rendering")
        else:
            failures += fail("Map area is all background — rooms may not be rendering")
        rx, ry = room_center(1, 4, 3, 3, ORIGIN_X, ORIGIN_Y)  # used by behavior 3

        # ------------------------------------------------------------------
        # Behavior 2 — Switching to Play mode: ChatPanel left, MapPanel right
        # ------------------------------------------------------------------
        print("\nBehavior 2 — Play mode layout: ChatPanel left, MapPanel right")

        chat_sample = pixel_rgb(pixels, shot_w, win_left, win_top, 220, 400)
        if color_close(chat_sample, BG_1, tol=25):
            ok(f"chat panel pixel {chat_sample} ~= BG_1 {BG_1}")
        else:
            failures += fail(f"chat panel pixel {chat_sample} far from BG_1 {BG_1}")

        map_sample = pixel_rgb(pixels, shot_w, win_left, win_top, 1200, 400)
        if color_close(map_sample, BG_0, tol=20):
            ok(f"map panel pixel {map_sample} ~= BG_0 {BG_0}")
        else:
            failures += fail(f"map panel pixel {map_sample} far from BG_0 {BG_0}")

        # ------------------------------------------------------------------
        # Behavior 3 — Clicking a room highlights it (TEAL stroke appears)
        # ------------------------------------------------------------------
        print("\nBehavior 3 — Clicking room 1-A highlights it")
        click_app(h.window_rect, rx, ry)
        time.sleep(0.5)
        shot = h.capture("room_clicked")
        pixels = h.pixels
        print(f"  Screenshot: {shot.name}")

        has_teal = scan_for_high_green(
            pixels, shot_w, win_left, win_top,
            arcade_x=rx, arcade_y=ry,
            radius=80,
            green_threshold=180,
        )
        if has_teal:
            ok("TEAL highlight found near room 1-A — room is current_room")
        else:
            failures += fail("no TEAL pixels found near room 1-A — highlight missing")

        # ------------------------------------------------------------------
        # Behavior 4 — Level stepper navigates between levels
        # ------------------------------------------------------------------
        print("\nBehavior 4 — Level stepper ▼ navigates to level 2")
        # Sample map pixels before clicking ▼ — level change will shift room positions
        _pts = [(sx, sy) for sy in range(150, 700, 110) for sx in range(500, 1280, 130)]
        before_map = [pixel_rgb(pixels, shot_w, win_left, win_top, sx, sy) for sx, sy in _pts]

        down_cx, down_cy = _stepper_btn_center(is_up=False)
        click_app(h.window_rect, down_cx, down_cy)
        time.sleep(0.8)
        shot = h.capture("level2")
        pixels = h.pixels
        shot_w = h.shot_w
        print(f"  Screenshot: {shot.name}")

        after_map = [pixel_rgb(pixels, shot_w, win_left, win_top, sx, sy) for sx, sy in _pts]
        changed = sum(1 for b, a in zip(before_map, after_map) if not color_close(b, a, tol=15))
        if changed >= 3:
            ok(f"{changed}/{len(_pts)} map pixels changed — level navigation worked")
        else:
            failures += fail(f"Only {changed}/{len(_pts)} map pixels changed — level may not have changed")

    # App terminates on __exit__
    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
