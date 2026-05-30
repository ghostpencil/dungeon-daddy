"""Arcade renderer for the dungeon layout pipeline output."""
from __future__ import annotations

import arcade

from dungeon_daddy.map.dungeon_layout import LayoutResult
from dungeon_daddy.map.dungeon_layout.connection_style import (
    GraphConnectionStyle,
    GraphConnectionStyleResolver,
)
from dungeon_daddy.map.dungeon_layout.critical_path_style import (
    CriticalPathPresentationResult,
    CriticalPathPresenter,
)
from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyle, GraphRoomStyleResolver
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_config import VisualHierarchyConfig
from dungeon_daddy.map.layout_debug_renderer import LayoutDebugRenderer
from dungeon_daddy.ui.theme import FONT_MONO, FONT_UI, TEAL, TEXT_XS

_ROOM_FILL = (30, 35, 45)
_ROOM_BORDER = (100, 120, 140)
_CRIT_BORDER = (160, 185, 210)
_EDGE_COLOR = (80, 100, 130)
_CRIT_EDGE_COLOR = (120, 150, 180)
_LABEL_COLOR = (160, 170, 180)
_LINE_WIDTH = 1
_SELECTION_WIDTH = 2

_DEFAULT_ROOM_STYLE = GraphRoomStyleResolver().resolve("unknown")
_DEFAULT_CONN_STYLE = GraphConnectionStyleResolver().resolve("")


class LayoutRenderer:
    """Draws a LayoutResult using Arcade primitives."""

    def __init__(self, config: VisualHierarchyConfig | None = None) -> None:
        self._debug_renderer = LayoutDebugRenderer()
        self._config = config or VisualHierarchyConfig()
        self._room_resolver = GraphRoomStyleResolver()
        self._conn_resolver = GraphConnectionStyleResolver()
        self._cp_presenter = CriticalPathPresenter()

    def draw(
        self,
        result: LayoutResult,
        origin_x: float,
        origin_y: float,
        zoom: float,
        selected_room_id: str | None = None,
    ) -> None:
        cp_result = self._cp_presenter.present(
            result.critical_path or None,
            self._config.emphasize_critical_path,
        )
        self._draw_edges(result, origin_x, origin_y, zoom, cp_result)
        self._draw_rooms(result, origin_x, origin_y, zoom, selected_room_id, cp_result)
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

    def _room_style(self, room_id: str, result: LayoutResult) -> GraphRoomStyle:
        if not self._config.style_room_roles:
            return _DEFAULT_ROOM_STYLE
        role = result.room_roles.get(room_id, "unknown")
        return self._room_resolver.resolve(role)

    def _conn_style(self, connection_id: str, result: LayoutResult) -> GraphConnectionStyle:
        label = result.edge_labels.get(connection_id, "")
        return self._conn_resolver.resolve(label)

    def _draw_rooms(
        self,
        result: LayoutResult,
        origin_x: float,
        origin_y: float,
        zoom: float,
        selected_room_id: str | None,
        cp_result: CriticalPathPresentationResult,
    ) -> None:

        for rect in result.rooms.values():
            style = self._room_style(rect.room_id, result)

            wx = self._wx(rect.x, origin_x, zoom)
            wy = self._wy(rect.y, origin_y, zoom)
            ww = rect.w * zoom
            wh = rect.h * zoom
            xywh = arcade.XYWH(wx + ww / 2, wy + wh / 2, ww, wh)

            fill = (*_ROOM_FILL, style.fill_alpha)
            border = (*_ROOM_BORDER, style.border_alpha)
            arcade.draw_rect_filled(xywh, fill)
            arcade.draw_rect_outline(xywh, border, style.border_width)

            if rect.room_id in cp_result.critical_path_room_ids:
                arcade.draw_rect_outline(xywh, _CRIT_BORDER, style.border_width)

            if rect.room_id == selected_room_id:
                arcade.draw_rect_outline(xywh, TEAL, _SELECTION_WIDTH)

            name = result.room_names.get(rect.room_id, "")
            label = f"{name}\n{rect.room_id}" if name else rect.room_id
            arcade.draw_text(
                label, wx + ww / 2, wy + wh / 2,
                _LABEL_COLOR, font_size=TEXT_XS, font_name=FONT_UI,
                anchor_x="center", anchor_y="center",
                width=int(ww), align="center",
                multiline=True,
            )

            if (self._config.enable_connection_markers
                    and style.show_marker and style.marker_text):
                arcade.draw_text(
                    style.marker_text,
                    wx + ww / 2, wy + wh * 0.15,
                    _LABEL_COLOR, font_size=TEXT_XS - 1, font_name=FONT_UI,
                    anchor_x="center", anchor_y="center",
                )

    def _draw_edges(
        self,
        result: LayoutResult,
        origin_x: float,
        origin_y: float,
        zoom: float,
        cp_result: CriticalPathPresentationResult,
    ) -> None:

        for edge in result.edges:
            style = self._conn_style(edge.connection_id, result)
            on_crit = edge.connection_id in cp_result.critical_path_connection_ids
            base_color = _CRIT_EDGE_COLOR if on_crit else _EDGE_COLOR
            color = (*base_color, style.alpha)
            line_width = style.line_width + (0.5 if on_crit else 0.0)

            pts = edge.points
            for i in range(len(pts) - 1):
                x1 = self._wx(pts[i][0], origin_x, zoom)
                y1 = self._wy(pts[i][1], origin_y, zoom)
                x2 = self._wx(pts[i + 1][0], origin_x, zoom)
                y2 = self._wy(pts[i + 1][1], origin_y, zoom)
                arcade.draw_line(x1, y1, x2, y2, color, line_width)

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
