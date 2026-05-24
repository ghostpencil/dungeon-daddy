"""
Stop the running screenshot watcher.

Creates the stop sentinel file that screenshot_start.py polls for.
Falls back to killing the process by PID if it does not exit within
GRACE_PERIOD seconds (e.g. the process is blocked on sleep).

Usage:
    python tools/screenshot_stop.py
"""
from __future__ import annotations

import ctypes
import os
import signal
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PID_FILE = SCRIPT_DIR / ".screenshot.pid"
STOP_FILE = SCRIPT_DIR / ".screenshot.stop"
GRACE_PERIOD = 6.0


# ---------------------------------------------------------------------------
# Cross-platform process liveness check
# ---------------------------------------------------------------------------

def _is_alive(pid: int) -> bool:
    """Return True if the process with this PID is still running."""
    if sys.platform == "win32":
        # On Windows, os.kill(pid, 0) is not reliable.
        # OpenProcess with SYNCHRONIZE (0x00100000) returns NULL if not alive.
        SYNCHRONIZE = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        # A handle can open on a zombie/exited process — check exit code too
        STILL_ACTIVE = 259
        PROCESS_QUERY_INFO = 0x00000400
        h2 = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFO, False, pid)
        if not h2:
            return False
        code = ctypes.c_ulong(0)
        ctypes.windll.kernel32.GetExitCodeProcess(h2, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h2)
        return code.value == STILL_ACTIVE
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True   # exists but we can't signal it


def _force_kill(pid: int) -> None:
    """Force-terminate a process by PID."""
    if sys.platform == "win32":
        PROCESS_TERMINATE = 0x0001
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
        if handle:
            ctypes.windll.kernel32.TerminateProcess(handle, 1)
            ctypes.windll.kernel32.CloseHandle(handle)
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


# ---------------------------------------------------------------------------

if not PID_FILE.exists():
    print("[screenshot_stop] No watcher is running (no PID file found).")
    sys.exit(0)

pid = int(PID_FILE.read_text().strip())

if not _is_alive(pid):
    print(f"[screenshot_stop] PID {pid} is not running — cleaning up stale files.")
    PID_FILE.unlink(missing_ok=True)
    STOP_FILE.unlink(missing_ok=True)
    sys.exit(0)

print(f"[screenshot_stop] Signalling watcher (PID {pid}) to stop ...")

# Drop the sentinel file — the watcher polls for this between sleeps
STOP_FILE.touch()

# Wait gracefully for the process to exit on its own
deadline = time.monotonic() + GRACE_PERIOD
while time.monotonic() < deadline:
    if not _is_alive(pid):
        print("[screenshot_stop] Watcher exited cleanly.")
        break
    time.sleep(0.25)
else:
    print(f"[screenshot_stop] Grace period elapsed; force-killing PID {pid}.")
    _force_kill(pid)

# Clean up any leftover files
PID_FILE.unlink(missing_ok=True)
STOP_FILE.unlink(missing_ok=True)
print("[screenshot_stop] Done.")
