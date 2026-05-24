"""Unit tests for MapPanel pan-tool state machine.

No arcade display needed — setup() is never called; only __init__ state is tested.
"""
from __future__ import annotations

import arcade

from dungeon_daddy.ui.panels.map_panel import MapPanel


def _panel() -> MapPanel:
    return MapPanel(on_level_change=lambda _: None)


def _panel_with_bounds(x: float = 440.0, y: float = 0.0, w: float = 1000.0, h: float = 700.0) -> MapPanel:
    """Panel with bounds set so viewport checks are meaningful."""
    p = MapPanel(on_level_change=lambda _: None)
    p._x, p._y, p._w, p._h = x, y, w, h
    return p


# ---------------------------------------------------------------------------
# Tool selection state
# ---------------------------------------------------------------------------

def test_default_tool_is_select():
    assert _panel().active_tool == "select"


def test_select_tool_press_returns_false():
    p = _panel_with_bounds()
    p._active_tool = "select"
    assert p.handle_mouse_press(600, 300, arcade.MOUSE_BUTTON_LEFT) is False


def test_pan_tool_press_inside_viewport_returns_true():
    p = _panel_with_bounds()
    p._active_tool = "pan"
    assert p.handle_mouse_press(600, 300, arcade.MOUSE_BUTTON_LEFT) is True


def test_pan_tool_press_inside_viewport_starts_panning():
    p = _panel_with_bounds()
    p._active_tool = "pan"
    p.handle_mouse_press(600, 300, arcade.MOUSE_BUTTON_LEFT)
    assert p._is_panning is True


def test_pan_press_outside_viewport_left_returns_false():
    """Click in the chat panel area (x < panel x) must not start panning."""
    p = _panel_with_bounds(x=440.0)
    p._active_tool = "pan"
    result = p.handle_mouse_press(100, 300, arcade.MOUSE_BUTTON_LEFT)
    assert result is False
    assert p._is_panning is False


def test_pan_press_outside_viewport_right_returns_false():
    """Click inside the stepper rail must not start panning."""
    p = _panel_with_bounds(x=440.0, w=1000.0)
    from dungeon_daddy.ui.theme import PANEL_STEPPER_WIDTH
    # x inside stepper rail: beyond (x + w - PANEL_STEPPER_WIDTH)
    stepper_x = 440.0 + 1000.0 - PANEL_STEPPER_WIDTH + 5
    p._active_tool = "pan"
    result = p.handle_mouse_press(stepper_x, 300, arcade.MOUSE_BUTTON_LEFT)
    assert result is False
    assert p._is_panning is False


def test_pan_press_outside_viewport_top_returns_false():
    """Click above the panel height must not start panning."""
    p = _panel_with_bounds(y=0.0, h=700.0)
    p._active_tool = "pan"
    # y above panel top: outside viewport
    above_panel_y = 700.0 + 5
    result = p.handle_mouse_press(600, above_panel_y, arcade.MOUSE_BUTTON_LEFT)
    assert result is False
    assert p._is_panning is False


def test_non_left_button_does_not_start_pan():
    p = _panel_with_bounds()
    p._active_tool = "pan"
    result = p.handle_mouse_press(600, 300, arcade.MOUSE_BUTTON_RIGHT)
    assert result is False
    assert p._is_panning is False


# ---------------------------------------------------------------------------
# Drag — offset accumulation
# ---------------------------------------------------------------------------

def test_drag_accumulates_offset_while_panning():
    p = _panel()
    p._active_tool = "pan"
    p._is_panning = True
    p.handle_mouse_drag(110, 115, 10, 15, arcade.MOUSE_BUTTON_LEFT)
    assert p.pan_offset == (10.0, 15.0)


def test_drag_accumulates_across_multiple_events():
    p = _panel()
    p._active_tool = "pan"
    p._is_panning = True
    p.handle_mouse_drag(0, 0, 5, 3, arcade.MOUSE_BUTTON_LEFT)
    p.handle_mouse_drag(0, 0, -2, 7, arcade.MOUSE_BUTTON_LEFT)
    assert p.pan_offset == (3.0, 10.0)


def test_drag_no_effect_when_not_panning():
    p = _panel()
    p._active_tool = "pan"
    p._is_panning = False
    p.handle_mouse_drag(110, 115, 10, 15, arcade.MOUSE_BUTTON_LEFT)
    assert p.pan_offset == (0.0, 0.0)


def test_drag_no_effect_in_select_mode():
    p = _panel()
    p._active_tool = "select"
    p._is_panning = True  # shouldn't happen, but guard anyway
    p.handle_mouse_drag(110, 115, 10, 15, arcade.MOUSE_BUTTON_LEFT)
    assert p.pan_offset == (0.0, 0.0)


# ---------------------------------------------------------------------------
# Release
# ---------------------------------------------------------------------------

def test_release_stops_panning():
    p = _panel()
    p._is_panning = True
    p.handle_mouse_release(0, 0, arcade.MOUSE_BUTTON_LEFT)
    assert p._is_panning is False


def test_release_right_button_does_not_stop_panning():
    p = _panel()
    p._is_panning = True
    p.handle_mouse_release(0, 0, arcade.MOUSE_BUTTON_RIGHT)
    assert p._is_panning is True
