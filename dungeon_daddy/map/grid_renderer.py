"""Grid-based map renderer — draws rooms and connections using arcade primitives."""
from __future__ import annotations

import math

import arcade

from dungeon_daddy.data.models import Connection, Level, Room, SessionState
from dungeon_daddy.map.routing import (
    get_room_port,
    is_route_problematic,
    route_detour,
    route_waypoints,
    select_port_direction,
    straight_path_blocked,
)
from dungeon_daddy.ui.theme import (
    EMBER,
    FONT_UI,
    INK_1,
    INK_2,
    INK_4,
    LINE,
    ROOM_COLORS,
    TEAL,
    TEXT_XS,
)


def _path_midpoint(pts: list[tuple[float, float]]) -> tuple[float, float]:
    """Return the point at the arc-length midpoint of a polyline."""
    if len(pts) == 1:
        return pts[0]
    total = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
    half = total / 2
    walked = 0.0
    for i in range(len(pts) - 1):
        seg_len = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        if walked + seg_len >= half:
            t = (half - walked) / seg_len if seg_len > 0 else 0.0
            return (pts[i][0] + t * (pts[i + 1][0] - pts[i][0]), pts[i][1] + t * (pts[i + 1][1] - pts[i][1]))
        walked += seg_len
    return pts[-1]


def _dist_point_to_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx, dy = bx - ax, by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0.0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class GridRenderer:
    def __init__(self, cell_px: int = 48, debug_routing: bool = False) -> None:
        self.cell_px = cell_px
        self.debug_routing = debug_routing

    def room_center(self, room: Room, origin_x: float, origin_y: float, zoom: float = 1.0) -> tuple[float, float]:
        effective = self.cell_px * zoom
        cx = origin_x + (room.x + room.w / 2) * effective
        cy = origin_y + (room.y + room.h / 2) * effective
        return cx, cy

    def _port_screen(self, room: Room, direction: str, origin_x: float, origin_y: float, zoom: float) -> tuple[float, float]:
        """Convert a grid-space port to screen pixels."""
        effective = self.cell_px * zoom
        gx, gy = get_room_port(room, direction)
        return origin_x + gx * effective, origin_y + gy * effective

    def hit_test_connection(
        self, level: Level, state: SessionState,
        x: float, y: float,
        origin_x: float, origin_y: float,
        zoom: float = 1.0,
        threshold: float = 8.0,
    ) -> Connection | None:
        effective = self.cell_px * zoom
        room_map = {r.id: r for r in level.rooms}
        for conn in level.connections:
            from_r = room_map.get(conn.from_room)
            to_r = room_map.get(conn.to_room)
            if not (from_r and to_r):
                continue
            if conn.waypoints is not None:
                path = route_waypoints(from_r, to_r, conn.waypoints)
                pts = [(origin_x + gx * effective, origin_y + gy * effective) for gx, gy in path]
            elif straight_path_blocked(from_r, to_r, level.rooms):
                path = route_detour(from_r, to_r, level.rooms)
                pts = [(origin_x + gx * effective, origin_y + gy * effective) for gx, gy in path]
            else:
                fd, td = select_port_direction(from_r, to_r)
                fx, fy = self._port_screen(from_r, fd, origin_x, origin_y, zoom)
                tx, ty = self._port_screen(to_r, td, origin_x, origin_y, zoom)
                pts = [(fx, fy), (tx, ty)]
            for i in range(len(pts) - 1):
                ax, ay = pts[i]
                bx, by = pts[i + 1]
                if _dist_point_to_segment(x, y, ax, ay, bx, by) <= threshold:
                    return conn
        return None

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
                drawn_pts: list[tuple[float, float]] | None = None
                if conn.waypoints is not None:
                    path = route_waypoints(from_r, to_r, conn.waypoints)
                    drawn_pts = [(origin_x + gx * effective, origin_y + gy * effective) for gx, gy in path]
                    for i in range(len(drawn_pts) - 1):
                        arcade.draw_line(drawn_pts[i][0], drawn_pts[i][1], drawn_pts[i + 1][0], drawn_pts[i + 1][1], LINE, 1)
                    if self.debug_routing:
                        for gx, gy in path[1:-1]:
                            wx, wy = origin_x + gx * effective, origin_y + gy * effective
                            arcade.draw_circle_filled(wx, wy, 4, TEAL)
                elif straight_path_blocked(from_r, to_r, level.rooms):
                    path = route_detour(from_r, to_r, level.rooms)
                    drawn_pts = [(origin_x + gx * effective, origin_y + gy * effective) for gx, gy in path]
                    problematic = self.debug_routing and is_route_problematic(path, level.rooms, from_r.id, to_r.id)
                    seg_color = EMBER if problematic else LINE
                    for i in range(len(drawn_pts) - 1):
                        arcade.draw_line(drawn_pts[i][0], drawn_pts[i][1], drawn_pts[i + 1][0], drawn_pts[i + 1][1], seg_color, 1)
                else:
                    arcade.draw_line(fx, fy, tx, ty, LINE, 1)
                if self.debug_routing:
                    arcade.draw_circle_filled(fx, fy, 4, TEAL)
                    arcade.draw_circle_filled(tx, ty, 4, TEAL)
                label = conn.type if len(conn.type) <= 12 else conn.type[:9] + "..."
                if drawn_pts is not None:
                    lx, ly = _path_midpoint(drawn_pts)
                else:
                    lx, ly = (fx + tx) / 2, (fy + ty) / 2
                arcade.draw_text(label, lx, ly, INK_4,
                                 font_size=TEXT_XS, font_name=FONT_UI,
                                 anchor_x="center", anchor_y="center")

        for room in level.rooms:
            cx, cy = self.room_center(room, origin_x, origin_y, zoom)
            w_px = room.w * effective
            h_px = room.h * effective
            rect = arcade.XYWH(cx, cy, w_px, h_px)

            colors = ROOM_COLORS.get(room.type, ROOM_COLORS["hall"])
            is_current = room.id == state.current_room_id

            fill = colors["fill"]
            stroke = TEAL if is_current else colors["stroke"]

            arcade.draw_rect_filled(rect, fill)  # type: ignore[arg-type]
            arcade.draw_rect_outline(rect, stroke, 2 if is_current else 1)  # type: ignore[arg-type]

            label_color = INK_1 if is_current else INK_2
            arcade.draw_text(
                f"{room.name} ({room.id})",
                cx, cy,
                label_color,
                font_size=TEXT_XS,
                font_name=FONT_UI,
                anchor_x="center",
                anchor_y="center",
            )
