"""Unit tests for atmosphere.py — restrained atmosphere layer."""
from __future__ import annotations

from unittest.mock import patch

from dungeon_daddy.map.dungeon_layout.atmosphere import build_atmosphere_spec
from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
from dungeon_daddy.map.dungeon_layout.graph_presentation_config import GraphPresentationConfig
from dungeon_daddy.map.dungeon_layout.models import LayoutBounds
from dungeon_daddy.map.layout_renderer import LayoutRenderer

# ---------------------------------------------------------------------------
# Cycle 1 — disabled config → enabled=False
# ---------------------------------------------------------------------------

def test_disabled_config_returns_enabled_false() -> None:
    spec = build_atmosphere_spec(GraphPresentationConfig(enable_atmosphere=False))
    assert spec.enabled is False


# ---------------------------------------------------------------------------
# Cycle 2 — default config → enabled=True
# ---------------------------------------------------------------------------

def test_default_config_returns_enabled_true() -> None:
    spec = build_atmosphere_spec()
    assert spec.enabled is True


def test_explicit_enabled_config_returns_enabled_true() -> None:
    spec = build_atmosphere_spec(GraphPresentationConfig(enable_atmosphere=True))
    assert spec.enabled is True


# ---------------------------------------------------------------------------
# Cycle 3 — default → vignette disabled (bands caused visible banding on dark BG)
# ---------------------------------------------------------------------------

def test_default_vignette_alpha_is_zero() -> None:
    # Vignette bands are intentionally disabled: they invert the gradient
    # (center darker than edges) on a near-black background, causing visible
    # concentric rectangle artefacts. Frame + corner ticks provide the mood.
    spec = build_atmosphere_spec()
    assert spec.vignette_alpha == 0


def test_default_vignette_bands_are_zero() -> None:
    spec = build_atmosphere_spec()
    assert spec.vignette_bands == 0


def test_disabled_vignette_alpha_is_zero() -> None:
    spec = build_atmosphere_spec(GraphPresentationConfig(enable_atmosphere=False))
    assert spec.vignette_alpha == 0


# ---------------------------------------------------------------------------
# Cycle 4 — default → frame is thin and inset from edge
# ---------------------------------------------------------------------------

def test_default_frame_width_is_thin() -> None:
    spec = build_atmosphere_spec()
    assert 1.0 <= spec.frame_width <= 3.0


def test_default_frame_inset_is_small() -> None:
    spec = build_atmosphere_spec()
    assert 0.0 < spec.frame_inset <= 20.0


def test_default_frame_color_has_visible_alpha() -> None:
    spec = build_atmosphere_spec()
    assert spec.frame_color[3] > 0


# ---------------------------------------------------------------------------
# Cycle 5 — corner ticks enabled by default, small, off when disabled
# ---------------------------------------------------------------------------

def test_default_shows_corner_ticks() -> None:
    spec = build_atmosphere_spec()
    assert spec.show_corner_ticks is True


def test_default_corner_tick_size_is_small() -> None:
    spec = build_atmosphere_spec()
    assert 0 < spec.corner_tick_size <= 30


def test_disabled_does_not_show_corner_ticks() -> None:
    spec = build_atmosphere_spec(GraphPresentationConfig(enable_atmosphere=False))
    assert spec.show_corner_ticks is False


# ---------------------------------------------------------------------------
# Cycles 6 & 7 — LayoutRenderer draws atmosphere when enabled, skips when disabled
# ---------------------------------------------------------------------------

def _minimal_result():
    from dungeon_daddy.map.dungeon_layout import LayoutResult
    bounds = LayoutBounds(min_x=0.0, min_y=0.0, max_x=400.0, max_y=300.0)
    return LayoutResult(
        rooms={},
        edges=[],
        labels=[],
        bounds=bounds,
        debug_overlay=DebugOverlay(enabled=False, bounds=bounds),
        room_names={},
        room_roles={},
        edge_labels={},
        critical_path=[],
    )


def test_renderer_atmosphere_enabled_draws_frame_and_ticks() -> None:
    renderer = LayoutRenderer()
    result = _minimal_result()
    cfg = GraphPresentationConfig(enable_atmosphere=True)

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(
            result, origin_x=0.0, origin_y=0.0, zoom=1.0,
            presentation_config=cfg,
            canvas_w=1200.0, canvas_h=800.0,
        )
        # Frame outline + corner ticks (8 lines) drawn when atmosphere enabled
        assert mock_arcade.draw_rect_outline.call_count >= 1
        assert mock_arcade.draw_line.call_count >= 8


def test_renderer_atmosphere_disabled_draws_no_frame() -> None:
    renderer = LayoutRenderer()
    cfg_on = GraphPresentationConfig(enable_atmosphere=True)
    cfg_off = GraphPresentationConfig(enable_atmosphere=False)

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_on:
        renderer.draw(_minimal_result(), 0.0, 0.0, 1.0, presentation_config=cfg_on,
                      canvas_w=1200.0, canvas_h=800.0)
        outlines_on = mock_on.draw_rect_outline.call_count

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_off:
        renderer.draw(_minimal_result(), 0.0, 0.0, 1.0, presentation_config=cfg_off,
                      canvas_w=1200.0, canvas_h=800.0)
        outlines_off = mock_off.draw_rect_outline.call_count

    assert outlines_on > outlines_off


# ---------------------------------------------------------------------------
# Cycle 8 — atmosphere frame is offset by viewport_x / viewport_y
# ---------------------------------------------------------------------------

def test_atmosphere_frame_centered_on_viewport_origin() -> None:
    """Frame center must be viewport_x + canvas_w/2, viewport_y + canvas_h/2."""
    renderer = LayoutRenderer()
    cfg = GraphPresentationConfig(enable_atmosphere=True)

    captured_rects: list = []

    class FakeXYWH:
        def __init__(self, x, y, w, h):
            self.x, self.y, self.w, self.h = x, y, w, h

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        mock_arcade.XYWH.side_effect = FakeXYWH
        renderer.draw(
            _minimal_result(), origin_x=0.0, origin_y=0.0, zoom=1.0,
            presentation_config=cfg,
            canvas_w=1200.0, canvas_h=800.0,
            viewport_x=100.0, viewport_y=50.0,
        )
        for call in mock_arcade.draw_rect_outline.call_args_list:
            rect = call.args[0]
            captured_rects.append(rect)

    # The atmosphere frame rect must be centred at (100 + 600, 50 + 400) = (700, 450)
    frame = captured_rects[0]
    assert frame.x == pytest.approx(700.0), f"frame cx={frame.x}, expected 700.0"
    assert frame.y == pytest.approx(450.0), f"frame cy={frame.y}, expected 450.0"


import pytest
