"""Arcade renderer for the dungeon layout debug overlay.

Draws diagnostic geometry (rooms, obstacles, ports, routes, labels,
camera bounds) on top of the normal map view when debug mode is active.
"""
from __future__ import annotations

import arcade

from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
from dungeon_daddy.map.dungeon_layout.models import RoomRect

# Debug color palette
_COLOR_ROOM = (80, 200, 120)       # green — room bounding boxes
_COLOR_OBSTACLE = (220, 80, 80)    # red — inflated obstacle boxes
_COLOR_PORT = (255, 220, 50)       # yellow — port dots
_COLOR_ROUTE = (80, 160, 255)      # blue — routed polylines
_COLOR_LABEL = (200, 100, 255)     # violet — label bounding boxes
_COLOR_BOUNDS = (255, 160, 30)     # orange — camera fit bounds
_COLOR_ILLEGAL = (255, 50, 50)     # bright red — illegal crossings

_LINE_WIDTH = 1


class LayoutDebugRenderer:
    """Draws a DebugOverlay using Arcade primitives."""

    def draw(
        self,
        overlay: DebugOverlay,
        origin_x: float,
        origin_y: float,
        zoom: float,
    ) -> None:
        if not overlay.enabled:
            return

        self._draw_rooms(overlay, origin_x, origin_y, zoom)
        self._draw_obstacles(overlay, origin_x, origin_y, zoom)
        self._draw_routes(overlay, origin_x, origin_y, zoom)
        self._draw_labels(overlay, origin_x, origin_y, zoom)
        self._draw_ports(overlay, origin_x, origin_y, zoom)
        self._draw_bounds(overlay, origin_x, origin_y, zoom)

    # ------------------------------------------------------------------
    # Private drawing helpers
    # ------------------------------------------------------------------

    def _world_x(self, x: float, origin_x: float, zoom: float) -> float:
        return origin_x + x * zoom

    def _world_y(self, y: float, origin_y: float, zoom: float) -> float:
        return origin_y + y * zoom

    def _draw_rect(
        self,
        rect: RoomRect,
        color: tuple[int, int, int],
        origin_x: float,
        origin_y: float,
        zoom: float,
    ) -> None:
        wx = self._world_x(rect.x, origin_x, zoom)
        wy = self._world_y(rect.y, origin_y, zoom)
        ww = rect.w * zoom
        wh = rect.h * zoom
        arcade.draw_rect_outline(
            arcade.XYWH(wx + ww / 2, wy + wh / 2, ww, wh),
            color,
            _LINE_WIDTH,
        )

    def _draw_rooms(
        self,
        overlay: DebugOverlay,
        origin_x: float,
        origin_y: float,
        zoom: float,
    ) -> None:
        for room in overlay.rooms:
            self._draw_rect(room, _COLOR_ROOM, origin_x, origin_y, zoom)

    def _draw_obstacles(
        self,
        overlay: DebugOverlay,
        origin_x: float,
        origin_y: float,
        zoom: float,
    ) -> None:
        for obs in overlay.obstacles:
            self._draw_rect(obs, _COLOR_OBSTACLE, origin_x, origin_y, zoom)

    def _draw_routes(
        self,
        overlay: DebugOverlay,
        origin_x: float,
        origin_y: float,
        zoom: float,
    ) -> None:
        for edge in overlay.edges:
            is_illegal = edge.connection_id in overlay.illegal_crossings
            color = _COLOR_ILLEGAL if is_illegal else _COLOR_ROUTE
            pts = edge.points
            for i in range(len(pts) - 1):
                x1 = self._world_x(pts[i][0], origin_x, zoom)
                y1 = self._world_y(pts[i][1], origin_y, zoom)
                x2 = self._world_x(pts[i + 1][0], origin_x, zoom)
                y2 = self._world_y(pts[i + 1][1], origin_y, zoom)
                arcade.draw_line(x1, y1, x2, y2, color, _LINE_WIDTH)

    def _draw_labels(
        self,
        overlay: DebugOverlay,
        origin_x: float,
        origin_y: float,
        zoom: float,
    ) -> None:
        for lb in overlay.labels:
            wx = self._world_x(lb.x, origin_x, zoom)
            wy = self._world_y(lb.y, origin_y, zoom)
            ww = lb.w * zoom
            wh = lb.h * zoom
            arcade.draw_rect_outline(
                arcade.XYWH(wx + ww / 2, wy + wh / 2, ww, wh),
                _COLOR_LABEL,
                _LINE_WIDTH,
            )

    def _draw_ports(
        self,
        overlay: DebugOverlay,
        origin_x: float,
        origin_y: float,
        zoom: float,
    ) -> None:
        for port in overlay.ports:
            px = self._world_x(port.x, origin_x, zoom)
            py = self._world_y(port.y, origin_y, zoom)
            arcade.draw_circle_filled(px, py, 3 * zoom, _COLOR_PORT)

    def _draw_bounds(
        self,
        overlay: DebugOverlay,
        origin_x: float,
        origin_y: float,
        zoom: float,
    ) -> None:
        if overlay.bounds is None:
            return
        b = overlay.bounds
        wx = self._world_x(b.min_x, origin_x, zoom)
        wy = self._world_y(b.min_y, origin_y, zoom)
        ww = b.width * zoom
        wh = b.height * zoom
        arcade.draw_rect_outline(
            arcade.XYWH(wx + ww / 2, wy + wh / 2, ww, wh),
            _COLOR_BOUNDS,
            _LINE_WIDTH,
        )
