"""Metadata quality feedback for the dungeon layout pipeline.

Measures how much explicit semantic metadata a floor carries vs. relying on
inference. Produces a MetadataQualityFeedback report and a Markdown summary row.
No Arcade dependency — pure Python / Pydantic.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from dungeon_daddy.data.models import Level
from dungeon_daddy.map.dungeon_layout.metadata_validator import validate_metadata
from dungeon_daddy.map.dungeon_layout.semantics import classify_all_roles

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class MetadataQualityFeedback(BaseModel):
    explicit_room_role_count: int
    inferred_room_role_count: int
    unknown_room_role_count: int
    explicit_connection_style_count: int
    inferred_connection_style_count: int
    explicit_critical_path: bool
    explicit_endpoint: bool
    explicit_entrance: bool
    metadata_score: float
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_metadata_quality_feedback(level: Level) -> MetadataQualityFeedback:
    """Return metadata quality feedback for *level*."""
    roles = classify_all_roles(level)

    explicit_room = sum(1 for r in level.rooms if r.layout_role is not None)
    unknown_room = sum(1 for rid, role in roles.items() if role == "unknown")
    inferred_room = len(level.rooms) - explicit_room - unknown_room

    explicit_conn = sum(
        1 for c in level.connections
        if c.connection_style is not None or c.layout_connection_role is not None
    )
    inferred_conn = len(level.connections) - explicit_conn

    meta = level.layout_metadata
    has_explicit_cp = meta is not None and len(meta.critical_path) > 0
    has_explicit_endpoint = meta is not None and meta.endpoint_room_id is not None
    has_explicit_entrance = meta is not None and meta.entrance_room_id is not None

    score = _compute_metadata_score(
        level=level,
        explicit_room=explicit_room,
        unknown_room=unknown_room,
        explicit_conn=explicit_conn,
        has_explicit_cp=has_explicit_cp,
        has_explicit_endpoint=has_explicit_endpoint,
        has_explicit_entrance=has_explicit_entrance,
    )

    raw_warnings = validate_metadata(level)
    warning_messages = [w.message for w in raw_warnings]

    return MetadataQualityFeedback(
        explicit_room_role_count=explicit_room,
        inferred_room_role_count=inferred_room,
        unknown_room_role_count=unknown_room,
        explicit_connection_style_count=explicit_conn,
        inferred_connection_style_count=inferred_conn,
        explicit_critical_path=has_explicit_cp,
        explicit_endpoint=has_explicit_endpoint,
        explicit_entrance=has_explicit_entrance,
        metadata_score=score,
        warnings=warning_messages,
    )


def format_summary_row(
    dungeon_name: str,
    level_name: str,
    geometry_score: float,
    semantic_score: float,
    feedback: MetadataQualityFeedback,
) -> str:
    """Return a Markdown table row for the layout feedback summary."""
    label = f"{dungeon_name} / {level_name}"
    status = (
        "PASS"
        if feedback.unknown_room_role_count == 0 and feedback.metadata_score >= 50.0
        else "WARN"
    )
    warning_count = len(feedback.warnings)
    return (
        f"| {label} "
        f"| {geometry_score:.1f} "
        f"| {semantic_score:.1f} "
        f"| {feedback.metadata_score:.1f} "
        f"| {feedback.unknown_room_role_count} "
        f"| {'yes' if feedback.explicit_entrance else 'no'} "
        f"| {'yes' if feedback.explicit_endpoint else 'no'} "
        f"| {'yes' if feedback.explicit_critical_path else 'no'} "
        f"| {warning_count} "
        f"| {status} |"
    )


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

def _compute_metadata_score(
    level: Level,
    explicit_room: int,
    unknown_room: int,
    explicit_conn: int,
    has_explicit_cp: bool,
    has_explicit_endpoint: bool,
    has_explicit_entrance: bool,
) -> float:
    """Return a 0–100 metadata quality score."""
    total_rooms = len(level.rooms)
    total_conns = len(level.connections)

    room_score = (explicit_room / total_rooms) if total_rooms else 1.0
    unknown_penalty = (unknown_room / total_rooms) if total_rooms else 0.0
    conn_score = (explicit_conn / total_conns) if total_conns else 1.0
    flag_score = (
        (1.0 if has_explicit_entrance else 0.0)
        + (1.0 if has_explicit_endpoint else 0.0)
        + (1.0 if has_explicit_cp else 0.0)
    ) / 3.0

    raw = (
        room_score * 0.35
        - unknown_penalty * 0.15
        + conn_score * 0.15
        + flag_score * 0.50
    )
    return round(max(0.0, min(100.0, raw * 100)), 1)
