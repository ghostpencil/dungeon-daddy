"""Unit tests for atmosphere.py — restrained atmosphere layer."""
from __future__ import annotations

from dungeon_daddy.map.dungeon_layout.atmosphere import AtmosphereSpec, build_atmosphere_spec
from dungeon_daddy.map.dungeon_layout.graph_presentation_config import GraphPresentationConfig


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
# Cycle 3 — default → vignette has visible alpha and multiple bands
# ---------------------------------------------------------------------------

def test_default_vignette_alpha_is_positive() -> None:
    spec = build_atmosphere_spec()
    assert 0 < spec.vignette_alpha <= 255


def test_default_vignette_bands_are_positive() -> None:
    spec = build_atmosphere_spec()
    assert spec.vignette_bands > 0


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

from unittest.mock import patch

from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
from dungeon_daddy.map.dungeon_layout.models import LayoutBounds, RoomRect
from dungeon_daddy.map.layout_renderer import LayoutRenderer


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


def test_renderer_atmosphere_enabled_draws_rect_fills() -> None:
    renderer = LayoutRenderer()
    result = _minimal_result()
    cfg = GraphPresentationConfig(enable_atmosphere=True)

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(
            result, origin_x=0.0, origin_y=0.0, zoom=1.0,
            presentation_config=cfg,
            canvas_w=1200.0, canvas_h=800.0,
        )
        # Atmosphere vignette bands generate multiple rect fills
        assert mock_arcade.draw_rect_filled.call_count > 0


def test_renderer_atmosphere_disabled_draws_no_atmosphere_fills() -> None:
    renderer = LayoutRenderer()
    cfg_on = GraphPresentationConfig(enable_atmosphere=True)
    cfg_off = GraphPresentationConfig(enable_atmosphere=False)

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_on:
        renderer.draw(_minimal_result(), 0.0, 0.0, 1.0, presentation_config=cfg_on,
                      canvas_w=1200.0, canvas_h=800.0)
        fills_on = mock_on.draw_rect_filled.call_count

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_off:
        renderer.draw(_minimal_result(), 0.0, 0.0, 1.0, presentation_config=cfg_off,
                      canvas_w=1200.0, canvas_h=800.0)
        fills_off = mock_off.draw_rect_filled.call_count

    assert fills_on > fills_off
