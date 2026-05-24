"""Windows platform backend — wraps all ctypes.windll calls for the smoke-test tools."""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import time

_GetDpiForSystem = ctypes.windll.user32.GetDpiForSystem
_GetDpiForWindow = ctypes.windll.user32.GetDpiForWindow

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP   = 0x0004
MOUSEEVENTF_WHEEL    = 0x0800
WHEEL_DELTA          = 120
KEYEVENTF_KEYUP      = 0x0002
KEYEVENTF_UNICODE    = 0x0004
INPUT_KEYBOARD       = 1


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         ctypes.c_ushort),
        ("wScan",       ctypes.c_ushort),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT), ("_pad", ctypes.c_byte * 28)]
    _anonymous_ = ("_u",)
    _fields_ = [("type", ctypes.c_ulong), ("_u", _U)]


def set_dpi_awareness() -> None:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)


def find_window(title: str) -> int:
    return ctypes.windll.user32.FindWindowW(None, title)


def get_window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    rect = ctypes.wintypes.RECT()
    if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def get_system_metrics(index: int) -> int:
    return ctypes.windll.user32.GetSystemMetrics(index)


def set_window_pos(hwnd: int, x: int, y: int, flags: int) -> None:
    ctypes.windll.user32.SetWindowPos(hwnd, 0, x, y, 0, 0, flags)


def post_message(hwnd: int, msg: int, wparam: int, lparam: int) -> None:
    ctypes.windll.user32.PostMessageW(hwnd, msg, wparam, lparam)


def set_cursor_pos(x: int, y: int) -> None:
    ctypes.windll.user32.SetCursorPos(x, y)


def mouse_event(flags: int, x: int, y: int, data: int, extra: int) -> None:
    ctypes.windll.user32.mouse_event(flags, x, y, data, extra)


def get_dpi_scale(hwnd: int = 0) -> float:
    if hwnd:
        dpi = _GetDpiForWindow(hwnd)
    else:
        dpi = _GetDpiForSystem()
    return dpi / 96.0


def send_click(sx: int, sy: int, delay: float = 0.05) -> None:
    ctypes.windll.user32.SetCursorPos(sx, sy)
    time.sleep(0.05)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, sx, sy, 0, 0)
    time.sleep(delay)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, sx, sy, 0, 0)


def send_key_combo(*vks: int) -> None:
    for vk in vks:
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    for vk in reversed(vks):
        ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def send_scroll(sx: int, sy: int, clicks: int = 3) -> None:
    ctypes.windll.user32.SetCursorPos(sx, sy)
    time.sleep(0.05)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, sx, sy, clicks * WHEEL_DELTA, 0)


def send_text(text: str, delay: float = 0.02) -> None:
    for ch in text:
        scan = ord(ch)
        for flags in (KEYEVENTF_UNICODE, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP):
            inp = _INPUT(type=INPUT_KEYBOARD)
            inp.ki = _KEYBDINPUT(wVk=0, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        time.sleep(delay)
