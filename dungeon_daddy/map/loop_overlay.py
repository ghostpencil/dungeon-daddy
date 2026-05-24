"""Overlay that draws active loop paths on top of the grid map."""
from __future__ import annotations

import arcade

from dungeon_daddy.data.models import Level, SessionState
from dungeon_daddy.map.grid_renderer import GridRenderer
from dungeon_daddy.ui.theme import PATH_A_COLOR, PATH_B_COLOR


class LoopOverlay:
    def draw(
        self,
        level: Level,
        state: SessionState,
        renderer: GridRenderer,
        origin_x: float,
        origin_y: float,
        zoom: float = 1.0,
    ) -> None:
        if state.active_loop_id is None:
            return

        loop = next((lp for lp in level.loops if lp.id == state.active_loop_id), None)
        if loop is None:
            return

        room_map = {r.id: r for r in level.rooms}
        self._draw_path(loop.path_a, PATH_A_COLOR, room_map, renderer, origin_x, origin_y, zoom)
        self._draw_path(loop.path_b, PATH_B_COLOR, room_map, renderer, origin_x, origin_y, zoom)

    def _draw_path(
        self,
        path: list[str],
        color: tuple,
        room_map: dict,
        renderer: GridRenderer,
        origin_x: float,
        origin_y: float,
        zoom: float = 1.0,
    ) -> None:
        for i in range(len(path) - 1):
            a = room_map.get(path[i])
            b = room_map.get(path[i + 1])
            if a and b:
                ax, ay = renderer.room_center(a, origin_x, origin_y, zoom)
                bx, by = renderer.room_center(b, origin_x, origin_y, zoom)
                arcade.draw_line(ax, ay, bx, by, color, 2)
