"""
Screenshot watcher — captures the screen every INTERVAL seconds.
Saves PNGs to tools/screenshots/ with timestamps.
Writes its PID to tools/.screenshot.pid so stop_screenshots.py can kill it.

Usage:
    python tools/screenshot_start.py           # default 2-second interval
    python tools/screenshot_start.py 5         # 5-second interval
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

from mss import MSS

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

INTERVAL = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0

SCRIPT_DIR = Path(__file__).parent
SCREENSHOTS_DIR = SCRIPT_DIR / "screenshots"
PID_FILE = SCRIPT_DIR / ".screenshot.pid"
STOP_FILE = SCRIPT_DIR / ".screenshot.stop"

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Remove any stale stop-file from a previous run
STOP_FILE.unlink(missing_ok=True)

# Write our PID so stop_screenshots.py can find us
PID_FILE.write_text(str(os.getpid()))

print(f"[screenshot_start] PID {os.getpid()} — capturing every {INTERVAL}s")
print(f"[screenshot_start] Saving to {SCREENSHOTS_DIR.resolve()}")
print("[screenshot_start] Run tools/screenshot_stop.py (or Ctrl-C) to stop.")

# ---------------------------------------------------------------------------
# Capture loop
# ---------------------------------------------------------------------------

count = 0
try:
    with MSS() as sct:
        monitor = sct.monitors[1]   # primary monitor (index 0 = all monitors combined)
        while not STOP_FILE.exists():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = SCREENSHOTS_DIR / f"screenshot_{ts}_{count:04d}.png"
            sct.shot(mon=1, output=str(filename))
            count += 1
            print(f"[screenshot_start] Saved {filename.name}")
            time.sleep(INTERVAL)
finally:
    PID_FILE.unlink(missing_ok=True)
    STOP_FILE.unlink(missing_ok=True)
    print(f"[screenshot_start] Stopped after {count} screenshot(s).")
