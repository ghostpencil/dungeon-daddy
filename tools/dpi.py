"""DPI scale helpers for Dungeon Daddy smoke tests."""
from __future__ import annotations

import sys

import platform_host as _ph


def get_dpi_scale(hwnd: int = 0) -> float:
    """Return the DPI scale factor for a window (or the system if hwnd=0)."""
    return _ph.get_platform().get_dpi_scale(hwnd)


def scale(hwnd: int = 0) -> float:
    """Return the DPI scale factor; returns 1.0 on non-Windows."""
    if sys.platform != "win32":
        return 1.0
    return get_dpi_scale(hwnd)
