"""Arcade renderer for the dungeon layout pipeline output."""
from __future__ import annotations

import math

import arcade

from dungeon_daddy.data.models import Level
from dungeon_daddy.map.dungeon_layout import LayoutResult
from dungeon_daddy.map.dungeon_layout.atmosphere import AtmosphereSpec, build_atmosphere_spec
from dungeon_daddy.map.dungeon_layout.connection_markers import resolve_connection_marker
from dungeon_daddy.map.dungeon_layout.connection_style import (
    GraphConnectionStyle,
    GraphConnectionStyleResolver,
)
from dungeon_daddy.map.dungeon_layout.critical_path_style import (
    CriticalPathPresentationResult,
    CriticalPathPresenter,
)
from dungeon_daddy.map.dungeon_layout.detail_panel_renderer import PanelLine, format_detail_panel
from dungeon_daddy.map.dungeon_layout.graph_presentation_config import GraphPresentationConfig
from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState
from dungeon_daddy.map.dungeon_layout.panel_placement import ScreenRect, compute_panel_position
from dungeon_daddy.map.dungeon_layout.role_markers import resolve_role_marker
from dungeon_daddy.map.dungeon_layout.room_detail_panel import build_room_detail
from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyle, GraphRoomStyleResolver
from dungeon_daddy.map.dungeon_layout.style_resolver import resolve_room_render_style
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

_PANEL_BG = (15, 20, 30, 210)
_PANEL_BORDER = (70, 90, 110, 200)
_PANEL_HEADER_COLOR = (160, 200, 220, 255)
_PANEL_SECTION_COLOR = (120, 140, 160, 220)
_PANEL_VALUE_COLOR = (180, 185, 190, 255)
_PANEL_LINE_HEIGHT = 16
_PANEL_PADDING = 10
_PANEL_WIDTH = 300.0
_PANEL_FONT_SIZE = 9

_DEFAULT_ROOM_STYLE = GraphRoomStyleResolver().resolve("unknown")
_DEFAULT_CONN_STYLE = GraphConnectionStyleResolver().resolve("")


def _draw_dashed_segment(
    x1: float, y1: float, x2: float, y2: float,
    color: tuple[int, int, int] | tuple[int, int, int, int], width: float, dash: float, gap: float,
) -> None:
    dx, dy = x2 - x1, y2 - y1
    total = math.sqrt(dx * dx + dy * dy)
    if total == 0:
        return
    ux, uy = dx / total, dy / total
    pos = 0.0
    drawing = True
    while pos < total:
        step = dash if drawing else gap
        end = min(pos + step, total)
        if drawing:
            arcade.draw_line(
                x1 + ux * pos, y1 + uy * pos,
                x1 + ux * end, y1 + uy * end,
                color, width,
            )
        pos += step
        drawing = not drawing


def _connected_room_ids(result: LayoutResult, selected_room_id: str | None) -> set[str]:
    """Return room IDs directly adjacent to *selected_room_id* via any edge."""
    if not selected_room_id:
        return set()
    ids: set[str] = set()
    for edge in result.edges:
        cid = edge.connection_id
        if "→" not in cid:
            continue
        src, tgt = cid.split("→", 1)
        if src == selected_room_id:
            ids.add(tgt)
        elif tgt == selected_room_id:
            ids.add(src)
    return ids


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
        view_state: GraphViewState | None = None,
        level: Level | None = None,
        presentation_config: GraphPresentationConfig | None = None,
        panel_x: float = 20.0,
        panel_y: float = 20.0,
        canvas_w: float = 1200.0,
        canvas_h: float = 800.0,
        viewport_x: float = 0.0,
        viewport_y: float = 0.0,
    ) -> None:
        cfg = presentation_config or GraphPresentationConfig()
        if presentation_config is not None:
            self._draw_atmosphere(build_atmosphere_spec(cfg), canvas_w, canvas_h, viewport_x, viewport_y)
        cp_result = self._cp_presenter.present(
            result.critical_path or None,
            self._config.emphasize_critical_path,
        )
        conn_metadata: dict[str, dict[str, str | None]] | None = None
        if level is not None:
            conn_metadata = {
                f"{c.from_room}→{c.to_room}": {
                    "layout_connection_role": c.layout_connection_role,
                    "connection_style": c.connection_style,
                }
                for c in level.connections
            }
        self._draw_edges(result, origin_x, origin_y, zoom, cp_result, view_state, conn_metadata)
        self._draw_rooms(result, origin_x, origin_y, zoom, selected_room_id, cp_result, view_state)
        self._draw_labels(result, origin_x, origin_y, zoom)
        if result.debug_overlay.enabled:
            self._debug_renderer.draw(result.debug_overlay, origin_x, origin_y, zoom)
        if level is not None:
            if cfg.show_detail_panel:
                sel = view_state.selected_room_id if view_state else selected_room_id
                panel_data = build_room_detail(sel, level, result) if sel else None
                lines = format_detail_panel(panel_data)
                panel_h = _PANEL_PADDING * 2 + len(lines) * _PANEL_LINE_HEIGHT
                sel_rect: ScreenRect | None = None
                conn_rects: list[ScreenRect] = []
                if sel and sel in result.rooms:
                    r = result.rooms[sel]
                    sel_rect = ScreenRect(
                        x=self._wx(r.x, origin_x, zoom),
                        y=self._wy(r.y, origin_y, zoom),
                        w=r.w * zoom,
                        h=r.h * zoom,
                    )
                    for cid in _connected_room_ids(result, sel):
                        if cid in result.rooms:
                            cr = result.rooms[cid]
                            conn_rects.append(ScreenRect(
                                x=self._wx(cr.x, origin_x, zoom),
                                y=self._wy(cr.y, origin_y, zoom),
                                w=cr.w * zoom,
                                h=cr.h * zoom,
                            ))
                placement = compute_panel_position(
                    panel_w=_PANEL_WIDTH,
                    panel_h=panel_h,
                    viewport=ScreenRect(viewport_x, viewport_y, canvas_w, canvas_h),
                    preferred_x=panel_x,
                    preferred_y=panel_y,
                    selected_rect=sel_rect,
                    connected_rects=conn_rects,
                )
                self._draw_detail_panel(lines, placement.x, placement.y)

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

    def _conn_style(
        self,
        connection_id: str,
        result: LayoutResult,
        conn_metadata: dict[str, dict[str, str | None]] | None = None,
    ) -> GraphConnectionStyle:
        label = result.edge_labels.get(connection_id, "")
        meta = conn_metadata.get(connection_id, {}) if conn_metadata else {}
        return self._conn_resolver.resolve(
            label,
            connection_style=meta.get("connection_style"),
            layout_connection_role=meta.get("layout_connection_role"),
        )

    def _draw_rooms(
        self,
        result: LayoutResult,
        origin_x: float,
        origin_y: float,
        zoom: float,
        selected_room_id: str | None,
        cp_result: CriticalPathPresentationResult,
        view_state: GraphViewState | None = None,
    ) -> None:

        connected_ids = _connected_room_ids(result, view_state.selected_room_id) if view_state else set()

        for rect in result.rooms.values():
            style = self._room_style(rect.room_id, result)
            if view_state is not None:
                style = resolve_room_render_style(
                    rect.room_id,
                    style,
                    view_state,
                    cp_result.critical_path_room_ids,
                    connected_ids,
                )

            wx = self._wx(rect.x, origin_x, zoom)
            wy = self._wy(rect.y, origin_y, zoom)
            ww = rect.w * zoom
            wh = rect.h * zoom
            xywh = arcade.XYWH(wx + ww / 2, wy + wh / 2, ww, wh)

            fill = (*style.fill_color, style.fill_alpha)
            border = (*style.border_color, style.border_alpha)
            arcade.draw_rect_filled(xywh, fill)
            arcade.draw_rect_outline(xywh, border, style.border_width)

            if style.glow_alpha > 0:
                glow_rect = arcade.XYWH(xywh.x, xywh.y, ww + 6, wh + 6)
                glow_color = (*style.border_color, style.glow_alpha)
                arcade.draw_rect_outline(glow_rect, glow_color, 1.0)

            if style.has_second_outline:
                second_rect = arcade.XYWH(xywh.x, xywh.y, ww + 10, wh + 10)
                second_color = (*style.border_color, max(40, style.border_alpha // 3))
                arcade.draw_rect_outline(second_rect, second_color, 1.0)

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

            role_str = str(result.room_roles.get(rect.room_id, "unknown"))
            marker_text = resolve_role_marker(role_str)
            if marker_text is None and style.show_marker:
                marker_text = style.marker_text
            if self._config.enable_connection_markers and marker_text:
                arcade.draw_text(
                    marker_text,
                    wx + ww / 2, wy + wh * 0.82,
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
        view_state: GraphViewState | None = None,
        conn_metadata: dict[str, dict[str, str | None]] | None = None,
    ) -> None:
        selected_id = view_state.selected_room_id if view_state else None

        for edge in result.edges:
            style = self._conn_style(edge.connection_id, result, conn_metadata)
            on_crit = edge.connection_id in cp_result.critical_path_connection_ids
            base_color = _CRIT_EDGE_COLOR if on_crit else _EDGE_COLOR
            alpha = style.alpha

            if selected_id is not None:
                cid = edge.connection_id
                touches_selected = (
                    "→" in cid and (
                        cid.split("→", 1)[0] == selected_id
                        or cid.split("→", 1)[1] == selected_id
                    )
                )
                if not touches_selected:
                    alpha = max(20, int(alpha * 0.4))

            color = (*base_color, alpha)
            line_width = style.line_width + (0.5 if on_crit else 0.0)

            if view_state is not None and view_state.hovered_connection_id == edge.connection_id:
                alpha = min(255, alpha + 60)
                color = (*base_color, alpha)
                line_width += 0.5

            marker = resolve_connection_marker(style)
            pts = edge.points
            for i in range(len(pts) - 1):
                x1 = self._wx(pts[i][0], origin_x, zoom)
                y1 = self._wy(pts[i][1], origin_y, zoom)
                x2 = self._wx(pts[i + 1][0], origin_x, zoom)
                y2 = self._wy(pts[i + 1][1], origin_y, zoom)
                if marker.is_dashed:
                    _draw_dashed_segment(x1, y1, x2, y2, color, line_width,
                                         marker.dash_length, marker.gap_length)
                else:
                    arcade.draw_line(x1, y1, x2, y2, color, line_width)

            if self._config.enable_connection_markers and marker.midpoint_glyph:
                mid_x = self._wx((pts[0][0] + pts[-1][0]) / 2, origin_x, zoom)
                mid_y = self._wy((pts[0][1] + pts[-1][1]) / 2, origin_y, zoom)
                arcade.draw_text(
                    marker.midpoint_glyph, mid_x, mid_y,
                    _LABEL_COLOR, font_size=TEXT_XS - 1, font_name=FONT_MONO,
                    anchor_x="center", anchor_y="center",
                )

    def _draw_detail_panel(
        self,
        lines: list[PanelLine],
        panel_x: float,
        panel_y: float,
    ) -> None:
        # panel_y is the BOTTOM edge; panel grows upward
        total_h = _PANEL_PADDING * 2 + len(lines) * _PANEL_LINE_HEIGHT
        bg_cx = panel_x + _PANEL_WIDTH / 2
        bg_cy = panel_y + total_h / 2
        bg_rect = arcade.XYWH(bg_cx, bg_cy, _PANEL_WIDTH, total_h)
        arcade.draw_rect_filled(bg_rect, _PANEL_BG)
        arcade.draw_rect_outline(bg_rect, _PANEL_BORDER, 1)

        y = panel_y + total_h - _PANEL_PADDING
        for line in lines:
            if line.kind == "header":
                color = _PANEL_HEADER_COLOR
            elif line.kind == "section":
                color = _PANEL_SECTION_COLOR
            else:
                color = _PANEL_VALUE_COLOR
            arcade.draw_text(
                line.text,
                panel_x + _PANEL_PADDING,
                y,
                color,
                font_size=_PANEL_FONT_SIZE,
                font_name=FONT_MONO,
                width=int(_PANEL_WIDTH - _PANEL_PADDING * 2),
            )
            y -= _PANEL_LINE_HEIGHT

    def _draw_atmosphere(
        self,
        spec: AtmosphereSpec,
        canvas_w: float,
        canvas_h: float,
        viewport_x: float = 0.0,
        viewport_y: float = 0.0,
    ) -> None:
        if not spec.enabled:
            return
        cx = viewport_x + canvas_w / 2
        cy = viewport_y + canvas_h / 2
        for i in range(spec.vignette_bands):
            fraction = (spec.vignette_bands - i) / spec.vignette_bands
            alpha = int(spec.vignette_alpha * fraction)
            band_w = canvas_w * (1.0 - i / spec.vignette_bands * 0.5)
            band_h = canvas_h * (1.0 - i / spec.vignette_bands * 0.5)
            arcade.draw_rect_filled(
                arcade.XYWH(cx, cy, band_w, band_h),
                (0, 0, 0, alpha),
            )
        inset = spec.frame_inset
        frame_rect = arcade.XYWH(cx, cy, canvas_w - inset * 2, canvas_h - inset * 2)
        arcade.draw_rect_outline(frame_rect, spec.frame_color, spec.frame_width)
        if spec.show_corner_ticks:
            t = spec.corner_tick_size
            color = spec.corner_tick_color
            corners = [
                (viewport_x + inset, viewport_y + canvas_h - inset),
                (viewport_x + canvas_w - inset, viewport_y + canvas_h - inset),
                (viewport_x + inset, viewport_y + inset),
                (viewport_x + canvas_w - inset, viewport_y + inset),
            ]
            offsets = [
                ((t, 0), (0, -t)),
                ((-t, 0), (0, -t)),
                ((t, 0), (0, t)),
                ((-t, 0), (0, t)),
            ]
            for (x, y), (dx1dy1, dx2dy2) in zip(corners, offsets):
                dx1, dy1 = dx1dy1
                dx2, dy2 = dx2dy2
                arcade.draw_line(x, y, x + dx1, y + dy1, color, 1.0)
                arcade.draw_line(x, y, x + dx2, y + dy2, color, 1.0)

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
