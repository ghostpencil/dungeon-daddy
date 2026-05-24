"""
Phase 10 smoke test — Design Mode Loop Editor.

Behaviors verified:
  1. Loops tab switches — ACTIVE LOOPS and PATTERN LIBRARY sections render
  2. Pattern click → main loop applied (TEAL card in ACTIVE LOOPS)
  3. + button on pattern card → sub-loop added (VIOLET card in ACTIVE LOOPS)
  4. × button → sub-loop removed (VIOLET card gone)
  5. Level picker chip click → active level changes without crash
  6. ChatBubble widget imports cleanly

Usage:
    cd tools && python smoke_test_phase10.py
"""
from __future__ import annotations

import sys
import time
import pathlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_PROJECT_ROOT = pathlib.Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ui_harness import UITestHarness
from ui_input import click_app
from smoke_helpers import (
    WINDOW_W, WINDOW_H, CHROME_TOTAL_H, PAD_MD, PAD_SM,
    ok, fail,
    pixel_rgb,
    menu_slot_center_x, menu_bar_center_y, dropdown_item_center_y,
)

# ---------------------------------------------------------------------------
# Inspector panel layout — derived from theme.py + inspector_panel.py
# ---------------------------------------------------------------------------

PANEL_INSPECTOR_W = 320
INSP_X = WINDOW_W - PANEL_INSPECTOR_W            # 1080
CONTENT_H = WINDOW_H - CHROME_TOTAL_H            # 830

_INSP_HEADER_H = 38
_INSP_TAB_H    = 32
_INSP_FOOTER_H = 44

# Tab bar (Arcade y)
_tab_y   = CONTENT_H - _INSP_HEADER_H - _INSP_TAB_H  # 760
_TAB_CY  = _tab_y + _INSP_TAB_H / 2                  # 776
_LOOPS_TAB_CX = INSP_X + PANEL_INSPECTOR_W * 3 // 4  # 1320  (right-half of inspector)

# LoopsPanel content area
_content_bot = _INSP_FOOTER_H                         # 44
_panel_h     = _tab_y - _content_bot                  # 716

# LoopsPanel draw starting y (top of content)
_SECTION_GAP = 12
_start_y = _content_bot + _panel_h - _SECTION_GAP     # 748

# Level picker chips row — cur_y after -= 18
_CHIP_Y  = int(_start_y - 18)                         # 730
_chip_w  = 26
_chip_gap = 4
_PAD_MD  = 12
# L2 chip center x = INSP_X + PAD_MD + chip_w + chip_gap + chip_w/2
_CHIP_L2_X = int(INSP_X + _PAD_MD + _chip_w + _chip_gap + _chip_w // 2)  # 1135

# Pattern card click x (horizontal center of inspector)
_PAT_CX = INSP_X + PANEL_INSPECTOR_W // 2             # 1240

# Pattern 1 y when no loops are assigned yet:
#   start=748, level_picker: -18=730, -4=726,
#   ACTIVE_LOOPS: -18=708, -4=704, no_loops: -20=684,
#   pat_lib_line: -12=672, label: -18=654, -4=650, card: -20=630
_PAT1_Y_EMPTY = 630

# Pattern 1 y after main loop is applied (path_a + path_b both drawn):
#   loop card: -22=682, path_a: -16=666, path_b: -14=652, gap: -8=644,
#   pat_lib_line: -12=632, label: -18=614, -4=610, card: -20=590
_PAT1_Y_WITH_MAIN = 590

# Sub-loop × button (right edge of inspector minus padding/half-btn)
_REMOVE_BTN_X = int(INSP_X + PANEL_INSPECTOR_W - _PAD_MD - 9)  # 1379
# Sub-loop card center y (after main with path_a + path_b, gap at 644):
#   sub card: 644 - 22 = 622
_REMOVE_BTN_Y = 622

# ---------------------------------------------------------------------------
# Pixel scan helpers
# ---------------------------------------------------------------------------

_SCAN_X0 = INSP_X + 10    # 1090
_SCAN_X1 = INSP_X + PANEL_INSPECTOR_W - 10  # 1390


def _has_teal(
    pixels: bytes, shot_w: int, win_left: int, win_top: int,
    y0: int, y1: int,
) -> bool:
    """Return True if a TEAL pixel is found in the inspector x-band, y0..y1 (Arcade y)."""
    for y_arc in range(y0, y1, 2):
        for x_arc in range(_SCAN_X0, _SCAN_X1, 3):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x_arc, y_arc)
            if g > 180 and b > 150 and r < 100:
                return True
    return False


def _has_violet(
    pixels: bytes, shot_w: int, win_left: int, win_top: int,
    y0: int, y1: int,
) -> bool:
    """Return True if a VIOLET pixel is found in the inspector x-band, y0..y1 (Arcade y)."""
    for y_arc in range(y0, y1, 2):
        for x_arc in range(_SCAN_X0, _SCAN_X1, 3):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x_arc, y_arc)
            if b > 190 and r > 130 and g < 130:
                return True
    return False


def _app_alive(h: UITestHarness) -> bool:
    return h._proc is not None and h._proc.poll() is None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    failures = 0
    print("\n=== Phase 10 Smoke Test ===\n")

    with UITestHarness(tag="phase10", render_wait=4.0) as h:
        if h.window_rect is None:
            print("  FAIL  Window did not open within timeout — aborting")
            return 1

        h.pin_window()
        win_left, win_top, _, _ = h.window_rect
        print(f"  Window pinned to (0,0)\n")

        # ------------------------------------------------------------------
        # Setup: load sample dungeon
        # ------------------------------------------------------------------
        print("Setup — File → Demo Dungeon to load sample dungeon")
        click_app(h.window_rect, menu_slot_center_x("File"), menu_bar_center_y())
        time.sleep(0.3)
        click_app(h.window_rect, menu_slot_center_x("File") + 40, dropdown_item_center_y(2))
        time.sleep(1.5)

        # ------------------------------------------------------------------
        # Behavior 1 — Loops tab switches cleanly
        # ------------------------------------------------------------------
        print("Behavior 1 — Loops tab click → ACTIVE LOOPS + PATTERN LIBRARY render")

        click_app(h.window_rect, _LOOPS_TAB_CX, _TAB_CY)
        time.sleep(0.6)

        shot = h.capture("loops_tab")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        # The active Loops tab border and level-picker chips are TEAL.
        # Scan the tab bar row and chip row (y=720..792) for TEAL.
        if _has_teal(pixels, shot_w, win_left, win_top, 720, 792):
            ok("TEAL found in Loops tab area — tab is active, panel rendered")
        else:
            failures += fail("No TEAL in Loops tab area — tab may not have switched")

        if _app_alive(h):
            ok("App alive after Loops tab switch")
        else:
            return failures + fail("App crashed after Loops tab switch — aborting")

        # ------------------------------------------------------------------
        # Behavior 2 — Pattern click → main loop applied
        # ------------------------------------------------------------------
        print("\nBehavior 2 — Click pattern card → main loop applied")

        click_app(h.window_rect, _PAT_CX, _PAT1_Y_EMPTY)
        time.sleep(0.4)

        shot = h.capture("pattern_click")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        # ACTIVE LOOPS section: loop card with TEAL border appears at y≈671..693
        # Scan y=665..726 (between level chips at 730 and the card area)
        if _has_teal(pixels, shot_w, win_left, win_top, 665, 726):
            ok("TEAL loop card found in ACTIVE LOOPS — main loop applied")
        else:
            failures += fail("No TEAL loop card in ACTIVE LOOPS after pattern click")

        # ------------------------------------------------------------------
        # Behavior 3 — + button on pattern card → sub-loop added
        # ------------------------------------------------------------------
        print("\nBehavior 3 — Click + button on pattern card → sub-loop added")

        # + button center x = same as × button x (both at far right of inspector)
        click_app(h.window_rect, _REMOVE_BTN_X, _PAT1_Y_WITH_MAIN)
        time.sleep(0.4)

        shot = h.capture("plus_button_click")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        # Sub-loop card appears at y≈622 with VIOLET border — scan 605..645
        if _has_violet(pixels, shot_w, win_left, win_top, 605, 645):
            ok("VIOLET sub-loop card found in ACTIVE LOOPS — + button worked")
        else:
            failures += fail("No VIOLET in ACTIVE LOOPS after + button click")

        # ------------------------------------------------------------------
        # Behavior 4 — × button → sub-loop removed
        # ------------------------------------------------------------------
        print("\nBehavior 4 — × click → sub-loop removed")

        click_app(h.window_rect, _REMOVE_BTN_X, _REMOVE_BTN_Y)
        time.sleep(0.4)

        shot = h.capture("subloop_removed")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        # Sub-loop card (y=605..645) should no longer have VIOLET
        if not _has_violet(pixels, shot_w, win_left, win_top, 605, 645):
            ok("No VIOLET in sub-loop region — sub-loop successfully removed")
        else:
            failures += fail("VIOLET still present in sub-loop region after × click")

        # ------------------------------------------------------------------
        # Behavior 5 — Level picker chip click → active level changes
        # ------------------------------------------------------------------
        print("\nBehavior 5 — Level picker: click L2 chip → no crash")

        click_app(h.window_rect, _CHIP_L2_X, _CHIP_Y)
        time.sleep(0.4)

        shot = h.capture("level_picker")
        print(f"  Screenshot: {shot.name}")

        if _app_alive(h):
            ok("App alive after level picker chip click")
        else:
            failures += fail("App crashed after level picker chip click")

        # ------------------------------------------------------------------
        # Behavior 6 — ChatBubble widget: import + instantiate
        # ------------------------------------------------------------------
        print("\nBehavior 6 — ChatBubble widget imports and instantiates cleanly")

    # Import check outside the harness (no arcade window needed for pure import)
    try:
        from dungeon_daddy.ui.widgets.chat_bubble import ChatBubble
        ChatBubble()
        ok("ChatBubble imported and instantiated without error")
    except Exception as exc:
        failures += fail(f"ChatBubble import/init failed: {exc}")

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
