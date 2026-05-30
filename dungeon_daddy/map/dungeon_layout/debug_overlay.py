"""Debug overlay data model for the dungeon layout pipeline.

Pure Python / Pydantic — no Arcade dependency.
Aggregates all layout geometry needed to render a diagnostic overlay.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from dungeon_daddy.map.dungeon_layout.models import (
    LabelBox,
    LayoutBounds,
    Port,
    RoomRect,
    RoutedEdge,
)


class DebugOverlay(BaseModel):
    """Snapshot of layout geometry for debug rendering."""

    enabled: bool = True
    rooms: list[RoomRect] = Field(default_factory=list)
    obstacles: list[RoomRect] = Field(default_factory=list)
    ports: list[Port] = Field(default_factory=list)
    edges: list[RoutedEdge] = Field(default_factory=list)
    labels: list[LabelBox] = Field(default_factory=list)
    bounds: LayoutBounds | None = None
    illegal_crossings: list[str] = Field(default_factory=list)


def build_debug_overlay(
    rooms: dict[str, RoomRect],
    obstacles: list[RoomRect],
    ports: list[Port],
    edges: list[RoutedEdge],
    labels: list[LabelBox],
    bounds: LayoutBounds,
) -> DebugOverlay:
    """Build a DebugOverlay from completed layout pipeline outputs."""
    illegal_crossings = [
        e.connection_id
        for e in edges
        if any("ILLEGAL_ROOM_CROSSING" in w for w in e.warnings)
    ]
    return DebugOverlay(
        enabled=True,
        rooms=list(rooms.values()),
        obstacles=obstacles,
        ports=ports,
        edges=edges,
        labels=labels,
        bounds=bounds,
        illegal_crossings=illegal_crossings,
    )
