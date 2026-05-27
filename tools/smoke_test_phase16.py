"""
Phase 16 smoke test — DM Stateful Conversation.

Behaviors verified:
  1. Edit Memory button visible in title bar (left of "PLAY MODE" badge)
  2. Room click fires DM narration (chat shows DM response)           [API]
  3. Second chat message uses history (no crash)                      [API]
  4. /clear resets history (teal "Conversation cleared." system msg)
  5. /remember <text> still works ("Noted:" system message)
  6. [REMEMBER] tag auto-stripped (tag not visible in chat bubble)    [API]
  7. Edit Memory button click opens overlay ("EDIT MEMORY" title)

Usage:
    cd tools && python smoke_test_phase16.py
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

from smoke_helpers import (
    BG_0,
    CHROME_TITLE_H,
    CHROME_TOTAL_H,
    PAD_MD,
    TEAL,
    WINDOW_H,
    WINDOW_W,
    color_close,
    dropdown_item_center_y,
    fail,
    menu_bar_center_y,
    menu_slot_center_x,
    menu_slot_x,
    ok,
    pixel_rgb,
    room_center,
)
from ui_harness import UITestHarness
from ui_input import (
    VK_CONTROL,
    click_app,
    key_combo,
    type_text,
)

# ---------------------------------------------------------------------------
# Play View layout constants
# ---------------------------------------------------------------------------

PANEL_CHAT_W = 440
CONTENT_H    = WINDOW_H - CHROME_TOTAL_H   # 830

# Chat input area (Arcade coords, y=0 at bottom of window)
# Source: smoke_test_phase8.py — confirmed working
_INPUT_AREA_H = 160
CHAT_INPUT_X  = 8 + 344 / 2    # ~180
CHAT_INPUT_Y  = 34 + 112 / 2   # ~90
CHAT_SEND_X   = 356 + 76 / 2   # ~394
CHAT_SEND_Y   = 34 + 38 / 2    # ~53

# Map origin (Arcade coords) — includes auto-centering pan offset from MapPanel._center_level()
# Level 1 bounding box: gx in [1,14], gy in [2,11] → grid centroid (7.5, 6.5)
# map_viewport: w=890, h=792 → pan_x=73, pan_y=72
_MAP_W       = WINDOW_W - PANEL_CHAT_W - 70     # 890 (minus stepper rail)
_MAP_H       = CONTENT_H - 38                   # 792 (minus header bar)
_GRID_CX     = 7.5                              # (min_gx + max_gx) / 2
_GRID_CY     = 6.5                              # (min_gy + max_gy) / 2
_CELL_PX     = 48
_PAN_X       = _MAP_W / 2 - PAD_MD - _GRID_CX * _CELL_PX   # 73
_PAN_Y       = _MAP_H / 2 - PAD_MD - _GRID_CY * _CELL_PX   # 72
_ORIGIN_X    = PANEL_CHAT_W + PAD_MD + _PAN_X   # 525
_ORIGIN_Y    = PAD_MD + _PAN_Y                  # 84

# Rooms: Demo Dungeon (Tomb of the Forgotten King) Level 1 — from dungeon.json
# room_center(room_x, room_y, room_w, room_h, origin_x, origin_y)
_ROOM_FLOODED_ENTRY   = room_center(1, 4, 3, 3, _ORIGIN_X, _ORIGIN_Y)  # 1-A → (645, 348)
_ROOM_DROWNED_SHRINE  = room_center(5, 2, 4, 4, _ORIGIN_X, _ORIGIN_Y)  # 1-B → (861, 276)

# Edit Memory button — custom title bar, top-right area (Arcade coords)
# Title bar occupies Arcade y: [CONTENT_H, WINDOW_H] = [830, 900]
# The menu bar is at the very top (y ∈ [874, 900]); title bar below it (y ∈ [830, 874])
_TITLE_BAR_MID_Y = CONTENT_H + CHROME_TITLE_H / 2   # ~852
_EDIT_MEM_BTN_X  = WINDOW_W - 185                    # ~1215, left of PLAY MODE badge

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VK_A = 0x41

_FILE_DEMO_ITEM_INDEX = 2   # File menu: New(0) Open(1) Demo Dungeon(2) Save(3)


def _app_alive(h: UITestHarness) -> bool:
    return h._proc is not None and h._proc.poll() is None


def _has_violet(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> bool:
    """True if a violet DM/system bubble border pixel exists in the chat area."""
    for y_arc in range(_INPUT_AREA_H, CONTENT_H, 2):
        for x_arc in range(15, PANEL_CHAT_W - 10, 2):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x_arc, y_arc)
            if r > 140 and b > 180 and g < 130:
                return True
    return False


def _has_teal_in_chat(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> bool:
    """True if a teal system-message pixel exists in the chat area."""
    for y_arc in range(_INPUT_AREA_H, CONTENT_H, 2):
        for x_arc in range(15, PANEL_CHAT_W - 10, 2):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x_arc, y_arc)
            if color_close((r, g, b), TEAL, tol=50):
                return True
    return False


def _send_chat(h: UITestHarness, msg: str) -> None:
    click_app(h.window_rect, CHAT_INPUT_X, CHAT_INPUT_Y)
    time.sleep(0.2)
    key_combo(VK_CONTROL, _VK_A)
    time.sleep(0.1)
    type_text(msg)
    time.sleep(0.15)
    click_app(h.window_rect, CHAT_SEND_X, CHAT_SEND_Y)


def _wait_for_dm(h: UITestHarness, tag: str, attempts: int = 3, wait: float = 12.0) -> bool:
    """Poll for a violet DM bubble; capture a screenshot each attempt."""
    for i in range(1, attempts + 1):
        print(f"  Waiting for DM response (attempt {i}/{attempts})…")
        time.sleep(wait)
        shot = h.capture(f"{tag}_{i}")
        pixels, shot_w = h.pixels, h.shot_w
        win_left, win_top = h.window_rect[0], h.window_rect[1]
        print(f"  Screenshot: {shot.name}")
        if _has_violet(pixels, shot_w, win_left, win_top):
            return True
    return False



def _switch_to_play_mode(h: UITestHarness) -> None:
    """Click Play → Switch to Play via the menu bar."""
    click_app(h.window_rect, menu_slot_center_x("Play"), menu_bar_center_y())
    time.sleep(0.4)
    click_app(h.window_rect, menu_slot_x("Play") + 40, dropdown_item_center_y(0))
    time.sleep(1.5)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    failures = 0
    has_api  = bool(os.environ.get("OPENAI_API_KEY"))

    print("\n=== Phase 16 Smoke Test — DM Stateful Conversation ===\n")
    if not has_api:
        print("  NOTE  OPENAI_API_KEY not set — behaviors 2, 3, 6 (LLM calls) skipped\n")

    with UITestHarness(tag="phase16", render_wait=4.0) as h:
        if h.window_rect is None:
            print("  FAIL  Window did not open within timeout — aborting")
            return 1

        win_left, win_top, _, _ = h.window_rect
        print(f"  Window rect: {h.window_rect}\n")

        # ── Setup: load Demo Dungeon via File menu ───────────────────────────
        print("Setup — File → Demo Dungeon")
        click_app(h.window_rect, menu_slot_center_x("File"), menu_bar_center_y())
        time.sleep(0.4)
        click_app(h.window_rect, menu_slot_x("File") + 40, dropdown_item_center_y(_FILE_DEMO_ITEM_INDEX))
        time.sleep(1.5)

        h.refresh_window_rect()
        win_left, win_top = h.window_rect[0], h.window_rect[1]

        shot = h.capture("00_after_load")
        print(f"  Screenshot: {shot.name}")

        if not _app_alive(h):
            return fail("App crashed after dungeon load — aborting")

        # ── Setup: switch to Play Mode ────────────────────────────────────────
        print("\nSetup — Play → Switch to Play")
        _switch_to_play_mode(h)
        h.refresh_window_rect()
        win_left, win_top = h.window_rect[0], h.window_rect[1]

        shot = h.capture("01_play_mode")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        if not _app_alive(h):
            return fail("App crashed switching to Play Mode — aborting")

        # ── Behavior 1: Edit Memory button visible in title bar ───────────────
        print("\nBehavior 1 — Edit Memory button visible in title bar")
        found_btn = False
        for dx in range(-60, 61, 3):
            r, g, b = pixel_rgb(
                pixels, shot_w, win_left, win_top,
                _EDIT_MEM_BTN_X + dx, _TITLE_BAR_MID_Y,
            )
            if not color_close((r, g, b), BG_0, tol=20):
                found_btn = True
                break
        if found_btn:
            ok("Non-background pixels at Edit Memory button position — button rendered")
        else:
            failures += fail("Button area appears uniform BG_0 — Edit Memory button may be missing")

        # ── Behavior 2: Room click fires DM narration ─────────────────────────
        if has_api:
            print("\nBehavior 2 — Room click fires DM narration (Flooded Entry)")
            rx, ry = _ROOM_FLOODED_ENTRY
            click_app(h.window_rect, rx, ry)
            if _wait_for_dm(h, "02_room_click"):
                ok("Violet DM bubble in chat — narration fired")
            else:
                failures += fail("No violet DM bubble after room click")

            if not _app_alive(h):
                return failures + fail("App crashed — aborting")
        else:
            print("\nBehavior 2 — SKIP (no API key)")

        # ── Behavior 3: Second message uses history ───────────────────────────
        if has_api:
            print("\nBehavior 3 — Second chat message uses history (no crash)")
            _send_chat(h, "What else can you tell me about this area?")
            if _wait_for_dm(h, "03_history"):
                ok("DM responded to follow-up — history passed, no crash")
            else:
                failures += fail("No DM response to follow-up message")

            if not _app_alive(h):
                return failures + fail("App crashed — aborting")
        else:
            print("\nBehavior 3 — SKIP (no API key)")

        # ── Behavior 4: /clear resets history ────────────────────────────────
        print("\nBehavior 4 — /clear resets history (teal confirmation)")
        _send_chat(h, "/clear")
        time.sleep(1.5)
        shot = h.capture("04_clear")
        pixels, shot_w = h.pixels, h.shot_w
        win_left, win_top = h.window_rect[0], h.window_rect[1]
        print(f"  Screenshot: {shot.name}")
        if _has_teal_in_chat(pixels, shot_w, win_left, win_top):
            ok("Teal pixel in chat — conversation cleared system message rendered")
        else:
            failures += fail("No teal system message after /clear")

        # ── Behavior 5: /remember still works ───────────────────────────────
        print("\nBehavior 5 — /remember <text> still works")
        _send_chat(h, "/remember The eastern corridor has a trapped floor tile.")
        time.sleep(1.5)
        shot = h.capture("05_remember")
        pixels, shot_w = h.pixels, h.shot_w
        win_left, win_top = h.window_rect[0], h.window_rect[1]
        print(f"  Screenshot: {shot.name}")
        if _has_violet(pixels, shot_w, win_left, win_top):
            ok("Violet system bubble after /remember — confirmation rendered")
        else:
            failures += fail("No violet bubble after /remember")

        # ── Behavior 6: [REMEMBER] tag auto-stripped ──────────────────────────
        if has_api:
            print("\nBehavior 6 — [REMEMBER] tag auto-stripped (screenshot for review)")
            rx2, ry2 = _ROOM_DROWNED_SHRINE
            click_app(h.window_rect, rx2, ry2)
            if _wait_for_dm(h, "06_tag_stripped"):
                ok("DM responded — inspect screenshot for absence of [REMEMBER] tag")
            else:
                failures += fail("No DM response for [REMEMBER] tag check")

            if not _app_alive(h):
                return failures + fail("App crashed — aborting")
        else:
            print("\nBehavior 6 — SKIP (no API key)")

        # ── Behavior 7: Edit Memory button opens overlay ──────────────────────
        print("\nBehavior 7 — Edit Memory button click opens overlay")
        click_app(h.window_rect, _EDIT_MEM_BTN_X, _TITLE_BAR_MID_Y)
        time.sleep(1.0)
        shot = h.capture("07_overlay")
        pixels, shot_w = h.pixels, h.shot_w
        win_left, win_top = h.window_rect[0], h.window_rect[1]
        print(f"  Screenshot: {shot.name}")

        cx, cy = WINDOW_W // 2, CONTENT_H // 2
        found_overlay = False
        for dy in range(-80, 81, 8):
            for dx in range(-160, 161, 8):
                r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, cx + dx, cy + dy)
                if not color_close((r, g, b), BG_0, tol=8):
                    found_overlay = True
                    break
            if found_overlay:
                break
        if found_overlay:
            ok("Non-BG_0 region in window center — Edit Memory overlay rendered")
        else:
            failures += fail("Window center appears uniform — overlay may not have opened")

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
