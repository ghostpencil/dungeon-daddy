import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "tools"))

import dpi


def test_scale_returns_1_on_non_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert dpi.scale() == 1.0


def test_scale_calls_get_dpi_scale_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    with patch("dpi.get_dpi_scale", return_value=1.25):
        assert dpi.scale() == 1.25
