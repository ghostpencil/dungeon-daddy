"""Tests for dungeon_daddy.map.layout_debug_renderer."""
from __future__ import annotations

from unittest.mock import patch

from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
from dungeon_daddy.map.dungeon_layout.models import (
    LayoutBounds,
    RoomRect,
    RoutedEdge,
)
from dungeon_daddy.map.layout_debug_renderer import LayoutDebugRenderer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _room(room_id: str, x: float = 0.0, y: float = 0.0) -> RoomRect:
    return RoomRect(room_id=room_id, x=x, y=y, w=100.0, h=60.0)


def _bounds() -> LayoutBounds:
    return LayoutBounds(min_x=0.0, min_y=0.0, max_x=500.0, max_y=400.0)


def _edge(connection_id: str, points: list[tuple[float, float]] | None = None) -> RoutedEdge:
    return RoutedEdge(
        connection_id=connection_id,
        points=points or [(0.0, 0.0), (100.0, 0.0), (100.0, 60.0)],
        source_port="right",
        target_port="top",
        score=50.0,
    )


def _disabled_overlay() -> DebugOverlay:
    return DebugOverlay(enabled=False)


def _overlay_with_rooms(*rooms: RoomRect) -> DebugOverlay:
    return DebugOverlay(
        enabled=True,
        rooms=list(rooms),
        bounds=_bounds(),
    )


# ---------------------------------------------------------------------------
# Cycle 5 — draw() does nothing when overlay.enabled is False
# ---------------------------------------------------------------------------

def test_draw_does_nothing_when_disabled():
    renderer = LayoutDebugRenderer()
    overlay = _disabled_overlay()
    with patch("dungeon_daddy.map.layout_debug_renderer.arcade") as mock_arcade:
        renderer.draw(overlay, origin_x=0.0, origin_y=0.0, zoom=1.0)
        mock_arcade.draw_rect_outline.assert_not_called()
        mock_arcade.draw_line.assert_not_called()


# ---------------------------------------------------------------------------
# Cycle 6 — draw() calls draw_rect_outline for each room bounding box
# ---------------------------------------------------------------------------

def test_draw_outlines_each_room():
    renderer = LayoutDebugRenderer()
    r1 = _room("r1", x=0.0, y=0.0)
    r2 = _room("r2", x=200.0, y=0.0)
    overlay = _overlay_with_rooms(r1, r2)

    with patch("dungeon_daddy.map.layout_debug_renderer.arcade") as mock_arcade:
        renderer.draw(overlay, origin_x=0.0, origin_y=0.0, zoom=1.0)
        assert mock_arcade.draw_rect_outline.call_count >= 2


# ---------------------------------------------------------------------------
# Cycle 7 — draw() outlines each obstacle box with a different color
# ---------------------------------------------------------------------------

def test_draw_outlines_obstacles_with_distinct_color():
    renderer = LayoutDebugRenderer()
    room = _room("r1")
    obstacle = room.inflate(16.0)
    overlay = DebugOverlay(
        enabled=True,
        rooms=[room],
        obstacles=[obstacle],
        bounds=_bounds(),
    )

    with patch("dungeon_daddy.map.layout_debug_renderer.arcade") as mock_arcade:
        renderer.draw(overlay, origin_x=0.0, origin_y=0.0, zoom=1.0)
        calls = mock_arcade.draw_rect_outline.call_args_list
        # At least 2 calls: one for room, one for obstacle
        assert len(calls) >= 2
        # The color arguments must differ between room and obstacle calls
        colors_used = {c.args[1] if c.args[1:] else c.kwargs.get("color") for c in calls}
        assert len(colors_used) >= 2


# ---------------------------------------------------------------------------
# Cycle 8 — draw() calls draw_line for each segment in each routed edge
# ---------------------------------------------------------------------------

def test_draw_lines_for_each_route_segment():
    renderer = LayoutDebugRenderer()
    # Edge has 3 points → 2 segments
    edge = _edge("r1→r2", points=[(0.0, 0.0), (100.0, 0.0), (100.0, 60.0)])
    overlay = DebugOverlay(
        enabled=True,
        edges=[edge],
        bounds=_bounds(),
    )

    with patch("dungeon_daddy.map.layout_debug_renderer.arcade") as mock_arcade:
        renderer.draw(overlay, origin_x=0.0, origin_y=0.0, zoom=1.0)
        # 2 segments → at least 2 draw_line calls
        assert mock_arcade.draw_line.call_count >= 2
