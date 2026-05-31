"""Interaction state for Graph Mode — camera, hover, and selection.

Kept separate from LayoutResult so stable geometry is never mutated by UI events.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class CameraState(BaseModel):
    pan_x: float = 0.0
    pan_y: float = 0.0
    zoom: float = 1.0


class GraphViewState(BaseModel):
    camera: CameraState = Field(default_factory=CameraState)
    selected_room_id: str | None = None
    hovered_room_id: str | None = None
    hovered_connection_id: str | None = None

    def hover_room(self, room_id: str | None) -> None:
        self.hovered_room_id = room_id

    def select_room(self, room_id: str | None) -> None:
        self.selected_room_id = room_id

    def hover_connection(self, connection_id: str | None) -> None:
        self.hovered_connection_id = connection_id

    def clear_selection(self) -> None:
        self.selected_room_id = None

    def recenter(self) -> None:
        self.camera.pan_x = 0.0
        self.camera.pan_y = 0.0
        self.camera.zoom = 1.0
