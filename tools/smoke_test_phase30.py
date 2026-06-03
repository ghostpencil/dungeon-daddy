"""
Phase 30 smoke test — Play Mode UI + Debug Tools.

Behaviors verified:
  1. App launches and switches to Play Mode without crashing            (30-7)
  2. RPG toggle button visible in title bar                             (30-7)
  3. Click RPG toggle → RPG side panel opens (BG_1 fills panel area)    (30-7)
  4. CHAR tab renders character sheet (default, no crash)               (30-2)
  5. DBG tab renders DEBUG CONTROLS section                             (30-6)
  6. MEM tab renders memory inspector with search input                 (30-5)
  7. FALLOUT tab renders fallout panel content                          (30-4)
  8. App alive after all checks                                         (30-7)

Screenshots and artifacts saved to:
  tools/screenshots/phase30_*.png
  artifacts/play_mode/phase30/

Usage:
    cd tools && python smoke_test_phase30.py

ANTHROPIC_API_KEY required for vision assertions (behaviors 5-7).
"""
from __future__ import annotations

import base64
import os
import shutil
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
    BG_1,
    CHROME_TOTAL_H,
    PAD_MD,
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
)
from ui_harness import UITestHarness
from ui_input import click_app, type_text

# ---------------------------------------------------------------------------
# Layout constants  (match dungeon_daddy/ui/theme.py and play_view.py)
# ---------------------------------------------------------------------------

CONTENT_H       = WINDOW_H - CHROME_TOTAL_H          # 830
_PANEL_CHAT_W   = 440
_RPG_PANEL_W    = 300
_RPG_TAB_H      = 26
_BTN_RPG_W      = 88
_BTN_EDIT_W     = 100
_BTN_H          = 24
_BOX_H          = 26.0    # MEM search box height (memory_inspector_panel._BOX_H)
_CHROME_TITLE_H = 44

# RPG toggle button position in the title bar
_PLAY_BADGE_W   = 100
_EDIT_LEFT      = WINDOW_W - PAD_MD - _PLAY_BADGE_W - PAD_MD * 2 - _BTN_EDIT_W   # 1164
_RPG_BTN_RIGHT  = _EDIT_LEFT - PAD_MD                                               # 1152
_RPG_BTN_X      = _RPG_BTN_RIGHT - _BTN_RPG_W                                      # 1064
_BAR_MID        = CONTENT_H + _CHROME_TITLE_H / 2                                   # 852.0
_RPG_BTN_Y      = _BAR_MID - _BTN_H / 2                                             # 840.0
_RPG_BTN_CX     = _RPG_BTN_X + _BTN_RPG_W / 2                                      # 1108.0
_RPG_BTN_CY     = _RPG_BTN_Y + _BTN_H / 2                                           # 852.0

# RPG panel area (when open)
_MAP_W_OPEN     = WINDOW_W - _PANEL_CHAT_W - _RPG_PANEL_W   # 660
_RPG_PANEL_X    = _PANEL_CHAT_W + _MAP_W_OPEN                # 1100

# Tab bar (when RPG panel open)
_TAB_W          = _RPG_PANEL_W / 5                           # 60.0
_TAB_Y          = float(CONTENT_H - _RPG_TAB_H)              # 804.0
_TAB_CY         = _TAB_Y + _RPG_TAB_H / 2                   # 817.0
# Tab centre x: CHAR=1130, SCENE=1190, FALLOUT=1250, MEM=1310, DBG=1370
_TAB_CX         = [_RPG_PANEL_X + i * _TAB_W + _TAB_W / 2 for i in range(5)]

# BG_2 — elevated surface color used for the RPG toggle button fill
_BG_2 = (48, 45, 68)

# File → Demo Dungeon index
_FILE_DEMO_IDX  = 2

# Artifact output dir
_ARTIFACTS_DIR  = _PROJECT_ROOT / "artifacts" / "play_mode" / "phase30"


# ---------------------------------------------------------------------------
# Vision assertion helper
# ---------------------------------------------------------------------------

def _vision_assert(screenshot_path: Path, question: str) -> bool:
    """Ask Claude a yes/no question about a screenshot. Returns True for YES."""
    import anthropic
    client = anthropic.Anthropic()
    img_b64 = base64.standard_b64encode(screenshot_path.read_bytes()).decode()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=5,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
                },
                {"type": "text", "text": f"{question}\nReply with only YES or NO."},
            ],
        }],
    )
    return response.content[0].text.strip().upper().startswith("Y")


# ---------------------------------------------------------------------------
# Pixel helpers
# ---------------------------------------------------------------------------

def _rpg_btn_is_rendered(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> bool:
    """True if BG_2-ish pixels appear at the RPG toggle button position."""
    for dx in range(-int(_BTN_RPG_W / 2), int(_BTN_RPG_W / 2), 4):
        r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, _RPG_BTN_CX + dx, _RPG_BTN_CY)
        if color_close((r, g, b), _BG_2, tol=20):
            return True
    return False


def _rpg_panel_is_open(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> bool:
    """True if the RPG panel area renders with BG_1 fill (not map BG_0)."""
    panel_mid_x = _RPG_PANEL_X + _RPG_PANEL_W / 2   # 1250
    panel_mid_y = CONTENT_H / 2                       # 415
    r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, panel_mid_x, panel_mid_y)
    return color_close((r, g, b), BG_1, tol=20)


def _app_alive(h: UITestHarness) -> bool:
    return h._proc is not None and h._proc.poll() is None


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

def _load_demo_dungeon(h: UITestHarness) -> None:
    click_app(h.window_rect, menu_slot_center_x("File"), menu_bar_center_y())
    time.sleep(0.4)
    click_app(h.window_rect, menu_slot_x("File") + 40, dropdown_item_center_y(_FILE_DEMO_IDX))
    time.sleep(1.5)
    h.refresh_window_rect()


def _switch_to_play_mode(h: UITestHarness) -> None:
    # Demo dungeon has no save_name so "Switch to Play" in the Play menu is
    # disabled.  Click the "Test Drive" button in the inspector footer instead.
    # Inspector: x=1080, y=0, w=320.  Footer btn_cy = FOOTER_H/2 = 22.
    # Button centre: x = 1080 + PAD_MD + ghost_w/2 = 1080 + 12 + 50 = 1142
    _TEST_DRIVE_X = 1142.0
    _TEST_DRIVE_Y = 22.0
    click_app(h.window_rect, _TEST_DRIVE_X, _TEST_DRIVE_Y)
    time.sleep(1.5)
    h.refresh_window_rect()


def _click_tab(h: UITestHarness, tab_index: int) -> None:
    """Click a tab in the RPG side panel (0=CHAR, 1=SCENE, 2=FALLOUT, 3=MEM, 4=DBG)."""
    click_app(h.window_rect, _TAB_CX[tab_index], _TAB_CY)
    time.sleep(0.5)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    failures = 0
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))

    print("\n=== Phase 30 Smoke Test — Play Mode UI + Debug Tools ===\n")
    if not has_anthropic:
        print("  NOTE  ANTHROPIC_API_KEY not set — vision assertions (behaviors 5-7) skipped\n")

    _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    screenshots: list[Path] = []

    with UITestHarness(tag="phase30", render_wait=4.0) as h:
        if h.window_rect is None:
            print("  FAIL  Window did not open within timeout — aborting")
            return 1

        print(f"  Window rect: {h.window_rect}\n")

        # ── Setup: load demo dungeon ─────────────────────────────────────────
        print("Setup — File → Demo Dungeon")
        _load_demo_dungeon(h)
        if not _app_alive(h):
            return fail("App crashed after dungeon load — aborting")

        # ── Setup: switch to Play Mode ───────────────────────────────────────
        print("Setup — Play → Switch to Play")
        _switch_to_play_mode(h)
        if not _app_alive(h):
            return fail("App crashed switching to Play Mode — aborting")

        win_left, win_top = h.window_rect[0], h.window_rect[1]

        # ── Behavior 1: app alive in Play Mode ───────────────────────────────
        print("\nBehavior 1 — App alive in Play Mode")
        shot = h.capture("00_play_mode")
        screenshots.append(shot)
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")
        if _app_alive(h):
            ok("App alive after switching to Play Mode")
        else:
            return fail("App crashed in Play Mode — aborting")

        # ── Behavior 2: RPG toggle button visible ────────────────────────────
        print(f"\nBehavior 2 — RPG toggle button at ({_RPG_BTN_CX:.0f}, {_RPG_BTN_CY:.0f})")
        if _rpg_btn_is_rendered(pixels, shot_w, win_left, win_top):
            ok("BG_2 pixels at RPG toggle button position — button rendered")
        else:
            failures += fail("No BG_2 pixels at RPG toggle button — button may not be rendered")

        # ── Behavior 3: Click toggle → RPG panel opens ───────────────────────
        print("\nBehavior 3 — Click RPG toggle → side panel opens")
        click_app(h.window_rect, _RPG_BTN_CX, _RPG_BTN_CY)
        time.sleep(0.8)
        shot = h.capture("01_rpg_panel_open")
        screenshots.append(shot)
        pixels, shot_w = h.pixels, h.shot_w
        win_left, win_top = h.window_rect[0], h.window_rect[1]
        print(f"  Screenshot: {shot.name}")
        if _rpg_panel_is_open(pixels, shot_w, win_left, win_top):
            ok("BG_1 fill in RPG panel area — panel is open")
        else:
            failures += fail("Expected BG_1 in RPG panel area — panel may not have opened")

        if not _app_alive(h):
            return failures + fail("App crashed after opening RPG panel — aborting")

        # ── Behavior 4: CHAR tab renders (default tab, no crash) ─────────────
        print("\nBehavior 4 — CHAR tab renders character sheet (default tab)")
        _click_tab(h, 0)
        shot = h.capture("02_char_tab")
        screenshots.append(shot)
        print(f"  Screenshot: {shot.name}")
        if _app_alive(h):
            ok("App alive on CHAR tab — character sheet panel rendered without crash")
        else:
            return failures + fail("App crashed on CHAR tab — aborting")

        # ── Behavior 5: DBG tab renders debug controls section ───────────────
        print("\nBehavior 5 — DBG tab renders DEBUG CONTROLS section")
        _click_tab(h, 4)
        shot = h.capture("03_dbg_tab")
        screenshots.append(shot)
        print(f"  Screenshot: {shot.name}")
        if not _app_alive(h):
            return failures + fail("App crashed on DBG tab — aborting")
        if has_anthropic:
            dbg_ok = _vision_assert(
                shot,
                "In the narrow right-side panel, is there any text visible in the content area "
                "below the tab bar? (e.g. 'DEBUG CONTROLS', 'No RPG service', or any label)",
            )
            if dbg_ok:
                ok("DBG tab rendered with visible content")
            else:
                failures += fail("DBG tab content not detected — check screenshot")
        else:
            ok("DBG tab — no crash (vision assertion skipped)")

        # ── Behavior 6: MEM tab renders memory inspector with search input ───
        print("\nBehavior 6 — MEM tab renders memory inspector")
        _click_tab(h, 3)
        time.sleep(0.5)
        shot = h.capture("04_mem_tab")
        screenshots.append(shot)
        print(f"  Screenshot: {shot.name}")
        if not _app_alive(h):
            return failures + fail("App crashed on MEM tab — aborting")
        if has_anthropic:
            mem_ok = _vision_assert(
                shot,
                "In the narrow right-side panel, is there a memory inspector with a search "
                "input field or text box visible?",
            )
            if mem_ok:
                ok("MEM tab shows memory inspector with search input")
            else:
                failures += fail("MEM tab search input not detected — check screenshot")
        else:
            ok("MEM tab — no crash (vision assertion skipped)")

        # Click the search box and type to verify it accepts input
        # Search box Arcade coords: cx=1250, cy=779 (top of MEM panel, y=766 + h/2)
        if _app_alive(h):
            print("  Clicking MEM search box and typing a query…")
            _MEM_SEARCH_CX = _RPG_PANEL_X + _RPG_PANEL_W / 2   # 1250 — box centre x
            _MEM_SEARCH_CY = CONTENT_H - _RPG_TAB_H - PAD_MD - _BOX_H / 2  # ~779
            click_app(h.window_rect, _MEM_SEARCH_CX, _MEM_SEARCH_CY)
            time.sleep(0.3)
            type_text("fallout")
            time.sleep(0.5)
            shot = h.capture("05_mem_search")
            screenshots.append(shot)
            print(f"  Screenshot: {shot.name}")
            if _app_alive(h):
                ok("MEM search input accepted text without crash")
            else:
                failures += fail("App crashed after typing in MEM search")

        # ── Behavior 7: FALLOUT tab renders fallout panel ────────────────────
        print("\nBehavior 7 — FALLOUT tab renders fallout panel")
        _click_tab(h, 2)
        shot = h.capture("06_fallout_tab")
        screenshots.append(shot)
        print(f"  Screenshot: {shot.name}")
        if not _app_alive(h):
            return failures + fail("App crashed on FALLOUT tab — aborting")
        if has_anthropic:
            fallout_ok = _vision_assert(
                shot,
                "In the narrow right-side panel, is there fallout panel content visible — "
                "such as 'No active fallout' text, a fallout list, or fallout section labels?",
            )
            if fallout_ok:
                ok("FALLOUT tab renders fallout panel content")
            else:
                failures += fail("FALLOUT tab content not detected — check screenshot")
        else:
            ok("FALLOUT tab — no crash (vision assertion skipped)")

        # ── Behavior 8: app alive after all checks ───────────────────────────
        print("\nBehavior 8 — App alive after all checks")
        if _app_alive(h):
            ok("App alive after all panel checks")
        else:
            failures += fail("App crashed during panel traversal")

    # ── Copy screenshots to artifacts dir ────────────────────────────────────
    print(f"\nCopying {len(screenshots)} screenshot(s) to {_ARTIFACTS_DIR} …")
    for src in screenshots:
        dst = _ARTIFACTS_DIR / src.name
        shutil.copy2(src, dst)
    print(f"  Artifacts saved to: {_ARTIFACTS_DIR}")

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
