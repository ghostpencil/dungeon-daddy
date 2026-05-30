"""Arcade renderer for the dungeon layout pipeline output."""
from __future__ import annotations

import arcade

from dungeon_daddy.map.dungeon_layout import LayoutResult
from dungeon_daddy.map.layout_debug_renderer import LayoutDebugRenderer
from dungeon_daddy.ui.theme import FONT_MONO, TEXT_XS

_ROOM_FILL = (30, 35, 45)
_ROOM_BORDER = (100, 120, 140)
_EDGE_COLOR = (80, 100, 130)
_LABEL_COLOR = (160, 170, 180)
_LINE_WIDTH = 1


class LayoutRenderer:
    """Draws a LayoutResult using Arcade primitives."""

    def __init__(self) -> None:
        self._debug_renderer = LayoutDebugRenderer()

    def draw(
        self,
        result: LayoutResult,
        origin_x: float,
        origin_y: float,
        zoom: float,
    ) -> None:
        self._draw_edges(result, origin_x, origin_y, zoom)
        self._draw_rooms(result, origin_x, origin_y, zoom)
        self._draw_labels(result, origin_x, origin_y, zoom)
        if result.debug_overlay.enabled:
            self._debug_renderer.draw(result.debug_overlay, origin_x, origin_y, zoom)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _wx(self, lx: float, origin_x: float, zoom: float) -> float:
        return origin_x + lx * zoom

    def _wy(self, ly: float, origin_y: float, zoom: float) -> float:
        return origin_y + ly * zoom

    def _draw_rooms(
        self,
        result: LayoutResult,
        origin_x: float,
        origin_y: float,
        zoom: float,
    ) -> None:
        for rect in result.rooms.values():
            wx = self._wx(rect.x, origin_x, zoom)
            wy = self._wy(rect.y, origin_y, zoom)
            ww = rect.w * zoom
            wh = rect.h * zoom
            xywh = arcade.XYWH(wx + ww / 2, wy + wh / 2, ww, wh)
            arcade.draw_rect_filled(xywh, _ROOM_FILL)
            arcade.draw_rect_outline(xywh, _ROOM_BORDER, _LINE_WIDTH)

    def _draw_edges(
        self,
        result: LayoutResult,
        origin_x: float,
        origin_y: float,
        zoom: float,
    ) -> None:
        for edge in result.edges:
            pts = edge.points
            for i in range(len(pts) - 1):
                x1 = self._wx(pts[i][0], origin_x, zoom)
                y1 = self._wy(pts[i][1], origin_y, zoom)
                x2 = self._wx(pts[i + 1][0], origin_x, zoom)
                y2 = self._wy(pts[i + 1][1], origin_y, zoom)
                arcade.draw_line(x1, y1, x2, y2, _EDGE_COLOR, _LINE_WIDTH)

    def _draw_labels(
        self,
        result: LayoutResult,
        origin_x: float,
        origin_y: float,
        zoom: float,
    ) -> None:
        for lb in result.labels:
            if not lb.text:
                continue
            wx = self._wx(lb.x, origin_x, zoom)
            wy = self._wy(lb.y, origin_y, zoom)
            arcade.draw_text(
                lb.text, wx, wy, _LABEL_COLOR,
                font_size=TEXT_XS, font_name=FONT_MONO,
            )
