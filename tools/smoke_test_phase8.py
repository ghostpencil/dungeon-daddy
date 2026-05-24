"""
Phase 8 smoke test — DM Chat + /remember + Map Variants + File Save.

Behaviors verified:
  1. Room click → TEAL highlight appears; DM narration fires (if OPENAI_API_KEY set)
  2. /remember <note> → system confirmation bubble (VIOLET) appears in chat
  3. View → Map: Tiles → renderer switches without crash
  4. View → Map: Graph → renderer switches without crash
  5. File → Save → app survives; no crash

File hygiene
------------
The test snapshots every file it may create before it runs.  On exit (even on
failure) it restores each file to its pre-test state:
  * File didn't exist → deleted if the test created it
  * File existed      → original bytes written back
The memory directory is removed only if the test created it from scratch.

Usage:
    cd tools && python smoke_test_phase8.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _load_dotenv() -> None:
    """Load project-root .env into os.environ if present.

    Keys already present in the environment are never overwritten, so the
    real shell environment always takes precedence over the file.
    """
    env_path = Path(__file__).parent.parent / ".env"
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
from ui_input import click_app, key_combo, type_text
from smoke_helpers import (
    WINDOW_W, WINDOW_H, CHROME_TOTAL_H, PAD_MD,
    ok, fail,
    pixel_rgb, scan_for_high_green,
    menu_slot_center_x, menu_slot_x, menu_bar_center_y, dropdown_item_center_y,
    room_center,
)

# ---------------------------------------------------------------------------
# Play View layout constants
# ---------------------------------------------------------------------------

PANEL_CHAT_W = 440
CONTENT_H    = WINDOW_H - CHROME_TOTAL_H      # 830
ORIGIN_X     = PANEL_CHAT_W + PAD_MD          # 452 — grid drawing origin x
ORIGIN_Y     = PAD_MD                         # 12  — grid drawing origin y

# Chat input widget and Send ("Draft") button centres in Arcade coordinates
# Panel: x=0, w=440.  input_w = 440 - PAD_SM - 4 - 76 - PAD_SM = 344
# btn_x = PAD_SM + input_w + 4 = 356;  button 76×38, base at y=34
CHAT_INPUT_X = 8 + 344 / 2                  # 180 — centre of UIInputText
CHAT_INPUT_Y = 34 + 112 / 2                 # 90  — centre of UIInputText
CHAT_SEND_X  = 356 + 76 / 2                 # 394 — centre of Send ("Draft") button
CHAT_SEND_Y  = 34 + 38 / 2                  # 53  — centre of Send button

_INPUT_AREA_H = 160   # from chat_panel.py — height of the input region at bottom

# ---------------------------------------------------------------------------
# File hygiene — paths the test may touch
# ---------------------------------------------------------------------------

_DUNGEON_NAME = "Tomb of the Forgotten King"   # dungeon.meta.title


def _dungeons_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA env var not set")
    return Path(local_app_data) / "DungeonDaddy" / "dungeons"


def _test_paths(dungeons_dir: Path) -> dict[str, Path]:
    """Paths this smoke test may create, keyed by label."""
    mem_dir = dungeons_dir / f"{_DUNGEON_NAME}_memory"
    return {
        "dungeon_json": dungeons_dir / f"{_DUNGEON_NAME}.json",
        "session_json": dungeons_dir / f"{_DUNGEON_NAME}_session.json",
        "memory_file":  mem_dir / "level_1.md",
        "memory_dir":   mem_dir,
    }


def _take_snapshot(paths: dict[str, Path]) -> dict[str, bytes | None | bool]:
    """Record pre-test state.  Files → bytes or None; memory_dir → bool."""
    snap: dict[str, bytes | None | bool] = {}
    for label in ("dungeon_json", "session_json", "memory_file"):
        p = paths[label]
        snap[label] = p.read_bytes() if p.exists() else None
    snap["memory_dir_existed"] = paths["memory_dir"].is_dir()
    return snap


def _pre_flight_report(paths: dict[str, Path], snap: dict[str, bytes | None | bool]) -> None:
    """Warn about pre-existing files so the user knows they will be restored."""
    existing = [
        label for label in ("dungeon_json", "session_json", "memory_file")
        if snap[label] is not None
    ]
    if existing:
        print("  NOTE  Pre-existing files found — will be restored after the test:")
        for label in existing:
            print(f"          {paths[label]}")
        print()


def _restore(paths: dict[str, Path], snap: dict[str, bytes | None | bool]) -> None:
    """Restore every touched path to its pre-test state."""
    for label in ("dungeon_json", "session_json", "memory_file"):
        path = paths[label]
        prior: bytes | None = snap[label]  # type: ignore[assignment]
        if prior is None:
            if path.exists():
                path.unlink()
        else:
            path.write_bytes(prior)

    # Remove the memory directory only if the test created it from scratch
    mem_dir = paths["memory_dir"]
    if not snap["memory_dir_existed"] and mem_dir.exists():
        try:
            mem_dir.rmdir()   # succeeds only when empty
        except OSError:
            pass              # non-empty: leave it — something else owns it


# ---------------------------------------------------------------------------
# Pixel helpers
# ---------------------------------------------------------------------------

def _has_violet(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> bool:
    """Return True if a VIOLET pixel exists anywhere in the chat message area.

    VIOLET (178, 100, 232) is the 1 px stroke color for DM and system bubbles.
    Step size 2 ensures we never skip over the single-pixel outline.
    Range covers the full message area above the input region.
    """
    for y_arc in range(_INPUT_AREA_H, CONTENT_H, 2):
        for x_arc in range(15, PANEL_CHAT_W - 10, 2):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x_arc, y_arc)
            if r > 140 and b > 180 and g < 130:
                return True
    return False


def _app_alive(h: UITestHarness) -> bool:
    return h._proc is not None and h._proc.poll() is None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    failures = 0
    has_api = bool(os.environ.get("OPENAI_API_KEY"))

    print("\n=== Phase 8 Smoke Test ===\n")
    if not has_api:
        print("  NOTE  OPENAI_API_KEY not set — DM narration check skipped\n")

    dungeons_dir = _dungeons_dir()
    paths = _test_paths(dungeons_dir)
    snap  = _take_snapshot(paths)
    _pre_flight_report(paths, snap)

    try:
        with UITestHarness(tag="phase8", render_wait=4.0) as h:
            if h.window_rect is None:
                print("  FAIL  Window did not open within timeout — aborting")
                return 1

            h.pin_window()
            win_left, win_top, _, _ = h.window_rect
            print(f"  Window pinned to (0,0)\n")

            # ------------------------------------------------------------------
            # Setup: load sample dungeon → switch to Play View
            # ------------------------------------------------------------------
            print("Setup — File → Demo Dungeon to load sample dungeon")
            click_app(h.window_rect, menu_slot_center_x("File"), menu_bar_center_y())
            time.sleep(0.3)
            click_app(h.window_rect, menu_slot_center_x("File") + 40, dropdown_item_center_y(2))
            time.sleep(1.5)

            print("Setup — Play → Switch to Play")
            click_app(h.window_rect, menu_slot_center_x("Play"), menu_bar_center_y())
            time.sleep(0.4)
            click_app(h.window_rect, menu_slot_x("Play") + 80, dropdown_item_center_y(0))
            time.sleep(1.5)

            # ------------------------------------------------------------------
            # Behavior 1 — Room click: TEAL highlight + DM narration
            # ------------------------------------------------------------------
            print("Behavior 1 — Room click → TEAL highlight + DM narration")

            rx, ry = room_center(1, 4, 3, 3, ORIGIN_X, ORIGIN_Y)
            click_app(h.window_rect, rx, ry)
            time.sleep(2.0)  # let room-selection event settle

            shot = h.capture("room_click")
            pixels = h.pixels
            shot_w = h.shot_w
            print(f"  Screenshot: {shot.name}")

            has_teal = scan_for_high_green(
                pixels, shot_w, win_left, win_top,
                arcade_x=rx, arcade_y=ry,
                radius=80,
            )
            if has_teal:
                ok("TEAL highlight found near clicked room — room is selected")
            else:
                failures += fail("No TEAL pixels near room — highlight missing")

            if has_api:
                # Poll up to 3 times so slow LLM responses still pass.
                # Each wait also lets the LLM finish and re-enables the Send button
                # before we attempt /remember below.
                dm_found = False
                for attempt in range(1, 4):
                    print(f"\n  Waiting for DM narration (attempt {attempt}/3)…")
                    time.sleep(8.0)
                    shot = h.capture(f"dm_narration_{attempt}")
                    pixels = h.pixels
                    print(f"  Screenshot: {shot.name}")
                    if _has_violet(pixels, shot_w, win_left, win_top):
                        ok("VIOLET bubble found in chat — DM narration received")
                        dm_found = True
                        break
                if not dm_found:
                    failures += fail("No VIOLET bubble after 3 attempts — DM narration missing")
            else:
                # No LLM call fires, but give the app a moment to settle
                # so the Send button is ready for /remember.
                time.sleep(1.5)

            # ------------------------------------------------------------------
            # Behavior 2 — /remember command → confirmation bubble
            # ------------------------------------------------------------------
            print("\nBehavior 2 — /remember → system confirmation bubble")

            click_app(h.window_rect, CHAT_INPUT_X, CHAT_INPUT_Y)
            time.sleep(0.5)
            type_text("/remember test note")
            time.sleep(0.3)
            click_app(h.window_rect, CHAT_SEND_X, CHAT_SEND_Y)
            time.sleep(1.5)

            shot = h.capture("remember")
            pixels = h.pixels
            print(f"  Screenshot: {shot.name}")

            if _has_violet(pixels, shot_w, win_left, win_top):
                ok("VIOLET bubble found in chat — /remember confirmation appeared")
            else:
                failures += fail("No VIOLET bubble after /remember — confirmation missing")

            # ------------------------------------------------------------------
            # Behavior 3 — View → Map: Tiles
            # ------------------------------------------------------------------
            print("\nBehavior 3 — View → Map: Tiles")

            click_app(h.window_rect, menu_slot_center_x("View"), menu_bar_center_y())
            time.sleep(0.4)
            click_app(h.window_rect, menu_slot_x("View") + 50, dropdown_item_center_y(1))
            time.sleep(0.8)

            shot = h.capture("map_tiles")
            print(f"  Screenshot: {shot.name}")

            if _app_alive(h):
                ok("App alive after Map: Tiles switch — no crash")
            else:
                failures += fail("App crashed after Map: Tiles switch")

            # ------------------------------------------------------------------
            # Behavior 4 — View → Map: Graph
            # ------------------------------------------------------------------
            print("\nBehavior 4 — View → Map: Graph")

            click_app(h.window_rect, menu_slot_center_x("View"), menu_bar_center_y())
            time.sleep(0.4)
            click_app(h.window_rect, menu_slot_x("View") + 50, dropdown_item_center_y(2))
            time.sleep(0.8)

            shot = h.capture("map_graph")
            print(f"  Screenshot: {shot.name}")

            if _app_alive(h):
                ok("App alive after Map: Graph switch — no crash")
            else:
                failures += fail("App crashed after Map: Graph switch")

            # ------------------------------------------------------------------
            # Behavior 5 — File → Save
            # ------------------------------------------------------------------
            print("\nBehavior 5 — File → Save")

            click_app(h.window_rect, menu_slot_center_x("File"), menu_bar_center_y())
            time.sleep(0.4)
            click_app(h.window_rect, menu_slot_x("File") + 50, dropdown_item_center_y(2))
            time.sleep(0.5)

            shot = h.capture("after_save")
            print(f"  Screenshot: {shot.name}")

            if _app_alive(h):
                ok("App alive after File → Save — no crash")
            else:
                failures += fail("App crashed after File → Save")

    finally:
        _restore(paths, snap)
        print("\n  Cleanup done — all test-created files restored to pre-test state")

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
