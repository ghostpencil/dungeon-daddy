"""
B3 smoke test — shift+click adds sub-loop.
Run standalone: python tools/run_b3_test.py
Leaves the app open so a screenshot can be taken afterwards.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from ui_input import (
    MOUSEEVENTF_LEFTDOWN,
    MOUSEEVENTF_LEFTUP,
    VK_CONTROL,
    VK_O,
    VK_SHIFT,
    WM_KEYDOWN,
    WM_KEYUP,
    app_to_screen,
    click_app,
    key_combo,
)

TITLE = "Dungeon Daddy"


def find_hwnd() -> int:
    return ctypes.windll.user32.FindWindowW(None, TITLE)


def get_rect(hwnd: int) -> tuple[int, int, int, int]:
    r = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


# ------------------------------------------------------------------
# Kill any existing instance
# ------------------------------------------------------------------
hwnd = find_hwnd()
if hwnd:
    print("Closing existing Dungeon Daddy window...")
    ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
    time.sleep(2.0)

# ------------------------------------------------------------------
# Launch fresh
# ------------------------------------------------------------------
print("Launching Dungeon Daddy...")
subprocess.Popen([sys.executable, "-m", "dungeon_daddy"], cwd=str(ROOT))

deadline = time.monotonic() + 15.0
while time.monotonic() < deadline:
    hwnd = find_hwnd()
    if hwnd:
        break
    time.sleep(0.25)

assert hwnd, "Window did not open in time"
print(f"Window found HWND={hwnd}, waiting for render...")
time.sleep(4.0)

# ------------------------------------------------------------------
# Pin to (0,0)
# ------------------------------------------------------------------
SWP_NOSIZE, SWP_NOZORDER = 0x0001, 0x0004
ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOZORDER)
time.sleep(0.3)
wr = get_rect(hwnd)
print(f"Window rect: {wr}")

# ------------------------------------------------------------------
# B1: load dungeon + switch to Loops tab
# ------------------------------------------------------------------
key_combo(VK_CONTROL, VK_O)
time.sleep(2.0)
click_app(wr, 1320, 776)   # Loops tab
time.sleep(0.8)

# ------------------------------------------------------------------
# B2: click pattern card (empty-state position, y=630)
# ------------------------------------------------------------------
click_app(wr, 1240, 630)   # applies main loop
time.sleep(0.8)
print("B2 done - main loop applied")

# ------------------------------------------------------------------
# B3: shift+click pattern card (with-main position, y=590)
#
# Root cause of earlier failures: pyglet tracks modifier state via
# WM_KEYDOWN messages arriving at ITS OWN message queue.  keybd_event /
# SendInput sends WM_KEYDOWN to the FOCUSED window (terminal), so pyglet
# never sees the shift key and modifiers=0 in on_mouse_press.
#
# Fix: PostMessageW(WM_KEYDOWN, VK_SHIFT) directly to DD's hwnd so
# pyglet's internal modifier tracker sees the shift key, then fire the
# real click via mouse_event (which we know reaches on_mouse_press).
# ------------------------------------------------------------------
sx, sy = app_to_screen(wr, 1240, 590)
print(f"B3 shift+click at screen ({sx}, {sy})")

kdown_lp = 0x00000001
kup_lp   = 0xC0000001

# 1. Tell pyglet shift is down (directly into DD's message queue)
ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, VK_SHIFT, kdown_lp)
time.sleep(0.08)   # let pyglet pump WM_KEYDOWN before the click arrives

# 2. Real hardware click (mouse_event reaches on_mouse_press)
ctypes.windll.user32.SetCursorPos(sx, sy)
time.sleep(0.03)
ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, sx, sy, 0, 0)
time.sleep(0.05)
ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, sx, sy, 0, 0)
time.sleep(0.03)

# 3. Release shift in pyglet
ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP, VK_SHIFT, kup_lp)

print("B3 sent - take screenshot now (app left open)")
time.sleep(1.0)
