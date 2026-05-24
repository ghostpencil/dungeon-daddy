"""
Phase 12 smoke test — Context Engineering.

Behaviors verified:
  1. "✦ context" chip absent in chat header when no context docs exist
  2. "✦ context" chip present after all 3 context docs are seeded on disk
     and the dungeon is reloaded (File→Demo Dungeon triggers _refresh_context_doc_statuses)

Usage:
    cd tools && python smoke_test_phase12.py

Chip geometry:
  ChatPanel header: x=240, w=840, h=830, header_h=38
  Chip center: arcade (x + w - 90, content_h - header_h/2) = (990, 811)
  draw_chip uses teal color (TEAL text on TEAL_DIM bg) — width=80, height=20
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
from ui_input import click_app
from smoke_helpers import (
    WINDOW_W, WINDOW_H, CHROME_TOTAL_H,
    ok, fail,
    pixel_rgb,
    menu_slot_center_x, menu_bar_center_y, dropdown_item_center_y,
)

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

PANEL_TREE_W      = 240
PANEL_INSPECTOR_W = 320
CONTENT_H         = WINDOW_H - CHROME_TOTAL_H   # 830
HEADER_H          = 38

_CHAT_X = PANEL_TREE_W                                       # 240
_CHAT_W = WINDOW_W - PANEL_TREE_W - PANEL_INSPECTOR_W       # 840

# "✦ context" chip center (arcade coordinates)
# draw_chip("✦ context", x + w - 90, y + h - HEADER_H/2, "teal")
_CHIP_CX = _CHAT_X + _CHAT_W - 90               # 990
_CHIP_CY = CONTENT_H - HEADER_H / 2             # 811.0

# Scan region ±50px wide, ±14px tall (chip is 80×20 px)
_CHIP_X0 = int(_CHIP_CX - 50)                   # 940
_CHIP_X1 = int(_CHIP_CX + 50)                   # 1040
_CHIP_Y0 = int(_CHIP_CY - 14)                   # 797
_CHIP_Y1 = int(_CHIP_CY + 14)                   # 825


# ---------------------------------------------------------------------------
# Context doc directory helpers
# ---------------------------------------------------------------------------

def _context_doc_dir() -> pathlib.Path:
    from platformdirs import user_data_path
    return (
        user_data_path("DungeonDaddy", appauthor=False)
        / "dungeons"
        / "Tomb of the Forgotten King"
    )


def _clean_context_docs() -> None:
    d = _context_doc_dir()
    for name in ("setting.md", "party.md"):
        p = d / name
        if p.exists():
            p.unlink()
            print(f"  Cleaned: {p.name}")
    for p in d.glob("level_*_design.md"):
        p.unlink()
        print(f"  Cleaned: {p.name}")


def _seed_context_docs() -> None:
    """Write all 3 context docs so _refresh_context_doc_statuses sees them all."""
    d = _context_doc_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "setting.md").write_text(
        "# Dungeon Setting\n\n"
        "A vast undead tomb beneath the blighted moors, carved by the forgotten king.",
        encoding="utf-8",
    )
    (d / "party.md").write_text(
        "# Party\n\n"
        "Four adventurers: a fighter, a rogue, a wizard, and a cleric. Seeking treasure.",
        encoding="utf-8",
    )
    (d / "level_1_design.md").write_text(
        "# Level 1 Design\n\n"
        "Entrance hall with skeletal guards. Two loops: patrol route and treasure vault.",
        encoding="utf-8",
    )
    print("  Seeded: setting.md, party.md, level_1_design.md")


# ---------------------------------------------------------------------------
# Pixel helpers
# ---------------------------------------------------------------------------

def _scan_context_chip(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> bool:
    """Return True if TEAL is found in the '✦ context' chip region."""
    for y in range(_CHIP_Y0, _CHIP_Y1, 2):
        for x in range(_CHIP_X0, _CHIP_X1, 3):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x, y)
            if g > 180 and b > 140 and r < 100:
                return True
    return False


def _load_demo_dungeon(h: UITestHarness) -> None:
    """Open File menu and click Demo Dungeon (index 2)."""
    rect = h.window_rect
    click_app(rect, menu_slot_center_x("File"), menu_bar_center_y())
    time.sleep(0.3)
    click_app(rect, menu_slot_center_x("File") + 40, dropdown_item_center_y(2))


def _app_alive(h: UITestHarness) -> bool:
    return h._proc is not None and h._proc.poll() is None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    failures = 0
    print("\n=== Phase 12 Smoke Test ===\n")

    print("Setup — cleaning pre-existing context docs")
    _clean_context_docs()

    with UITestHarness(tag="phase12", render_wait=4.0) as h:
        if h.window_rect is None:
            print("  FAIL  Window did not open within timeout — aborting")
            return 1

        h.pin_window()
        win_left, win_top, _win_right, _win_bottom = h.window_rect
        print(f"  Window pinned to (0,0); win_top={win_top}\n")

        # ------------------------------------------------------------------
        # Setup: load sample dungeon via Ctrl+O
        # ------------------------------------------------------------------
        print("Setup — File → Demo Dungeon (no docs exist yet)")
        _load_demo_dungeon(h)
        time.sleep(1.5)

        if not _app_alive(h):
            return fail("App crashed during dungeon load — aborting")

        # ------------------------------------------------------------------
        # Behavior 1 — chip absent when no context docs exist
        # ------------------------------------------------------------------
        print("Behavior 1 — No context docs → '✦ context' chip absent")

        shot = h.capture("b1_no_docs")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        if not _scan_context_chip(pixels, shot_w, win_left, win_top):
            ok("No TEAL in chip region — correct, docs absent")
        else:
            failures += fail("TEAL chip found before any docs were created (unexpected)")

        if _app_alive(h):
            ok("App alive after first load")
        else:
            return failures + fail("App crashed — aborting")

        # ------------------------------------------------------------------
        # Behavior 2 — chip present after seeding all 3 docs and reloading
        # ------------------------------------------------------------------
        print("\nBehavior 2 — Seed all 3 docs → reload → '✦ context' chip present")

        print("  Writing context docs to disk...")
        _seed_context_docs()

        print("  File → Demo Dungeon to reload (_refresh_context_doc_statuses fires on load_dungeon)")
        _load_demo_dungeon(h)
        time.sleep(1.5)

        if not _app_alive(h):
            return failures + fail("App crashed after reload — aborting")

        shot = h.capture("b2_docs_seeded")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        if _scan_context_chip(pixels, shot_w, win_left, win_top):
            ok("TEAL '✦ context' chip found in chat header — all 3 docs loaded")
        else:
            failures += fail("No TEAL chip after seeding all 3 docs (chip may not be rendering)")

        if _app_alive(h):
            ok("App alive after reload with seeded docs")
        else:
            return failures + fail("App crashed after reload — aborting")

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
