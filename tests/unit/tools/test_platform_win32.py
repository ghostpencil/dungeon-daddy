import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "tools"))

import platform_win32


def test_get_dpi_scale_system_100_percent():
    with patch("platform_win32._GetDpiForSystem", return_value=96):
        assert platform_win32.get_dpi_scale() == 1.0


def test_get_dpi_scale_system_125_percent():
    with patch("platform_win32._GetDpiForSystem", return_value=120):
        assert platform_win32.get_dpi_scale() == 1.25


def test_get_dpi_scale_hwnd_path():
    with patch("platform_win32._GetDpiForWindow", return_value=144) as mock_fn:
        assert platform_win32.get_dpi_scale(hwnd=12345) == 1.5
        mock_fn.assert_called_once_with(12345)
