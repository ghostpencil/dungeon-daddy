"""Tests for MapPanel.update_state()."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.ui.panels.map_panel import MapPanel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state(level_idx: int = 0) -> SessionState:
    return SessionState(dungeon_id="test", current_level_idx=level_idx)


@pytest.fixture
def panel():
    """MapPanel with its LevelStepper replaced by a MagicMock."""
    mp = MapPanel(on_level_change=lambda _: None)
    mp._stepper = MagicMock()
    return mp


# ---------------------------------------------------------------------------
# update_state()
# ---------------------------------------------------------------------------

class TestUpdateState:
    def test_stores_new_state(self, panel):
        state = _state(level_idx=2)
        panel.update_state(state, total_levels=5)
        assert panel._state is state

    def test_stepper_label_uses_one_based_index(self, panel):
        panel.update_state(_state(level_idx=2), total_levels=5)
        panel._stepper.set_label.assert_called_once_with("L3")

    def test_stepper_label_at_first_level(self, panel):
        panel.update_state(_state(level_idx=0), total_levels=3)
        panel._stepper.set_label.assert_called_once_with("L1")

    def test_up_enabled_when_not_first_level(self, panel):
        panel.update_state(_state(level_idx=1), total_levels=3)
        panel._stepper.set_up_enabled.assert_called_once_with(True)

    def test_up_disabled_at_first_level(self, panel):
        panel.update_state(_state(level_idx=0), total_levels=3)
        panel._stepper.set_up_enabled.assert_called_once_with(False)

    def test_down_enabled_when_not_last_level(self, panel):
        panel.update_state(_state(level_idx=0), total_levels=3)
        panel._stepper.set_down_enabled.assert_called_once_with(True)

    def test_down_disabled_at_last_level(self, panel):
        panel.update_state(_state(level_idx=2), total_levels=3)
        panel._stepper.set_down_enabled.assert_called_once_with(False)
