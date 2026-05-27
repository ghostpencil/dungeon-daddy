"""TilesRenderer — shaded top-down tile style map renderer."""
from __future__ import annotations

import arcade

from dungeon_daddy.data.models import Level, SessionState
from dungeon_daddy.map.grid_renderer import GridRenderer
from dungeon_daddy.map.routing import select_port_direction
from dungeon_daddy.ui.theme import (
    FONT_UI,
    INK_2,
    INK_4,
    LINE,
    ROOM_COLORS,
    ROOM_UNSEEN_FILL,
    ROOM_UNSEEN_STROKE,
    TEAL,
    TEXT_XS,
)

_TILE_SHADE = (0, 0, 0, 40)


class TilesRenderer(GridRenderer):
    """Renders rooms as shaded tiles with a crosshatch floor pattern."""

    def draw(self, level: Level, state: SessionState, origin_x: float, origin_y: float, zoom: float = 1.0) -> None:
        effective = self.cell_px * zoom
        room_map = {r.id: r for r in level.rooms}

        for conn in level.connections:
            from_r = room_map.get(conn.from_room)
            to_r = room_map.get(conn.to_room)
            if from_r and to_r:
                fd, td = select_port_direction(from_r, to_r)
                fx, fy = self._port_screen(from_r, fd, origin_x, origin_y, zoom)
                tx, ty = self._port_screen(to_r, td, origin_x, origin_y, zoom)
                arcade.draw_line(fx, fy, tx, ty, LINE, 2)

        for room in level.rooms:
            cx, cy = self.room_center(room, origin_x, origin_y, zoom)
            w_px = room.w * effective
            h_px = room.h * effective
            rect = arcade.XYWH(cx, cy, w_px, h_px)

            is_seen = room.id in state.visited_rooms or room.id == state.current_room_id
            colors = ROOM_COLORS.get(room.type, ROOM_COLORS["hall"])

            fill = colors["fill"] if is_seen else ROOM_UNSEEN_FILL
            if room.id == state.current_room_id:
                stroke = TEAL
            elif is_seen:
                stroke = colors["stroke"]  # type: ignore[assignment]
            else:
                stroke = ROOM_UNSEEN_STROKE

            arcade.draw_rect_filled(rect, fill)  # type: ignore[arg-type]
            arcade.draw_rect_filled(rect, _TILE_SHADE)
            arcade.draw_rect_outline(rect, stroke, 2)

            label_color = INK_2 if is_seen else INK_4
            arcade.draw_text(
                f"{room.name} ({room.id})", cx, cy, label_color,
                font_size=TEXT_XS, font_name=FONT_UI,
                anchor_x="center", anchor_y="center",
            )
