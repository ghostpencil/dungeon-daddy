"""Connection marker resolution: maps a GraphConnectionStyle to render properties."""
from __future__ import annotations

from dataclasses import dataclass

from dungeon_daddy.map.dungeon_layout.connection_style import GraphConnectionStyle

_GLYPH_MAP: dict[str, str] = {
    "lock": "LOCK",
    "vertical": "↕",
    "hazard": "!",
}


@dataclass
class ConnectionMarker:
    midpoint_glyph: str | None
    is_dashed: bool
    dash_length: float
    gap_length: float


def resolve_connection_marker(style: GraphConnectionStyle) -> ConnectionMarker:
    """Return marker properties derived from a GraphConnectionStyle."""
    glyph = _GLYPH_MAP.get(style.marker_type) if style.marker_type else None
    if style.dashed:
        return ConnectionMarker(
            midpoint_glyph=glyph,
            is_dashed=True,
            dash_length=8.0,
            gap_length=6.0,
        )
    return ConnectionMarker(
        midpoint_glyph=glyph,
        is_dashed=False,
        dash_length=0.0,
        gap_length=0.0,
    )
