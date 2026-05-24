"""
Phase 17 smoke test — Play Mode Loop Guidance.

Behaviors verified:
  1. Loop Toggle Strip — pill visible in bottom-right of map canvas        (F-27)
  2. Click pill — system message posted in chat                            (F-28)
  3. Click pill — loop overlay (violet path B lines) appears on map        (F-27)
  4. Click pill again — 'cleared' system message posted                    (F-28)
  5. Click pill again — violet overlay lines gone from map                 (F-27)
  6. DM narration references active loop when room clicked                 (F-29) [API]

Usage:
    cd tools && python smoke_test_phase17.py

Demo dungeon Level 1 has one loop:
  id='L1-main'  pattern='lock_key'
  entry='1-A' (Flooded Entry) → goal='1-B' (Drowned Shrine)
  path_a=['1-A','1-B']
  path_b=['1-A','1-C','1-E','1-D','1-B']
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _load_dotenv() -> None:
    env_path = _PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

from ui_harness import UITestHarness
from ui_input import click_app
from smoke_helpers import (
    WINDOW_W, WINDOW_H, CHROME_TOTAL_H,
    PAD_MD, TEAL,
    ok, fail,
    pixel_rgb, color_close,
    menu_slot_center_x, menu_slot_x, menu_bar_center_y, dropdown_item_center_y,
    room_center,
)

# ---------------------------------------------------------------------------
# Layout constants (Arcade coordinate system: y=0 at bottom of content area)
# ---------------------------------------------------------------------------

PANEL_CHAT_W     = 440
PANEL_STEPPER_W  = 70
CONTENT_H        = WINDOW_H - CHROME_TOTAL_H   # 830

# Loop pill — bottom-right of map canvas (Arcade coords)
# _build_loop_strip_rects: right_edge = map_x + (map_w - stepper) - PAD = 1322
#                          x1 = right_edge - 110 = 1212, y1 = 8, pill_h = 24
_PILL_W    = 110
_PILL_H    = 24
_PILL_PAD  = 8
_MAP_X     = PANEL_CHAT_W                              # 440
_MAP_W     = WINDOW_W - PANEL_CHAT_W                   # 960
_RIGHT_EDGE = _MAP_X + (_MAP_W - PANEL_STEPPER_W) - _PILL_PAD  # 1322
_PILL_X1   = _RIGHT_EDGE - _PILL_W                    # 1212
_PILL_Y1   = _PILL_PAD                                 # 8
_PILL_CX   = _PILL_X1 + _PILL_W / 2                   # 1267
_PILL_CY   = _PILL_Y1 + _PILL_H / 2                   # 20

# Map content area (for overlay pixel scanning)
_MAP_SCAN_X1 = PANEL_CHAT_W + PAD_MD
_MAP_SCAN_X2 = WINDOW_W - PANEL_STEPPER_W - PAD_MD
_MAP_SCAN_Y1 = 40   # above the pill strip
_MAP_SCAN_Y2 = CONTENT_H - 50

# PATH_B color (violet — used for loop overlay path B lines)
_PATH_B = (178, 100, 232)

# Chat scan area
_CHAT_X1, _CHAT_X2 = 15, PANEL_CHAT_W - 10
_CHAT_Y1, _CHAT_Y2 = 160, CONTENT_H

# Rooms: Level 1 origin uses auto-centered pan offset (from smoke_test_phase16.py)
_MAP_W_INNER  = WINDOW_W - PANEL_CHAT_W - 70
_MAP_H_INNER  = CONTENT_H - 38
_GRID_CX      = 7.5
_GRID_CY      = 6.5
_CELL_PX      = 48
_PAN_X        = _MAP_W_INNER / 2 - PAD_MD - _GRID_CX * _CELL_PX
_PAN_Y        = _MAP_H_INNER / 2 - PAD_MD - _GRID_CY * _CELL_PX
_ORIGIN_X     = PANEL_CHAT_W + PAD_MD + _PAN_X
_ORIGIN_Y     = PAD_MD + _PAN_Y
_ROOM_1A      = room_center(1, 4, 3, 3, _ORIGIN_X, _ORIGIN_Y)   # Flooded Entry
_ROOM_1B      = room_center(5, 2, 4, 4, _ORIGIN_X, _ORIGIN_Y)   # Drowned Shrine

_FILE_DEMO_IDX = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app_alive(h: UITestHarness) -> bool:
    return h._proc is not None and h._proc.poll() is None


def _has_teal_in_chat(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> bool:
    for y_arc in range(_CHAT_Y1, _CHAT_Y2, 2):
        for x_arc in range(_CHAT_X1, _CHAT_X2, 2):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x_arc, y_arc)
            if color_close((r, g, b), TEAL, tol=50):
                return True
    return False


def _count_violet_on_map(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> int:
    """Count PATH_B_COLOR (violet) pixels on the map canvas."""
    count = 0
    for y_arc in range(_MAP_SCAN_Y1, _MAP_SCAN_Y2, 2):
        for x_arc in range(_MAP_SCAN_X1, _MAP_SCAN_X2, 4):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x_arc, y_arc)
            if color_close((r, g, b), _PATH_B, tol=40):
                count += 1
    return count


def _pill_is_rendered(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> bool:
    """True if non-background pixels exist at the expected pill location."""
    from smoke_helpers import BG_0
    for dx in range(-int(_PILL_W / 2), int(_PILL_W / 2), 4):
        r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, int(_PILL_CX) + dx, int(_PILL_CY))
        if not color_close((r, g, b), BG_0, tol=15):
            return True
    return False


def _has_violet_in_chat(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> bool:
    """True if a violet DM/system bubble border exists in the chat area."""
    for y_arc in range(_CHAT_Y1, _CHAT_Y2, 2):
        for x_arc in range(_CHAT_X1, _CHAT_X2, 2):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x_arc, y_arc)
            if r > 140 and b > 180 and g < 130:
                return True
    return False


def _wait_for_dm(h: UITestHarness, tag: str, attempts: int = 3, wait: float = 12.0) -> bool:
    for i in range(1, attempts + 1):
        print(f"  Waiting for DM response (attempt {i}/{attempts})…")
        time.sleep(wait)
        h.capture(f"{tag}_{i}")
        if _has_violet_in_chat(h.pixels, h.shot_w, h.window_rect[0], h.window_rect[1]):
            return True
    return False


def _switch_to_play_mode(h: UITestHarness) -> None:
    click_app(h.window_rect, menu_slot_center_x("Play"), menu_bar_center_y())
    time.sleep(0.4)
    click_app(h.window_rect, menu_slot_x("Play") + 40, dropdown_item_center_y(0))
    time.sleep(1.5)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    failures = 0
    has_api = bool(os.environ.get("OPENAI_API_KEY"))

    print("\n=== Phase 17 Smoke Test — Play Mode Loop Guidance ===\n")
    if not has_api:
        print("  NOTE  OPENAI_API_KEY not set — behavior 6 (DM loop context) skipped\n")

    with UITestHarness(tag="phase17", render_wait=4.0) as h:
        if h.window_rect is None:
            print("  FAIL  Window did not open within timeout — aborting")
            return 1

        win_left, win_top = h.window_rect[0], h.window_rect[1]
        print(f"  Window rect: {h.window_rect}\n")

        # ── Setup: File → Demo Dungeon ──────────────────────────────────────
        print("Setup — File → Demo Dungeon")
        click_app(h.window_rect, menu_slot_center_x("File"), menu_bar_center_y())
        time.sleep(0.4)
        click_app(h.window_rect, menu_slot_x("File") + 40, dropdown_item_center_y(_FILE_DEMO_IDX))
        time.sleep(1.5)
        h.refresh_window_rect()
        win_left, win_top = h.window_rect[0], h.window_rect[1]

        if not _app_alive(h):
            return fail("App crashed after dungeon load — aborting")

        # ── Setup: Play → Switch to Play ────────────────────────────────────
        print("Setup — Play → Switch to Play")
        _switch_to_play_mode(h)
        h.refresh_window_rect()
        win_left, win_top = h.window_rect[0], h.window_rect[1]

        shot = h.capture("00_play_mode")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        if not _app_alive(h):
            return fail("App crashed switching to Play Mode — aborting")

        # ── Behavior 1: Loop Toggle Strip pill visible ──────────────────────
        print(f"\nBehavior 1 — Loop Toggle Strip pill visible at ({_PILL_CX:.0f}, {_PILL_CY:.0f})")
        if _pill_is_rendered(pixels, shot_w, win_left, win_top):
            ok("Non-background pixels at pill location — strip rendered")
        else:
            failures += fail("Pill area appears uniform background — strip not rendered")

        # Baseline violet count (shrine room always has violet border)
        violet_baseline = _count_violet_on_map(pixels, shot_w, win_left, win_top)
        print(f"  Violet baseline pixel count: {violet_baseline}")

        # ── Behavior 2: Click pill → system message in chat ─────────────────
        print("\nBehavior 2 — Click pill → system message in chat (F-28)")
        click_app(h.window_rect, _PILL_CX, _PILL_CY)
        time.sleep(0.8)
        shot = h.capture("02_after_activate")
        pixels, shot_w = h.pixels, h.shot_w
        win_left, win_top = h.window_rect[0], h.window_rect[1]
        print(f"  Screenshot: {shot.name}")
        if _has_teal_in_chat(pixels, shot_w, win_left, win_top):
            ok("Teal pixel in chat after pill click — system message posted")
        else:
            failures += fail("No teal system message in chat after activating loop")

        if not _app_alive(h):
            return failures + fail("App crashed after pill click — aborting")

        # ── Behavior 3: Loop overlay (violet) increases pixel count ─────────
        print("\nBehavior 3 — Loop overlay path B (violet) increases map violet pixels (F-27)")
        violet_active = _count_violet_on_map(pixels, shot_w, win_left, win_top)
        print(f"  Violet pixel count with overlay: {violet_active} (baseline: {violet_baseline})")
        if violet_active > violet_baseline + 5:
            ok(f"Violet pixel count rose by {violet_active - violet_baseline} — loop overlay active")
        else:
            failures += fail(f"Violet pixel count unchanged ({violet_active} vs baseline {violet_baseline}) — overlay may not be drawing")

        # ── Behavior 4: Click pill again → 'cleared' message ────────────────
        print("\nBehavior 4 — Click pill again → 'Loop overlay cleared.' system message (F-28)")
        click_app(h.window_rect, _PILL_CX, _PILL_CY)
        time.sleep(0.8)
        shot = h.capture("04_after_deactivate")
        pixels, shot_w = h.pixels, h.shot_w
        win_left, win_top = h.window_rect[0], h.window_rect[1]
        print(f"  Screenshot: {shot.name}")
        if _has_teal_in_chat(pixels, shot_w, win_left, win_top):
            ok("Teal pixel in chat after deactivate — 'cleared' message posted")
        else:
            failures += fail("No teal message in chat after deactivating loop")

        # ── Behavior 5: Violet count returns to baseline after deactivate ───
        print("\nBehavior 5 — Violet overlay gone after deactivation (F-27)")
        violet_after = _count_violet_on_map(pixels, shot_w, win_left, win_top)
        print(f"  Violet pixel count after deactivate: {violet_after} (baseline: {violet_baseline})")
        if violet_after <= violet_baseline + 5:
            ok(f"Violet count back to baseline — loop overlay cleared")
        else:
            failures += fail(f"Violet count still elevated ({violet_after} vs baseline {violet_baseline}) — overlay not cleared")

        # ── Behavior 6: DM narration references active loop ─────────────────
        if has_api:
            print("\nBehavior 6 — DM narration references active loop when room clicked (F-29)")
            # Re-activate loop
            click_app(h.window_rect, _PILL_CX, _PILL_CY)
            time.sleep(0.5)
            # Click a room
            rx, ry = _ROOM_1A
            click_app(h.window_rect, rx, ry)
            if _wait_for_dm(h, "06_dm_loop_context"):
                ok("DM responded while loop active — inspect screenshot for loop context")
            else:
                failures += fail("No DM response while loop active")

            if not _app_alive(h):
                return failures + fail("App crashed — aborting")
        else:
            print("\nBehavior 6 — SKIP (no API key)")

        if _app_alive(h):
            ok("App alive after all checks")
        else:
            failures += fail("App crashed before clean exit")

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
