"""Visual hierarchy feedback report generation for Graph Mode.

Assembles resolved style data, endpoint emphasis, and critical path results
into a structured feedback section for the layout feedback JSON.
No Arcade dependency — pure Python / Pydantic.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from dungeon_daddy.map.dungeon_layout.connection_style import GraphConnectionStyleResolver
from dungeon_daddy.map.dungeon_layout.critical_path_style import CriticalPathPresentationResult
from dungeon_daddy.map.dungeon_layout.endpoint_emphasis import EndpointEmphasisResult
from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyleResolver
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_config import VisualHierarchyConfig

_room_resolver = GraphRoomStyleResolver()
_conn_resolver = GraphConnectionStyleResolver()

_SECRET_LABELS: frozenset[str] = frozenset({"secret", "shortcut", "secret_shortcut"})
_VERTICAL_LABELS: frozenset[str] = frozenset({"vertical", "hole"})


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class RoomStyleFeedbackEntry(BaseModel):
    room_id: str
    room_name: str
    role: str
    style_key: str
    expected_visual_priority: str
    actual_visual_priority: str
    warnings: list[str] = Field(default_factory=list)


class ConnectionStyleFeedbackEntry(BaseModel):
    connection_id: str
    label: str
    connection_type: str
    style_key: str
    warnings: list[str] = Field(default_factory=list)


class EndpointFeedback(BaseModel):
    endpoint_room_id: str | None
    endpoint_role: str | None
    is_emphasized: bool
    has_sufficient_spacing: bool
    warnings: list[str] = Field(default_factory=list)


class CriticalPathFeedback(BaseModel):
    critical_path: list[str]
    is_visually_distinguished: bool
    warnings: list[str] = Field(default_factory=list)


class VisualHierarchyFeedbackReport(BaseModel):
    roles_styled: bool
    connection_styles_applied: bool
    critical_path_emphasized: bool
    endpoint_emphasized: bool
    shape_grammar_applied: bool
    semantic_score: float
    room_style_feedback: list[RoomStyleFeedbackEntry]
    connection_style_feedback: list[ConnectionStyleFeedbackEntry]
    endpoint_feedback: EndpointFeedback
    critical_path_feedback: CriticalPathFeedback
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_visual_hierarchy_feedback(
    rooms: dict[str, str],
    room_names: dict[str, str],
    connections: list[tuple[str, str]],
    endpoint_result: EndpointEmphasisResult,
    critical_path_result: CriticalPathPresentationResult,
    config: VisualHierarchyConfig,
) -> VisualHierarchyFeedbackReport:
    """Assemble visual hierarchy feedback from resolved style data."""
    warnings: list[str] = []

    room_fb = _build_room_feedback(rooms, room_names)
    conn_fb = _build_connection_feedback(connections)

    _collect_room_warnings(rooms, config, warnings)
    _collect_connection_warnings(connections, config, warnings)
    warnings.extend(endpoint_result.warnings)
    warnings.extend(critical_path_result.warnings)

    score = _compute_semantic_score(room_fb, conn_fb, endpoint_result, critical_path_result)

    non_default_conn = any(e.style_key != "normal" for e in conn_fb)

    return VisualHierarchyFeedbackReport(
        roles_styled=config.style_room_roles,
        connection_styles_applied=non_default_conn,
        critical_path_emphasized=critical_path_result.is_visually_distinguished,
        endpoint_emphasized=endpoint_result.is_emphasized,
        shape_grammar_applied=config.enable_shape_grammar,
        semantic_score=score,
        room_style_feedback=room_fb,
        connection_style_feedback=conn_fb,
        endpoint_feedback=EndpointFeedback(
            endpoint_room_id=endpoint_result.endpoint_room_id,
            endpoint_role=endpoint_result.endpoint_role,
            is_emphasized=endpoint_result.is_emphasized,
            has_sufficient_spacing=endpoint_result.has_sufficient_spacing,
            warnings=list(endpoint_result.warnings),
        ),
        critical_path_feedback=CriticalPathFeedback(
            critical_path=sorted(critical_path_result.critical_path_room_ids),
            is_visually_distinguished=critical_path_result.is_visually_distinguished,
            warnings=list(critical_path_result.warnings),
        ),
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------

def _build_room_feedback(
    rooms: dict[str, str],
    room_names: dict[str, str],
) -> list[RoomStyleFeedbackEntry]:
    entries: list[RoomStyleFeedbackEntry] = []
    for room_id, role in rooms.items():
        style = _room_resolver.resolve(role)  # type: ignore[arg-type]
        entries.append(RoomStyleFeedbackEntry(
            room_id=room_id,
            room_name=room_names.get(room_id, room_id),
            role=role,
            style_key=style.key,
            expected_visual_priority=style.priority,
            actual_visual_priority=style.priority,
        ))
    return entries


def _build_connection_feedback(
    connections: list[tuple[str, str]],
) -> list[ConnectionStyleFeedbackEntry]:
    entries: list[ConnectionStyleFeedbackEntry] = []
    for connection_id, label in connections:
        style = _conn_resolver.resolve(label)
        entries.append(ConnectionStyleFeedbackEntry(
            connection_id=connection_id,
            label=label,
            connection_type=style.key,
            style_key=style.key,
        ))
    return entries


def _collect_room_warnings(
    rooms: dict[str, str],
    config: VisualHierarchyConfig,
    warnings: list[str],
) -> None:
    roles = set(rooms.values())
    if "unknown" in roles:
        warnings.append("MISSING_SEMANTIC_ROLE")
    if not config.style_room_roles:
        if "hub" in roles:
            warnings.append("HUB_NOT_EMPHASIZED")
        if "boss" in roles:
            warnings.append("BOSS_NOT_EMPHASIZED")


def _collect_connection_warnings(
    connections: list[tuple[str, str]],
    config: VisualHierarchyConfig,
    warnings: list[str],
) -> None:
    labels = {label for _, label in connections}
    if not config.style_secret_connections:
        if labels & _SECRET_LABELS:
            warnings.append("SECRET_CONNECTION_NOT_DISTINCT")
    if not config.enable_connection_markers:
        if labels & _VERTICAL_LABELS:
            warnings.append("VERTICAL_CONNECTION_NOT_DISTINCT")


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

def _compute_semantic_score(
    room_fb: list[RoomStyleFeedbackEntry],
    conn_fb: list[ConnectionStyleFeedbackEntry],
    endpoint_result: EndpointEmphasisResult,
    critical_path_result: CriticalPathPresentationResult,
) -> float:
    if room_fb:
        high_rooms = sum(1 for e in room_fb if e.expected_visual_priority != "low")
        room_score = high_rooms / len(room_fb)
    else:
        room_score = 1.0

    if conn_fb:
        styled_conns = sum(1 for e in conn_fb if e.style_key != "normal")
        conn_score = styled_conns / len(conn_fb)
    else:
        conn_score = 1.0

    endpoint_score = 1.0 if endpoint_result.is_emphasized else 0.0
    cp_score = 1.0 if critical_path_result.is_visually_distinguished else 0.0

    raw = room_score * 0.35 + conn_score * 0.15 + endpoint_score * 0.25 + cp_score * 0.25
    return round(raw * 100, 1)
