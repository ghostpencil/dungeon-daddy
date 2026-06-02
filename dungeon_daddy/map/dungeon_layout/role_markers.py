"""Role marker resolution: maps room roles to small text glyphs."""
from __future__ import annotations

_MARKERS: dict[str, str] = {
    "entrance": "IN",
    "objective": "OBJ",
    "boss": "BOSS",
    "hazard": "!",
    "key_room": "KEY",
    "descent": "↓",
    "stairs": "↓",
    "elevator": "↓",
    "transition": "↓",
    "treasure": "$",
    "hub": "HUB",
}


def resolve_role_marker(role: str) -> str | None:
    """Return the display glyph for a room role, or None for quiet roles."""
    return _MARKERS.get(role)
