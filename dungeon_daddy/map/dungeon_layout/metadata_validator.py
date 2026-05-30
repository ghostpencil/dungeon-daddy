"""Semantic metadata validation for the dungeon layout pipeline.

Validates floor-level layout_metadata, room layout_role values, and
connection style/role fields. Returns warnings; never raises fatal errors.
No Arcade dependency — pure Python / Pydantic.
"""
from __future__ import annotations

from dungeon_daddy.data.models import Level
from dungeon_daddy.map.dungeon_layout.models import LayoutWarning

# ---------------------------------------------------------------------------
# Valid value sets
# ---------------------------------------------------------------------------

_VALID_LAYOUT_ROLES = frozenset({
    "entrance", "hub", "boss", "objective", "exit", "descent",
    "elevator", "stairs", "key_room", "lock_room", "treasure",
    "hazard", "secret", "corridor", "hall", "library", "forge",
    "utility", "study", "transition", "side_room", "unknown",
})

_VALID_GRAPH_TEMPLATES = frozenset({
    "linear", "freeform", "hub_spoke", "branch_and_merge",
    "lock_key", "split_path", "boss_endcap", "loop",
})

_VALID_CONNECTION_STYLES = frozenset({
    "normal", "critical", "optional", "secret", "locked",
    "vertical", "shortcut", "hazard",
})

_VALID_CONNECTION_ROLES = frozenset({
    "critical", "optional", "secret", "locked", "vertical", "shortcut", "normal",
})

# Roles that make a room a valid critical-path endpoint
_ENDPOINT_ROLES = frozenset({
    "objective", "boss", "exit", "descent", "elevator", "stairs", "transition",
})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_metadata(level: Level) -> list[LayoutWarning]:
    """Return a list of metadata warnings for *level*.

    Checks room roles, connection styles/roles, and floor-level layout_metadata
    consistency. All issues are warnings — none are fatal.
    """
    warnings: list[LayoutWarning] = []
    room_ids = {r.id for r in level.rooms}

    _check_room_roles(level, warnings)
    _check_connection_fields(level, warnings)

    meta = level.layout_metadata
    if meta is None:
        return warnings

    _check_graph_template(meta.graph_template, warnings)
    _check_reference_ids(meta, room_ids, warnings)
    _check_critical_path(meta, room_ids, warnings)
    _check_critical_connections(level, meta, warnings)

    return warnings


# ---------------------------------------------------------------------------
# Internal checks
# ---------------------------------------------------------------------------

def _check_room_roles(level: Level, warnings: list[LayoutWarning]) -> None:
    for room in level.rooms:
        role = room.layout_role
        if role is not None and role not in _VALID_LAYOUT_ROLES:
            warnings.append(LayoutWarning(
                category="INVALID_LAYOUT_ROLE",
                severity="medium",
                message=f"Room '{room.id}' has unrecognised layout_role '{role}'.",
            ))


def _check_connection_fields(level: Level, warnings: list[LayoutWarning]) -> None:
    for conn in level.connections:
        if conn.connection_style is not None and conn.connection_style not in _VALID_CONNECTION_STYLES:
            warnings.append(LayoutWarning(
                category="INVALID_CONNECTION_STYLE",
                severity="medium",
                message=(
                    f"Connection '{conn.from_room}→{conn.to_room}' has unrecognised "
                    f"connection_style '{conn.connection_style}'."
                ),
            ))
        if conn.layout_connection_role is not None and conn.layout_connection_role not in _VALID_CONNECTION_ROLES:
            warnings.append(LayoutWarning(
                category="INVALID_CONNECTION_ROLE",
                severity="medium",
                message=(
                    f"Connection '{conn.from_room}→{conn.to_room}' has unrecognised "
                    f"layout_connection_role '{conn.layout_connection_role}'."
                ),
            ))


def _check_graph_template(template: str | None, warnings: list[LayoutWarning]) -> None:
    if template is not None and template not in _VALID_GRAPH_TEMPLATES:
        warnings.append(LayoutWarning(
            category="INVALID_GRAPH_TEMPLATE",
            severity="medium",
            message=f"layout_metadata.graph_template '{template}' is not a recognised template.",
        ))


def _check_reference_ids(
    meta: object,
    room_ids: set[str],
    warnings: list[LayoutWarning],
) -> None:
    from dungeon_daddy.data.models import LayoutMetadata
    assert isinstance(meta, LayoutMetadata)

    if meta.entrance_room_id and meta.entrance_room_id not in room_ids:
        warnings.append(LayoutWarning(
            category="ENTRANCE_ROOM_NOT_FOUND",
            severity="high",
            message=f"entrance_room_id '{meta.entrance_room_id}' does not match any room ID.",
        ))

    if meta.endpoint_room_id and meta.endpoint_room_id not in room_ids:
        warnings.append(LayoutWarning(
            category="ENDPOINT_ROOM_NOT_FOUND",
            severity="high",
            message=f"endpoint_room_id '{meta.endpoint_room_id}' does not match any room ID.",
        ))


def _check_critical_path(
    meta: object,
    room_ids: set[str],
    warnings: list[LayoutWarning],
) -> None:
    from dungeon_daddy.data.models import LayoutMetadata
    assert isinstance(meta, LayoutMetadata)

    path = meta.critical_path
    if not path:
        return

    # Missing room IDs
    for rid in path:
        if rid not in room_ids:
            warnings.append(LayoutWarning(
                category="CRITICAL_PATH_ROOM_NOT_FOUND",
                severity="high",
                message=f"critical_path contains room ID '{rid}' which does not exist.",
            ))

    # Duplicates
    seen: set[str] = set()
    for rid in path:
        if rid in seen:
            warnings.append(LayoutWarning(
                category="CRITICAL_PATH_DUPLICATE",
                severity="medium",
                message=f"critical_path contains duplicate room ID '{rid}'.",
            ))
        seen.add(rid)

    # Entrance alignment
    if meta.entrance_room_id and path[0] != meta.entrance_room_id:
        warnings.append(LayoutWarning(
            category="CRITICAL_PATH_ENTRANCE_MISMATCH",
            severity="medium",
            message=(
                f"critical_path starts with '{path[0]}' but entrance_room_id is "
                f"'{meta.entrance_room_id}'."
            ),
        ))

    # Endpoint alignment
    if meta.endpoint_room_id and path[-1] != meta.endpoint_room_id:
        warnings.append(LayoutWarning(
            category="CRITICAL_PATH_ENDPOINT_MISMATCH",
            severity="medium",
            message=(
                f"critical_path ends with '{path[-1]}' but endpoint_room_id is "
                f"'{meta.endpoint_room_id}'."
            ),
        ))


def _check_critical_connections(
    level: Level,
    meta: object,
    warnings: list[LayoutWarning],
) -> None:
    from dungeon_daddy.data.models import LayoutMetadata
    assert isinstance(meta, LayoutMetadata)

    path = meta.critical_path
    if not path:
        return

    path_pairs = {(path[i], path[i + 1]) for i in range(len(path) - 1)}
    path_pairs |= {(b, a) for a, b in path_pairs}  # undirected

    for conn in level.connections:
        if conn.layout_connection_role == "critical":
            pair = (conn.from_room, conn.to_room)
            if pair not in path_pairs:
                warnings.append(LayoutWarning(
                    category="CRITICAL_CONNECTION_NOT_IN_PATH",
                    severity="medium",
                    message=(
                        f"Connection '{conn.from_room}→{conn.to_room}' is marked critical "
                        f"but neither direction appears in critical_path."
                    ),
                ))
