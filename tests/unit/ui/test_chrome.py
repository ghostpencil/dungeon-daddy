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
#   total_w = 4*90 + 3*8 = 384; right_edge = 1000-12 = 988
#   library (idx=0): cx = 988-384 + 0*98 + 45 = 649  → left=604, right=694
#   design  (idx=1): cx = 988-384 + 1*98 + 45 = 747  → left=702, right=792
#   campaign(idx=2): cx = 988-384 + 2*98 + 45 = 845  → left=800, right=890
#   play    (idx=3): cx = 988-384 + 3*98 + 45 = 943  → left=898, right=988

_W1000 = SimpleNamespace(width=1000, height=800)


class TestTitleBarModeAt:
    def test_click_library_pill_returns_library(self):
        assert title_bar_mode_at(649, 778, _W1000) == "library"

    def test_click_design_pill_returns_design(self):
        assert title_bar_mode_at(747, 778, _W1000) == "design"

    def test_click_campaign_pill_returns_campaign(self):
        assert title_bar_mode_at(845, 778, _W1000) == "campaign"

    def test_click_play_pill_returns_play(self):
        assert title_bar_mode_at(943, 778, _W1000) == "play"

    def test_click_between_pills_returns_none(self):
        # x=796 is between design (right=792) and campaign (left=800)
        assert title_bar_mode_at(796, 778, _W1000) is None

    def test_click_left_of_pills_returns_none(self):
        assert title_bar_mode_at(400, 778, _W1000) is None

    def test_click_below_title_bar_returns_none(self):
        # title bar bottom = 756; y=720 is below it
        assert title_bar_mode_at(747, 720, _W1000) is None
