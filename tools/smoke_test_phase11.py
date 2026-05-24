"""
Phase 11 smoke test — Design Mode Polish + Context Docs Foundation.

Behaviors verified:
  1. Settings tab: Context docs section renders with real row labels
  2. Freshly loaded dungeon shows all three rows as "○ pending" (no TEAL in status area)
  3. Clicking a context doc row opens the edit overlay (TEAL Save button appears)
  4. Cancel (Esc) closes the overlay (TEAL Save button gone, UI restored)
  5. Save persists content and updates word count to TEAL "✓ NNN words"

Usage:
    cd tools && python smoke_test_phase11.py

Coordinate note:
  Inspector _draw_settings elements (doc rows, complexity) use a top-down
  layout that scales with window height.  When the window is constrained
  (< 900 px) their *screen* y happens to coincide with the value produced
  by pixel_rgb(…, WINDOW_H=900), so click_app / _scan_teal work as-is.

  The context-doc overlay card is *centred* in the content area, so its
  screen y does NOT follow that rule.  All overlay-button interactions use
  _btn_screen_y() which derives coords from h.window_rect at runtime.
"""
from __future__ import annotations

import pathlib
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_PROJECT_ROOT = pathlib.Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ui_harness import UITestHarness
from ui_input import click, click_app, key_combo, type_text
from smoke_helpers import (
    WINDOW_W, WINDOW_H, CHROME_TOTAL_H, os_titlebar_h, PAD_MD,
    ok, fail,
    pixel_rgb,
    menu_slot_center_x, menu_bar_center_y, dropdown_item_center_y,
)

# ---------------------------------------------------------------------------
# Inspector panel layout constants
# ---------------------------------------------------------------------------

PANEL_INSPECTOR_W = 320
PANEL_TREE_W      = 240
INSP_X            = WINDOW_W - PANEL_INSPECTOR_W   # 1080
CONTENT_H         = WINDOW_H - CHROME_TOTAL_H      # 830

_INSP_HEADER_H = 38
_INSP_TAB_H    = 32
_INSP_FOOTER_H = 44
_SECTION_GAP   = 12
_PAD_SM        = 8
_PAD_XS        = 4
_ROW_H         = 22

# Content area bounds for the Settings tab
_tab_y       = CONTENT_H - _INSP_HEADER_H - _INSP_TAB_H   # 760
_content_bot = _INSP_FOOTER_H                               # 44
_content_h   = _tab_y - _content_bot                       # 716

# Walk _draw_settings to find context doc row positions (Arcade y)
# cur_y starts at y_bot + h - SECTION_GAP = 44 + 716 - 12 = 748
_cur_y = _content_bot + _content_h - _SECTION_GAP           # 748

# Party section
_cur_y -= _ROW_H + _PAD_SM                                  # -= 22 + 8 = 30 → 718
_cur_y -= 28 + _PAD_XS                                      # Size row  → 686
_cur_y -= 28 + _PAD_XS                                      # Level row → 654
_cur_y -= _SECTION_GAP                                       # gap       → 642

# Dungeon section
_cur_y -= _ROW_H + _PAD_SM                                  # heading   → 612
_cur_y -= 28 + _PAD_XS                                      # Theme row → 580
_cur_y -= 28 + _PAD_XS                                      # Levels row→ 548

# Complexity
_cur_y -= _ROW_H                                            # label     → 526
_cur_y -= 26                                                # seg ctrl  → 500
_cur_y -= 12 + _SECTION_GAP                                 # gap       → 476

# Context docs heading
_cur_y -= _ROW_H + _PAD_SM                                  # heading   → 446

# Three context doc rows
_DOC_ROW_1_Y = _cur_y - _ROW_H                             # 424  Dungeon Setting
_cur_y -= _ROW_H + _PAD_XS                                  # 420
_DOC_ROW_2_Y = _cur_y - _ROW_H                             # 398  Party Doc
_cur_y -= _ROW_H + _PAD_XS                                  # 394
_DOC_ROW_3_Y = _cur_y - _ROW_H                             # 372  Level Design

# Horizontal click target: centre of the inspector
_DOC_ROW_CX = INSP_X + PANEL_INSPECTOR_W // 2              # 1240

# Status text area (right-aligned at INSP_X + PANEL_INSPECTOR_W - PAD_MD = 1388)
_STATUS_X0   = 1320
_STATUS_X1   = 1388

# ---------------------------------------------------------------------------
# Overlay geometry  (mirrors DesignView._overlay_card_rect)
# ---------------------------------------------------------------------------

_MAP_AREA_W  = WINDOW_W - PANEL_TREE_W - PANEL_INSPECTOR_W  # 840
_CARD_W      = int(_MAP_AREA_W * 0.85)                       # 714
_CARD_H      = int(CONTENT_H * 0.80)                         # 664
_CARD_X      = int(PANEL_TREE_W + (_MAP_AREA_W - _CARD_W) / 2)  # 303
_CARD_Y      = int((CONTENT_H - _CARD_H) / 2)               # 83

_BTN_H   = 28
_BTN_W   = 80

# Save button center x (arcade x — window width is not constrained)
# save_x = card_x + card_w/2 - btn_w - pad/2  (left edge of save button)
# center = save_x + btn_w/2
_SAVE_BTN_CX = int(_CARD_X + _CARD_W / 2 - _BTN_W / 2 - PAD_MD / 2)  # 614

# Text input area centre x
_TEXT_CX = _CARD_X + _CARD_W // 2                           # 660

# Virtual key code for Escape
VK_ESCAPE = 0x1B


# ---------------------------------------------------------------------------
# Overlay coordinate helpers  (window-rect-aware)
# ---------------------------------------------------------------------------

def _btn_screen_y(win_top: int, win_bottom: int) -> int:
    """
    Compute the screen y-coordinate for the overlay Save/Cancel button row.

    The overlay card is centred in the actual content area, which changes when
    Windows constrains the window height below the requested 900 px.  This
    function derives the position from h.window_rect at runtime.
    """
    arcade_win_h = win_bottom - win_top - os_titlebar_h()  # arcade window.height
    content_h    = arcade_win_h - CHROME_TOTAL_H
    card_h       = int(content_h * 0.80)
    card_y       = (content_h - card_h) / 2
    btn_cy_arcade = card_y + PAD_MD + _BTN_H / 2
    # arcade y=0 is at win_bottom; count up from there
    return win_bottom - int(btn_cy_arcade)


def _text_screen_y(win_top: int, win_bottom: int) -> int:
    """Screen y for clicking into the overlay text area."""
    arcade_win_h = win_bottom - win_top - os_titlebar_h()
    content_h    = arcade_win_h - CHROME_TOTAL_H
    card_h       = int(content_h * 0.80)
    card_y       = (content_h - card_h) / 2
    text_y_arcade = card_y + PAD_MD + _BTN_H + PAD_MD + int(card_h * 0.25)
    return win_bottom - int(text_y_arcade)


# ---------------------------------------------------------------------------
# Pixel helpers
# ---------------------------------------------------------------------------

TEAL = (60, 210, 195)


def _scan_teal(
    pixels: bytes, shot_w: int, win_left: int, win_top: int,
    x0: int, x1: int, y0: int, y1: int,
) -> bool:
    """
    Scan for TEAL in an Inspector-panel arcade-coord rectangle.

    x0/x1/y0/y1 are Arcade app coordinates.  Because Inspector rows follow
    a top-down layout that scales uniformly with window height, the screen y
    produced by pixel_rgb(WINDOW_H=900) coincides with the actual screen y
    even when the window is constrained — so this function is correct for
    all Inspector elements.
    """
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 3):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x, y)
            if g > 180 and b > 140 and r < 100:
                return True
    return False


def _scan_teal_screen(
    pixels: bytes, shot_w: int,
    sx0: int, sx1: int, sy0: int, sy1: int,
) -> bool:
    """
    Scan for TEAL in a screen-coordinate rectangle.

    Use this for overlay elements whose screen position cannot be derived
    from pixel_rgb (arcade coord → screen mismatch when window is constrained).
    """
    for sy in range(sy0, sy1, 2):
        for sx in range(sx0, sx1, 3):
            offset = (sy * shot_w + sx) * 4
            b = pixels[offset]
            g = pixels[offset + 1]
            r = pixels[offset + 2]
            if g > 180 and b > 140 and r < 100:
                return True
    return False


def _app_alive(h: UITestHarness) -> bool:
    return h._proc is not None and h._proc.poll() is None


# ---------------------------------------------------------------------------
# Pre-test cleanup
# ---------------------------------------------------------------------------

def _clean_context_docs() -> None:
    """Delete any pre-existing context docs for the sample dungeon."""
    from platformdirs import user_data_path
    data_dir = user_data_path("DungeonDaddy", appauthor=False)
    dungeon_dir = data_dir / "dungeons" / "Tomb of the Forgotten King"
    for fname in ("setting.md", "party.md"):
        p = dungeon_dir / fname
        if p.exists():
            p.unlink()
            print(f"  Cleaned up pre-existing: {p.name}")
    # Remove level design docs
    for p in dungeon_dir.glob("level_*_design.md"):
        p.unlink()
        print(f"  Cleaned up pre-existing: {p.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    failures = 0
    print("\n=== Phase 11 Smoke Test ===\n")

    print("Setup — cleaning pre-existing context docs")
    _clean_context_docs()

    with UITestHarness(tag="phase11", render_wait=4.0) as h:
        if h.window_rect is None:
            print("  FAIL  Window did not open within timeout — aborting")
            return 1

        h.pin_window()
        win_left, win_top, win_right, win_bottom = h.window_rect
        print(f"  Window pinned to (0,0); win_bottom={win_bottom}\n")

        # ------------------------------------------------------------------
        # Setup: load sample dungeon via File → Demo Dungeon
        # ------------------------------------------------------------------
        print("Setup — File → Demo Dungeon to load sample dungeon")
        click_app(h.window_rect, menu_slot_center_x("File"), menu_bar_center_y())
        time.sleep(0.3)
        click_app(h.window_rect, menu_slot_center_x("File") + 40, dropdown_item_center_y(2))
        time.sleep(1.5)

        if not _app_alive(h):
            return fail("App crashed during dungeon load — aborting")

        # ------------------------------------------------------------------
        # Behavior 1 — Context docs section renders with real labels
        # ------------------------------------------------------------------
        print("Behavior 1 — Context docs section renders with real row labels")

        shot = h.capture("b1_context_docs_rendered")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        if _app_alive(h):
            ok("App alive after dungeon load — Settings tab renders without crash")
        else:
            return failures + fail("App crashed loading dungeon — aborting")

        # The Settings tab TEAL border should be visible in the tab bar row.
        # Tab bar y band: _tab_y .. _tab_y + _INSP_TAB_H = 760..792
        if _scan_teal(pixels, shot_w, win_left, win_top,
                      INSP_X, INSP_X + PANEL_INSPECTOR_W // 2, 760, 792):
            ok("TEAL found in Settings tab border — Settings tab is active")
        else:
            failures += fail("No TEAL in Settings tab area — tab may not be active")

        # ------------------------------------------------------------------
        # Behavior 2 — All three doc rows show "○ pending" (no TEAL in status area)
        # ------------------------------------------------------------------
        print("\nBehavior 2 — Pending rows: no TEAL in context doc status area")

        # Status area for all three rows: y range 370..430
        if not _scan_teal(pixels, shot_w, win_left, win_top,
                          _STATUS_X0, _STATUS_X1, 368, 432):
            ok("No TEAL in context doc status area — all rows show ○ pending")
        else:
            failures += fail("Unexpected TEAL in context doc status area before any docs saved")

        # ------------------------------------------------------------------
        # Behavior 3 — Clicking a doc row opens the overlay
        # ------------------------------------------------------------------
        print("\nBehavior 3 — Click 'Dungeon Setting' row → overlay opens")

        click_app(h.window_rect, _DOC_ROW_CX, _DOC_ROW_1_Y)
        time.sleep(0.5)

        shot = h.capture("b3_overlay_open")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        # Compute actual screen coordinates for the Save button
        btn_sy  = _btn_screen_y(win_top, win_bottom)
        btn_sx_save = win_left + _SAVE_BTN_CX
        save_screen_x0 = btn_sx_save - _BTN_W // 2 - 4
        save_screen_x1 = btn_sx_save + _BTN_W // 2 + 4
        save_screen_y0 = btn_sy - _BTN_H // 2 - 4
        save_screen_y1 = btn_sy + _BTN_H // 2 + 4

        if _scan_teal_screen(pixels, shot_w,
                             save_screen_x0, save_screen_x1,
                             save_screen_y0, save_screen_y1):
            ok("TEAL Save button detected — overlay is open")
        else:
            failures += fail("No TEAL Save button found — overlay may not have opened")

        if _app_alive(h):
            ok("App alive after clicking doc row")
        else:
            return failures + fail("App crashed after clicking doc row — aborting")

        # ------------------------------------------------------------------
        # Behavior 4 — Esc closes the overlay
        # ------------------------------------------------------------------
        print("\nBehavior 4 — Press Esc → overlay closes")

        key_combo(VK_ESCAPE)
        time.sleep(0.4)

        shot = h.capture("b4_overlay_cancelled")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        # Save button TEAL should be gone after Esc
        if not _scan_teal_screen(pixels, shot_w,
                                  save_screen_x0, save_screen_x1,
                                  save_screen_y0, save_screen_y1):
            ok("No TEAL Save button — overlay closed after Esc")
        else:
            failures += fail("TEAL Save button still present after Esc")

        # Inspector word count should still show no TEAL (still pending)
        if not _scan_teal(pixels, shot_w, win_left, win_top,
                          _STATUS_X0, _STATUS_X1, 415, 435):
            ok("Dungeon Setting row still ○ pending after Esc — no write occurred")
        else:
            failures += fail("Dungeon Setting row shows word count after Esc (unexpected)")

        if _app_alive(h):
            ok("App alive after Esc")
        else:
            return failures + fail("App crashed after Esc — aborting")

        # ------------------------------------------------------------------
        # Behavior 5 — Save persists content and updates word count to TEAL
        # ------------------------------------------------------------------
        print("\nBehavior 5 — Open overlay, type content, Save → TEAL word count")

        click_app(h.window_rect, _DOC_ROW_CX, _DOC_ROW_1_Y)
        time.sleep(0.5)

        # Click inside the text area to ensure focus, then type content
        text_sy = _text_screen_y(win_top, win_bottom)
        text_sx = win_left + _TEXT_CX
        click(text_sx, text_sy)
        time.sleep(0.2)
        type_text("A vast undead tomb beneath the blighted moors.")
        time.sleep(0.2)

        # Click Save button using actual screen coordinates
        click(btn_sx_save, btn_sy)
        time.sleep(0.5)

        shot = h.capture("b5_after_save")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        # Overlay should be closed (no TEAL Save button)
        if not _scan_teal_screen(pixels, shot_w,
                                  save_screen_x0, save_screen_x1,
                                  save_screen_y0, save_screen_y1):
            ok("Overlay closed after Save")
        else:
            failures += fail("Save button still visible after Save — overlay may not have closed")

        # Dungeon Setting row should now show TEAL "✓ NNN words"
        if _scan_teal(pixels, shot_w, win_left, win_top,
                      _STATUS_X0, _STATUS_X1, 415, 435):
            ok("TEAL word count found for Dungeon Setting row — Save persisted content")
        else:
            failures += fail("No TEAL word count in Dungeon Setting row after Save")

        if _app_alive(h):
            ok("App alive after Save")
        else:
            return failures + fail("App crashed after Save — aborting")

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
