import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "tools"))

import pytest


def test_get_platform_returns_stub_on_non_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    import platform_host
    importlib.reload(platform_host)
    plat = platform_host.get_platform()
    with pytest.raises(NotImplementedError, match="Contribute"):
        plat.find_window("Dungeon Daddy")


def test_get_platform_returns_win32_on_windows():
    import platform_host
    import platform_win32
    importlib.reload(platform_host)
    assert platform_host.get_platform() is platform_win32
