"""Tests for MapPanel zoom and variant-tab behaviour — no display required."""
from __future__ import annotations

from unittest.mock import MagicMock

import arcade
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_panel(on_variant_change=None):
    from dungeon_daddy.ui.panels.map_panel import _ZOOM_DEFAULT, _ZOOM_MAX, _ZOOM_MIN, MapPanel

    renderer = MagicMock()
    renderer.cell_px = 48
    overlay = MagicMock()
    panel = MapPanel(
        on_level_change=lambda d: None,
        renderer=renderer,
        overlay=overlay,
        on_variant_change=on_variant_change,
    )
    panel._x, panel._y, panel._w, panel._h = 440.0, 0.0, 800.0, 600.0
    return panel, _ZOOM_MIN, _ZOOM_MAX, _ZOOM_DEFAULT


def _make_level(rooms_data: list[dict]):
    from dungeon_daddy.data.models import Level, Room
    rooms = [
        Room(id=f"r{i}", num=i, name=f"Room {i}",
             x=d["x"], y=d["y"], w=d["w"], h=d["h"],
             type="hall", note="")
        for i, d in enumerate(rooms_data, 1)
    ]
    return Level(id=1, name="Test Level", summary="", ecology="", loop="",
                 width=50, height=50, entries=[], rooms=rooms, connections=[])


def _make_state():
    from dungeon_daddy.data.models import SessionState
    return SessionState(dungeon_id="test", current_level_idx=0)


# ---------------------------------------------------------------------------
# Default zoom
# ---------------------------------------------------------------------------

def test_zoom_level_default() -> None:
    panel, _, _, default = _make_panel()
    assert panel.zoom_level == pytest.approx(default)


# ---------------------------------------------------------------------------
# Mouse scroll
# ---------------------------------------------------------------------------

def test_scroll_up_increases_zoom() -> None:
    panel, _, _, _ = _make_panel()
    before = panel.zoom_level
    panel.handle_mouse_scroll(x=500.0, y=300.0, scroll_x=0, scroll_y=1)
    assert panel.zoom_level > before


def test_scroll_down_decreases_zoom() -> None:
    panel, _, _, _ = _make_panel()
    before = panel.zoom_level
    panel.handle_mouse_scroll(x=500.0, y=300.0, scroll_x=0, scroll_y=-1)
    assert panel.zoom_level < before


def test_scroll_outside_map_ignored() -> None:
    panel, _, _, default = _make_panel()
    # x=0 is in the chat panel (left of map at x=440)
    panel.handle_mouse_scroll(x=0.0, y=300.0, scroll_x=0, scroll_y=3)
    assert panel.zoom_level == pytest.approx(default)


def test_scroll_clamps_to_max() -> None:
    panel, _, max_zoom, _ = _make_panel()
    panel._zoom_level = max_zoom
    panel.handle_mouse_scroll(x=500.0, y=300.0, scroll_x=0, scroll_y=10)
    assert panel.zoom_level == pytest.approx(max_zoom)


def test_scroll_clamps_to_min() -> None:
    panel, min_zoom, _, _ = _make_panel()
    panel._zoom_level = min_zoom
    panel.handle_mouse_scroll(x=500.0, y=300.0, scroll_x=0, scroll_y=-10)
    assert panel.zoom_level == pytest.approx(min_zoom)


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------

def test_key_plus_increases_zoom() -> None:
    panel, _, _, _ = _make_panel()
    before = panel.zoom_level
    panel.handle_key_press(arcade.key.NUM_ADD)
    assert panel.zoom_level > before


def test_key_equal_increases_zoom() -> None:
    """= (unshifted +) also zooms in."""
    panel, _, _, _ = _make_panel()
    before = panel.zoom_level
    panel.handle_key_press(arcade.key.EQUAL)
    assert panel.zoom_level > before


def test_key_minus_decreases_zoom() -> None:
    panel, _, _, _ = _make_panel()
    before = panel.zoom_level
    panel.handle_key_press(arcade.key.MINUS)
    assert panel.zoom_level < before


def test_key_0_resets_zoom() -> None:
    panel, _, _, default = _make_panel()
    panel._zoom_level = 2.5
    panel.handle_key_press(arcade.key.KEY_0)
    assert panel.zoom_level == pytest.approx(default)


def test_key_clamps_to_max() -> None:
    panel, _, max_zoom, _ = _make_panel()
    panel._zoom_level = max_zoom
    panel.handle_key_press(arcade.key.NUM_ADD)
    assert panel.zoom_level == pytest.approx(max_zoom)


def test_key_clamps_to_min() -> None:
    panel, min_zoom, _, _ = _make_panel()
    panel._zoom_level = min_zoom
    panel.handle_key_press(arcade.key.MINUS)
    assert panel.zoom_level == pytest.approx(min_zoom)


# ---------------------------------------------------------------------------
# Zoom adjusts pan to keep map center stable
# ---------------------------------------------------------------------------

def test_zoom_in_adjusts_pan_offset() -> None:
    """Zooming in adjusts pan_offset so the viewport centre stays mapped to
    the same map coordinate (zoom-to-centre behaviour)."""
    panel, _, _, _ = _make_panel()
    # panel: x=440, y=0, w=800, h=600; PAD_MD=12, _HEADER_H=38, zoom 1.0→1.25
    # map_cx = 440 + (800-12)/2 = 834; map_cy = (600-38)/2 = 281
    # _apply_zoom derives exact offsets: see map_panel.py:_apply_zoom
    panel.handle_key_press(arcade.key.NUM_ADD)
    px, py = panel.pan_offset
    assert px == pytest.approx(-95.5)
    assert py == pytest.approx(-67.25)


# ---------------------------------------------------------------------------
# Variant tab callback
# ---------------------------------------------------------------------------

def test_variant_tab_click_no_callback_does_not_raise() -> None:
    panel, _, _, _ = _make_panel(on_variant_change=None)
    panel._variant_btns = [MagicMock(), MagicMock()]  # Graph + Pan
    panel._handle_variant_click("Map")
    assert panel._active_variant == "Map"
    assert panel._active_tool == "select"


def test_load_zeroes_pan_when_panel_not_set_up() -> None:
    from dungeon_daddy.ui.panels.map_panel import MapPanel
    renderer = MagicMock()
    renderer.cell_px = 48
    panel = MapPanel(on_level_change=lambda d: None, renderer=renderer, overlay=MagicMock())
    # _w and _h are 0.0 — panel not yet set up
    level = _make_level([{"x": 0, "y": 0, "w": 10, "h": 8}])
    panel.load(level, _make_state())
    px, py = panel.pan_offset
    assert px == pytest.approx(0.0)
    assert py == pytest.approx(0.0)
