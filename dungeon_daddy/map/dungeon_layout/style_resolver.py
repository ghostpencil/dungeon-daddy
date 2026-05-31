"""Interaction style resolution pipeline for Graph Mode rooms.

Composes final render style from: base role style → critical path → focus/fade → hover → selected.
No Arcade dependency — pure Python.
"""
from __future__ import annotations

import dataclasses

from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyle
from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState


def resolve_room_render_style(
    room_id: str,
    base_style: GraphRoomStyle,
    view_state: GraphViewState,
    critical_path_room_ids: set[str],
    connected_room_ids: set[str],
) -> GraphRoomStyle:
    """Return a new GraphRoomStyle with interaction state composited on top of base_style."""
    s = dataclasses.replace(base_style)

    selected_id = view_state.selected_room_id
    is_selected = selected_id == room_id

    # --- Focus / fade (only when another room is selected) ---
    selected_on_critical_path = selected_id is not None and selected_id in critical_path_room_ids
    if selected_id is not None and not is_selected:
        if room_id in connected_room_ids:
            s = dataclasses.replace(
                s,
                border_alpha=min(255, s.border_alpha + 30),
                fill_alpha=min(255, s.fill_alpha + 15),
                border_width=s.border_width + 0.5,
            )
        elif room_id in critical_path_room_ids and selected_on_critical_path:
            # Selected room is on the critical path — emphasise the whole path
            s = dataclasses.replace(
                s,
                border_alpha=min(255, s.border_alpha + 40),
                border_width=s.border_width + 0.5,
            )
        elif room_id in critical_path_room_ids:
            s = dataclasses.replace(
                s,
                border_alpha=max(100, s.border_alpha - 40),
            )
        else:
            s = dataclasses.replace(
                s,
                border_alpha=max(60, s.border_alpha - 80),
                fill_alpha=max(15, s.fill_alpha - 20),
            )

    # --- Hover (skipped when selected) ---
    if view_state.hovered_room_id == room_id and not is_selected:
        s = dataclasses.replace(
            s,
            border_alpha=min(255, s.border_alpha + 40),
            fill_alpha=min(255, s.fill_alpha + 15),
            border_width=s.border_width + 0.5,
        )

    # --- Selected (dominant) ---
    if is_selected:
        s = dataclasses.replace(
            s,
            border_width=max(base_style.border_width, 3.5),
            border_alpha=255,
            border_color=(220, 220, 255),
            fill_alpha=min(255, base_style.fill_alpha + 30),
        )

    return s
