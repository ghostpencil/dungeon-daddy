"""Platform backend selector — returns win32 or stub based on sys.platform."""
from __future__ import annotations

import sys


def get_platform():
    """Return the platform backend module for the current OS."""
    if sys.platform == "win32":
        import platform_win32
        return platform_win32
    import platform_stub
    return platform_stub
