"""Visual hierarchy configuration constants for Graph Mode.

Controls which semantic presentation features are active.
No Arcade dependency — pure Python.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VisualHierarchyConfig:
    show_role_debug_labels: bool = False
    emphasize_critical_path: bool = True
    style_secret_connections: bool = True
    style_endpoint_rooms: bool = True
    style_room_roles: bool = True
    enable_shape_grammar: bool = True
    enable_connection_markers: bool = True
    enable_visual_hierarchy_feedback: bool = True
