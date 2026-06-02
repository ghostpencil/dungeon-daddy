"""Marker scoring for Graph Mode presentation feedback.

Computes marker_feedback dict for a Level, distinguishing between:
- fixtures with marker-worthy connections (scored normally)
- fixtures with no marker-worthy connections (not penalized)
"""
from __future__ import annotations

from dungeon_daddy.data.models import Level
from dungeon_daddy.map.dungeon_layout.role_markers import resolve_role_marker

_MARKER_WORTHY_ROLES: frozenset[str] = frozenset(
    {"locked", "secret", "shortcut", "vertical", "hazard"}
)


def compute_marker_feedback(level: Level) -> dict:
    """Return marker_feedback dict for a presentation report.

    If no marker-worthy connections exist, sets not_penalized_reason so the
    artifact generator knows not to dock points.
    """
    role_markers_applied = any(
        resolve_role_marker(r.layout_role or "") is not None
        for r in level.rooms
    )

    detected = sum(
        1 for c in level.connections
        if c.layout_connection_role in _MARKER_WORTHY_ROLES
    )
    applied = detected > 0

    result: dict = {
        "role_markers_applied": role_markers_applied,
        "connection_markers_applied": applied,
        "marker_worthy_connections_detected": detected,
        "marker_worthy_connections_rendered": detected if applied else 0,
        "warnings": [],
    }

    if detected == 0:
        result["not_penalized_reason"] = "No marker-worthy connections in fixture metadata"

    return result
