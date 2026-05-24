"""
Stop the running Dungeon Daddy Arcade window.

Finds the window by title, sends WM_CLOSE for a graceful shutdown,
and falls back to taskkill if it does not close within GRACE_PERIOD seconds.

Usage:
    python tools/arcade_stop.py
    python tools/arcade_stop.py "Dungeon Daddy"   # optional title override
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import subprocess
import sys
import time

WINDOW_TITLE = sys.argv[1] if len(sys.argv) > 1 else "Dungeon Daddy"
GRACE_PERIOD = 5.0
WM_CLOSE = 0x0010


def _find_hwnd(title: str) -> int | None:
    hwnd = ctypes.windll.user32.FindWindowW(None, title)
    return hwnd if hwnd else None


def _window_exists(title: str) -> bool:
    return _find_hwnd(title) is not None


# ---------------------------------------------------------------------------

hwnd = _find_hwnd(WINDOW_TITLE)
if hwnd is None:
    print(f"[arcade_stop] No window titled '{WINDOW_TITLE}' found — nothing to stop.")
    sys.exit(0)

print(f"[arcade_stop] Found '{WINDOW_TITLE}' (hwnd={hwnd}) — sending WM_CLOSE ...")
ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

# Wait for the window to disappear
deadline = time.monotonic() + GRACE_PERIOD
while time.monotonic() < deadline:
    if not _window_exists(WINDOW_TITLE):
        print("[arcade_stop] Window closed cleanly.")
        sys.exit(0)
    time.sleep(0.2)

# Still open — force-kill via taskkill
print(f"[arcade_stop] Window did not close after {GRACE_PERIOD}s — force-killing via taskkill ...")
result = subprocess.run(
    ["taskkill", "/F", "/FI", f"WINDOWTITLE eq {WINDOW_TITLE}"],
    capture_output=True, text=True,
)
if result.returncode == 0:
    print("[arcade_stop] Process terminated.")
else:
    print(f"[arcade_stop] taskkill output: {result.stdout.strip()} {result.stderr.strip()}")

sys.exit(0)
