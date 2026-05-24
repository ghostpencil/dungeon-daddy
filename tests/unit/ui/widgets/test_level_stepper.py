"""Tests for LevelStepper — setup, state methods, draw."""
from __future__ import annotations

from unittest.mock import MagicMock

import arcade
import arcade.gui
import pytest

from dungeon_daddy.ui.widgets.level_stepper import LevelStepper


@pytest.fixture
def cb():
    return MagicMock()


@pytest.fixture
def stepper(cb):
    return LevelStepper(cb)


@pytest.fixture
def btn_mocks(monkeypatch):
    """Replace UIFlatButton with two distinct mocks; return (up, down)."""
    up = MagicMock()
    down = MagicMock()
    cls = MagicMock()
    cls.side_effect = [up, down]
    monkeypatch.setattr(arcade.gui, "UIFlatButton", cls)
    return up, down


@pytest.fixture
def arcade_draw(monkeypatch):
    """Suppress arcade draw calls; return (text_mock, circle_mock)."""
    text_mock = MagicMock()
    circle_mock = MagicMock()
    monkeypatch.setattr(arcade, "draw_text", text_mock)
    monkeypatch.setattr(arcade, "draw_circle_outline", circle_mock)
    return text_mock, circle_mock


# ---------------------------------------------------------------------------
# setup()
# ---------------------------------------------------------------------------

class TestSetup:
    def test_stores_layout_bounds(self, stepper, btn_mocks):
        stepper.setup(MagicMock(), x=10.0, y=20.0, w=50.0, h=200.0)
        assert (stepper._x, stepper._y, stepper._w, stepper._h) == (10.0, 20.0, 50.0, 200.0)

    def test_adds_both_buttons_to_manager(self, stepper, btn_mocks):
        mgr = MagicMock()
        stepper.setup(mgr, 0.0, 0.0, 50.0, 200.0)
        assert mgr.add.call_count == 2

    def test_up_button_click_fires_minus_one(self, stepper, btn_mocks, cb):
        up_mock, _ = btn_mocks
        stepper.setup(MagicMock(), 0.0, 0.0, 50.0, 200.0)
        on_click = up_mock.event.call_args.args[0]
        on_click(None)
        cb.assert_called_once_with(-1)

    def test_down_button_click_fires_plus_one(self, stepper, btn_mocks, cb):
        _, down_mock = btn_mocks
        stepper.setup(MagicMock(), 0.0, 0.0, 50.0, 200.0)
        on_click = down_mock.event.call_args.args[0]
        on_click(None)
        cb.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# set_label / set_*_enabled
# ---------------------------------------------------------------------------

class TestState:
    def test_set_label_updates_label(self, stepper):
        stepper.set_label("Level 3")
        assert stepper._label == "Level 3"

    def test_set_up_enabled_true_clears_disabled(self, stepper, btn_mocks):
        up_mock, _ = btn_mocks
        stepper.setup(MagicMock(), 0.0, 0.0, 50.0, 200.0)
        stepper.set_up_enabled(True)
        assert up_mock.disabled is False

    def test_set_up_enabled_false_sets_disabled(self, stepper, btn_mocks):
        up_mock, _ = btn_mocks
        stepper.setup(MagicMock(), 0.0, 0.0, 50.0, 200.0)
        stepper.set_up_enabled(False)
        assert up_mock.disabled is True

    def test_set_down_enabled_false_sets_disabled(self, stepper, btn_mocks):
        _, down_mock = btn_mocks
        stepper.setup(MagicMock(), 0.0, 0.0, 50.0, 200.0)
        stepper.set_down_enabled(False)
        assert down_mock.disabled is True

    def test_set_up_enabled_before_setup_does_not_raise(self, stepper):
        stepper.set_up_enabled(False)
        assert stepper._up_btn is None

    def test_set_down_enabled_before_setup_does_not_raise(self, stepper):
        stepper.set_down_enabled(False)
        assert stepper._down_btn is None


# ---------------------------------------------------------------------------
# draw()
# ---------------------------------------------------------------------------

class TestDraw:
    def test_draws_label_at_widget_centre(self, stepper, arcade_draw):
        text_mock, _ = arcade_draw
        stepper._x, stepper._y, stepper._w, stepper._h = 0.0, 0.0, 50.0, 200.0
        stepper._label = "Level 2"
        stepper.draw()
        first_call = text_mock.call_args_list[0]
        assert first_call.args[0] == "Level 2"
        assert first_call.args[1] == 25.0   # cx = 0 + 50/2
        assert first_call.args[2] == 100.0  # label_y = 0 + 200/2

    def test_draws_compass_rose_circle(self, stepper, arcade_draw):
        _, circle_mock = arcade_draw
        stepper._x, stepper._y, stepper._w, stepper._h = 0.0, 0.0, 50.0, 200.0
        stepper.draw()
        circle_mock.assert_called_once()
