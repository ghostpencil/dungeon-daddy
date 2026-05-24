"""GraphRenderer — abstract node graph style map renderer."""
from __future__ import annotations

import math
import arcade

from dungeon_daddy.data.models import Level, SessionState
from dungeon_daddy.map.grid_renderer import GridRenderer
from dungeon_daddy.ui.theme import (
    FONT_UI,
    INK_1,
    INK_2,
    LINE,
    ROOM_COLORS,
    TEAL,
    TEXT_XS,
)

_NODE_RADIUS_CELLS = 0.6


class GraphRenderer(GridRenderer):
    """Renders rooms as circular nodes connected by lines."""

    def draw(self, level: Level, state: SessionState, origin_x: float, origin_y: float, zoom: float = 1.0) -> None:
        effective = self.cell_px * zoom
        room_map = {r.id: r for r in level.rooms}

        radius = _NODE_RADIUS_CELLS * effective
        for conn in level.connections:
            from_r = room_map.get(conn.from_room)
            to_r = room_map.get(conn.to_room)
            if from_r and to_r:
                fcx, fcy = self.room_center(from_r, origin_x, origin_y, zoom)
                tcx, tcy = self.room_center(to_r, origin_x, origin_y, zoom)
                dx, dy = tcx - fcx, tcy - fcy
                dist = math.hypot(dx, dy)
                if dist > 0:
                    ndx, ndy = dx / dist, dy / dist
                    fx, fy = fcx + ndx * radius, fcy + ndy * radius
                    tx, ty = tcx - ndx * radius, tcy - ndy * radius
                else:
                    fx, fy, tx, ty = fcx, fcy, tcx, tcy
                arcade.draw_line(fx, fy, tx, ty, LINE, 1)

        for room in level.rooms:
            cx, cy = self.room_center(room, origin_x, origin_y, zoom)
            colors = ROOM_COLORS.get(room.type, ROOM_COLORS["hall"])
            is_current = room.id == state.current_room_id

            fill = colors["fill"]
            stroke = TEAL if is_current else colors["stroke"]

            arcade.draw_circle_filled(cx, cy, radius, fill)
            arcade.draw_circle_outline(cx, cy, radius, stroke, 2 if is_current else 1)

            label_color = INK_1 if is_current else INK_2
            arcade.draw_text(
                f"{room.name} ({room.id})", cx, cy, label_color,
                font_size=TEXT_XS, font_name=FONT_UI,
                anchor_x="center", anchor_y="center",
            )
