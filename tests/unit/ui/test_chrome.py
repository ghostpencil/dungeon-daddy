"""Tests for title_bar_mode_at() pill hit-test logic."""
from __future__ import annotations

from types import SimpleNamespace

from dungeon_daddy.ui.chrome import title_bar_mode_at

# ---------------------------------------------------------------------------
# title_bar_mode_at — pill hit-test
# ---------------------------------------------------------------------------
#
# Window 1000 × 800:
#   CHROME_MENUBAR_HEIGHT=0 → bar_top=800, bar_bottom=756, bar_mid=778
#   _PILL_W=90, _PILL_H=22, _PILL_GAP=8, PAD_MD=12
#   total_w = 1*90 + 0*8 = 90; right_edge = 1000-12 = 988
#   library (idx=0): cx = 988-90 + 0 + 45 = 943  → left=898, right=988

_W1000 = SimpleNamespace(width=1000, height=800)


class TestTitleBarModeAt:
    def test_click_library_pill_returns_library(self):
        assert title_bar_mode_at(943, 778, _W1000) == "library"

    def test_click_library_pill_left_edge_returns_library(self):
        assert title_bar_mode_at(899, 778, _W1000) == "library"

    def test_click_right_edge_returns_library(self):
        assert title_bar_mode_at(987, 778, _W1000) == "library"

    def test_click_left_of_pill_returns_none(self):
        assert title_bar_mode_at(796, 778, _W1000) is None

    def test_click_far_left_returns_none(self):
        assert title_bar_mode_at(400, 778, _W1000) is None

    def test_click_below_title_bar_returns_none(self):
        # title bar bottom = 756; y=720 is below it
        assert title_bar_mode_at(943, 720, _W1000) is None
