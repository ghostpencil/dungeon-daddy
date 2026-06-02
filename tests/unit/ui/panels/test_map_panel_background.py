"""Tests for MapPanel background image drawing (VP-2)."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_panel(variant: str = "Graph"):
    from dungeon_daddy.ui.panels.map_panel import MapPanel

    renderer = MagicMock()
    renderer.cell_px = 48
    panel = MapPanel(
        on_level_change=lambda _: None,
        renderer=renderer,
        overlay=MagicMock(),
    )
    panel._stepper = MagicMock()
    panel._x, panel._y, panel._w, panel._h = 440.0, 0.0, 800.0, 600.0
    panel._loop_strip_rects = {}
    panel._active_variant = variant
    panel._level = None
    panel._state = None
    panel._dungeon_title = ""
    return panel


@contextmanager
def _patched(panel):
    """Yield mocked arcade module with a fake ctx; also silences theme arcade calls."""
    with (
        patch("dungeon_daddy.ui.panels.map_panel.arcade") as mock_arcade,
        patch("dungeon_daddy.ui.theme.arcade"),
    ):
        mock_ctx = MagicMock()
        mock_ctx.scissor = None
        mock_arcade.get_window.return_value.ctx = mock_ctx
        yield mock_arcade


# ---------------------------------------------------------------------------
# Cycle 1 — background drawn in Graph mode when texture available
# ---------------------------------------------------------------------------

def test_background_drawn_in_graph_mode() -> None:
    panel = _make_panel(variant="Graph")
    fake_tex = MagicMock()
    panel._art = MagicMock()
    panel._art.background = fake_tex

    with _patched(panel) as mock_arcade:
        panel.draw()

    textures_drawn = [c.args[0] for c in mock_arcade.draw_texture_rect.call_args_list]
    assert fake_tex in textures_drawn


# ---------------------------------------------------------------------------
# Cycle 2 — background NOT drawn in non-Graph mode
# ---------------------------------------------------------------------------

def test_background_not_drawn_in_grid_mode() -> None:
    panel = _make_panel(variant="Grid")
    fake_tex = MagicMock()
    panel._art = MagicMock()
    panel._art.background = fake_tex

    with _patched(panel) as mock_arcade:
        panel.draw()

    textures_drawn = [c.args[0] for c in mock_arcade.draw_texture_rect.call_args_list]
    assert fake_tex not in textures_drawn


# ---------------------------------------------------------------------------
# Cycle 3 — no crash when background texture is None
# ---------------------------------------------------------------------------

def test_no_crash_when_background_is_none() -> None:
    panel = _make_panel(variant="Graph")
    panel._art = MagicMock()
    panel._art.background = None

    with _patched(panel):
        panel.draw()  # must not raise
