"""Geometry data models for the dungeon layout pipeline.

All coordinates are in abstract layout space (pixels or grid units).
No Arcade dependency — pure Python / Pydantic.
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, computed_field


# ---------------------------------------------------------------------------
# RoomRect
# ---------------------------------------------------------------------------

class RoomRect(BaseModel):
    """Bounding rectangle for a placed room."""

    room_id: str = ""
    x: float
    y: float
    w: float
    h: float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def left(self) -> float:
        return self.x

    @computed_field  # type: ignore[prop-decorator]
    @property
    def bottom(self) -> float:
        return self.y

    @computed_field  # type: ignore[prop-decorator]
    @property
    def right(self) -> float:
        return self.x + self.w

    @computed_field  # type: ignore[prop-decorator]
    @property
    def top(self) -> float:
        return self.y + self.h

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def inflate(self, amount: float) -> "RoomRect":
        return RoomRect(
            room_id=self.room_id,
            x=self.x - amount,
            y=self.y - amount,
            w=self.w + amount * 2,
            h=self.h + amount * 2,
        )

    def contains_point(self, px: float, py: float) -> bool:
        return self.left <= px <= self.right and self.bottom <= py <= self.top


# ---------------------------------------------------------------------------
# Port
# ---------------------------------------------------------------------------

PortSide = Literal["top", "bottom", "left", "right"]


class Port(BaseModel):
    """A named connection point on a room edge."""

    room_id: str
    side: PortSide
    x: float
    y: float


# ---------------------------------------------------------------------------
# RouteSegment
# ---------------------------------------------------------------------------

Point = tuple[float, float]


class RouteSegment(BaseModel):
    """A single straight segment of a routed polyline."""

    start: Point
    end: Point

    @computed_field  # type: ignore[prop-decorator]
    @property
    def length(self) -> float:
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        return math.sqrt(dx * dx + dy * dy)


# ---------------------------------------------------------------------------
# RoutedEdge
# ---------------------------------------------------------------------------

class RoutedEdge(BaseModel):
    """A fully routed connection between two rooms."""

    connection_id: str
    points: list[Point]
    source_port: str
    target_port: str
    score: float
    warnings: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def bend_count(self) -> int:
        if len(self.points) < 3:
            return 0
        return len(self.points) - 2


# ---------------------------------------------------------------------------
# LabelBox
# ---------------------------------------------------------------------------

class LabelBox(BaseModel):
    """Bounding rectangle for a placed connection label."""

    connection_id: str
    text: str
    x: float
    y: float
    w: float
    h: float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def right(self) -> float:
        return self.x + self.w

    @computed_field  # type: ignore[prop-decorator]
    @property
    def top(self) -> float:
        return self.y + self.h


# ---------------------------------------------------------------------------
# LayoutBounds
# ---------------------------------------------------------------------------

class LayoutBounds(BaseModel):
    """Axis-aligned bounding box of the full layout (for camera fit)."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @computed_field  # type: ignore[prop-decorator]
    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    def expand(self, margin: float) -> "LayoutBounds":
        return LayoutBounds(
            min_x=self.min_x - margin,
            min_y=self.min_y - margin,
            max_x=self.max_x + margin,
            max_y=self.max_y + margin,
        )

    @classmethod
    def from_rects(cls, rects: list[RoomRect]) -> "LayoutBounds":
        return cls(
            min_x=min(r.left for r in rects),
            min_y=min(r.bottom for r in rects),
            max_x=max(r.right for r in rects),
            max_y=max(r.top for r in rects),
        )
