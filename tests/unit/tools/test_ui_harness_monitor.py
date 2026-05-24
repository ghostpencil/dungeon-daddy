import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "tools"))

import pytest
import ui_harness
from ui_harness import UITestHarness, _monitor_for_rect

# Synthetic two-monitor layout (side by side, 1920×1080 each)
_M_ALL = {"left": 0,    "top": 0, "width": 3840, "height": 1080}
_M1    = {"left": 0,    "top": 0, "width": 1920, "height": 1080}
_M2    = {"left": 1920, "top": 0, "width": 1920, "height": 1080}


class _FakeSct:
    monitors = [_M_ALL, _M1, _M2]


def test_monitor_for_rect_fully_on_m1():
    assert _monitor_for_rect((100, 50, 1500, 1000), _FakeSct()) is _M1


def test_monitor_for_rect_fully_on_m2():
    assert _monitor_for_rect((2000, 50, 3500, 1000), _FakeSct()) is _M2


@pytest.mark.parametrize("rect,expected_mon", [
    # overlap M1: 1820×950=1_729_000  overlap M2: 80×950=76_000  → M1 wins
    ((100,  50, 2000, 1000), _M1),
    # overlap M1: 120×950=114_000  overlap M2: 1580×950=1_501_000  → M2 wins
    ((1800, 50, 3500, 1000), _M2),
])
def test_monitor_for_rect_straddling(rect, expected_mon):
    assert _monitor_for_rect(rect, _FakeSct()) is expected_mon


def test_monitor_for_rect_off_screen_warns_and_falls_back():
    with pytest.warns(UserWarning, match="overlap"):
        result = _monitor_for_rect((5000, 50, 6400, 1000), _FakeSct())
    assert result is _M1


def test_monitor_for_rect_single_monitor():
    class _Single:
        monitors = [_M_ALL, _M1]

    assert _monitor_for_rect((100, 50, 1400, 950), _Single()) is _M1


def test_refresh_window_rect_updates_monitor():
    fake_monitor = {"left": 1920, "top": 0, "width": 1920, "height": 1080}

    with patch("ui_harness.mss.MSS") as mock_mss_cls, \
         patch("ui_harness._monitor_for_rect", return_value=fake_monitor) as mock_mfr, \
         patch.object(UITestHarness, "_find_window_rect",
                      return_value=(1950, 50, 3350, 950)):

        mock_sct = MagicMock()
        mock_mss_cls.return_value.__enter__ = lambda s: mock_sct
        mock_mss_cls.return_value.__exit__  = MagicMock(return_value=False)

        h = UITestHarness.__new__(UITestHarness)
        h.window_rect = None
        h._monitor    = None
        h.refresh_window_rect()

        mock_mfr.assert_called_once_with((1950, 50, 3350, 950), mock_sct)
        assert h._monitor is fake_monitor
