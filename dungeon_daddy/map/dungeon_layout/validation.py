"""Layout validation and feedback reporting for the dungeon layout pipeline.

Runs invariant checks (hard failures) and collects diagnostic warnings.
No Arcade dependency — pure Python / Pydantic.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from dungeon_daddy.map.dungeon_layout.models import (
    LabelBox,
    LayoutBounds,
    RoomRect,
    RoutedEdge,
)
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_feedback import VisualHierarchyFeedbackReport

# ---------------------------------------------------------------------------
# Warning model
# ---------------------------------------------------------------------------

class LayoutWarning(BaseModel):
    category: str
    severity: str = "medium"
    message: str
    connection_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Sub-report models
# ---------------------------------------------------------------------------

class LayoutMetrics(BaseModel):
    room_overlap_count: int = 0
    illegal_connection_crossing_count: int = 0
    edge_crossing_count: int = 0
    average_route_length: float = 0.0
    average_bend_count: float = 0.0
    max_bend_count: int = 0
    label_overlap_count: int = 0
    offscreen_geometry_count: int = 0
    excessive_detour_count: int = 0
    layout_score: float = 0.0


class RouteFeedback(BaseModel):
    connection_id: str
    style: str = "normal"
    source_port: str
    target_port: str
    bend_count: int
    route_length: float
    direct_distance: float
    detour_ratio: float
    score: float
    warnings: list[str] = Field(default_factory=list)


class LabelFeedback(BaseModel):
    connection_id: str
    label: str
    placement_segment_index: int = 0
    overlaps_room: bool = False
    overlaps_other_label: bool = False
    near_viewport_edge: bool = False
    score: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class CameraFeedback(BaseModel):
    fit_bounds: tuple[float, float, float, float]
    contains_all_rooms: bool
    contains_all_routes: bool
    contains_all_labels: bool
    margin_applied: float = 0.0


# ---------------------------------------------------------------------------
# Top-level feedback report
# ---------------------------------------------------------------------------

class LayoutFeedbackReport(BaseModel):
    fixture_name: str
    seed: int
    layout_template: str
    template_confidence: float
    room_roles: dict[str, str]
    critical_path: list[str]
    optional_branches: list[list[str]]
    layout_metrics: LayoutMetrics
    route_feedback: list[RouteFeedback]
    label_feedback: list[LabelFeedback]
    camera_feedback: CameraFeedback
    warnings: list[LayoutWarning] = Field(default_factory=list)
    human_review_notes: list[str] = Field(default_factory=list)
    visual_hierarchy_feedback: VisualHierarchyFeedbackReport | None = None
    metadata_quality_feedback: MetadataQualityFeedback | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_layout(
    fixture_name: str,
    seed: int,
    template: str,
    template_confidence: float,
    roles: dict[str, str],
    critical_path: list[str],
    optional_branches: list[list[str]],
    rooms: dict[str, RoomRect],
    edges: list[RoutedEdge],
    labels: list[LabelBox],
    bounds: LayoutBounds,
) -> LayoutFeedbackReport:
    """Run invariant checks and collect feedback for a completed layout."""
    warnings: list[LayoutWarning] = []

    metrics = _compute_metrics(rooms, edges, labels, bounds, warnings)
    route_fb = _route_feedback(edges, warnings)
    label_fb = _label_feedback(labels, rooms)
    camera_fb = _camera_feedback(bounds, rooms, edges, labels, warnings)

    _check_role_warnings(roles, warnings)

    return LayoutFeedbackReport(
        fixture_name=fixture_name,
        seed=seed,
        layout_template=template,
        template_confidence=template_confidence,
        room_roles=roles,
        critical_path=critical_path,
        optional_branches=optional_branches,
        layout_metrics=metrics,
        route_feedback=route_fb,
        label_feedback=label_fb,
        camera_feedback=camera_fb,
        warnings=warnings,
    )


def write_feedback_report(report: LayoutFeedbackReport, output_dir: Path) -> Path:
    """Write *report* as JSON to *output_dir*/<fixture_name>.layout_feedback.json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{report.fixture_name}.layout_feedback.json"
    path.write_text(
        json.dumps(report.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def write_summary(
    reports: list[LayoutFeedbackReport],
    output_dir: Path,
    visual_reports: dict[str, "VisualHierarchyFeedbackReport"] | None = None,
) -> Path:
    """Write a Markdown summary of all *reports* to *output_dir*/layout_feedback_summary.md."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "layout_feedback_summary.md"

    lines = [
        "# Layout Feedback Summary\n",
        "| Fixture | Template | Critical Path | Semantic Score | Geometry Score | Visual Warnings | Status |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for r in reports:
        cp = " → ".join(r.critical_path) if r.critical_path else "—"
        m = r.layout_metrics
        hard_fail = m.room_overlap_count > 0 or m.illegal_connection_crossing_count > 0
        status = "FAIL" if hard_fail else "PASS"
        vr = visual_reports.get(r.fixture_name) if visual_reports else None
        sem_score = f"{vr.semantic_score:.1f}" if vr is not None else "—"
        vis_warns = str(len(vr.warnings)) if vr is not None else "—"
        lines.append(
            f"| {r.fixture_name} | {r.layout_template} | {cp} "
            f"| {sem_score} | {m.layout_score:.1f} | {vis_warns} | {status} |"
        )

    lines.append("")
    for r in reports:
        vr = visual_reports.get(r.fixture_name) if visual_reports else None
        lines += _human_review_checklist(r, vr)

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Internal — metrics
# ---------------------------------------------------------------------------

def _compute_metrics(
    rooms: dict[str, RoomRect],
    edges: list[RoutedEdge],
    labels: list[LabelBox],
    bounds: LayoutBounds,
    warnings: list[LayoutWarning],
) -> LayoutMetrics:
    overlap_count = _count_room_overlaps(rooms, warnings)
    illegal_count = _count_illegal_crossings(rooms, edges, warnings)
    edge_cross_count = _count_edge_crossings(edges, warnings)
    label_overlap = _count_label_overlaps(labels, rooms, warnings)
    offscreen = _count_offscreen(rooms, edges, labels, bounds, warnings)
    excessive_detour = _count_excessive_detours(edges, warnings)

    lengths = [_route_length(e.points) for e in edges] if edges else []
    bends = [e.bend_count for e in edges] if edges else []

    avg_len = sum(lengths) / len(lengths) if lengths else 0.0
    avg_bends = sum(bends) / len(bends) if bends else 0.0
    max_bends = max(bends) if bends else 0

    penalty = (
        overlap_count * 50
        + illegal_count * 100
        + edge_cross_count * 10
        + label_overlap * 5
        + offscreen * 20
        + excessive_detour * 15
    )
    score = max(0.0, 100.0 - penalty)

    return LayoutMetrics(
        room_overlap_count=overlap_count,
        illegal_connection_crossing_count=illegal_count,
        edge_crossing_count=edge_cross_count,
        average_route_length=round(avg_len, 2),
        average_bend_count=round(avg_bends, 2),
        max_bend_count=max_bends,
        label_overlap_count=label_overlap,
        offscreen_geometry_count=offscreen,
        excessive_detour_count=excessive_detour,
        layout_score=round(score, 1),
    )


def _count_room_overlaps(
    rooms: dict[str, RoomRect],
    warnings: list[LayoutWarning],
) -> int:
    room_list = list(rooms.values())
    count = 0
    for i in range(len(room_list)):
        for j in range(i + 1, len(room_list)):
            if _rects_overlap(room_list[i], room_list[j]):
                count += 1
                warnings.append(LayoutWarning(
                    category="ROOM_OVERLAP",
                    severity="high",
                    message=(
                        f"Rooms '{room_list[i].room_id}' and '{room_list[j].room_id}' overlap."
                    ),
                ))
    return count


def _count_illegal_crossings(
    rooms: dict[str, RoomRect],
    edges: list[RoutedEdge],
    warnings: list[LayoutWarning],
) -> int:
    count = 0
    for edge in edges:
        from_id, to_id = _parse_connection_id(edge.connection_id)
        exclude = {from_id, to_id}
        for rid, rect in rooms.items():
            if rid in exclude:
                continue
            if _polyline_intersects_rect(edge.points, rect):
                count += 1
                warnings.append(LayoutWarning(
                    category="ILLEGAL_ROOM_CROSSING",
                    severity="high",
                    message=(
                        f"Connection '{edge.connection_id}' passes through room '{rid}'."
                    ),
                    connection_id=edge.connection_id,
                ))
                break  # count once per edge
    return count


def _count_edge_crossings(
    edges: list[RoutedEdge],
    warnings: list[LayoutWarning],
) -> int:
    count = 0
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            if _polylines_cross(edges[i].points, edges[j].points):
                count += 1
                warnings.append(LayoutWarning(
                    category="EDGE_CROSSING",
                    severity="low",
                    message=(
                        f"Connections '{edges[i].connection_id}' and "
                        f"'{edges[j].connection_id}' cross."
                    ),
                ))
    return count


def _count_label_overlaps(
    labels: list[LabelBox],
    rooms: dict[str, RoomRect],
    warnings: list[LayoutWarning],
) -> int:
    count = 0
    for lb in labels:
        for room in rooms.values():
            if _label_overlaps_room(lb, room):
                count += 1
                warnings.append(LayoutWarning(
                    category="LABEL_ROOM_OVERLAP",
                    severity="medium",
                    message=f"Label for '{lb.connection_id}' overlaps room '{room.room_id}'.",
                    connection_id=lb.connection_id,
                ))
                break
    return count


def _count_offscreen(
    rooms: dict[str, RoomRect],
    edges: list[RoutedEdge],
    labels: list[LabelBox],
    bounds: LayoutBounds,
    warnings: list[LayoutWarning],
) -> int:
    count = 0
    for r in rooms.values():
        if not _room_in_bounds(r, bounds):
            count += 1
            warnings.append(LayoutWarning(
                category="OFFSCREEN_GEOMETRY",
                severity="medium",
                message=f"Room '{r.room_id}' extends outside layout bounds.",
            ))
    return count


def _count_excessive_detours(
    edges: list[RoutedEdge],
    warnings: list[LayoutWarning],
    threshold: float = 2.5,
) -> int:
    count = 0
    for edge in edges:
        if len(edge.points) < 2:
            continue
        direct = math.dist(edge.points[0], edge.points[-1])
        if direct < 1.0:
            continue
        length = _route_length(edge.points)
        ratio = length / direct
        if ratio > threshold:
            count += 1
            warnings.append(LayoutWarning(
                category="EXCESSIVE_DETOUR",
                severity="medium",
                message=(
                    f"Connection '{edge.connection_id}' detour ratio is {ratio:.2f}, "
                    f"which may create a large rectangular corridor artifact."
                ),
                connection_id=edge.connection_id,
                data={
                    "route_length": round(length, 2),
                    "direct_distance": round(direct, 2),
                    "detour_ratio": round(ratio, 2),
                },
            ))
    return count


def _check_role_warnings(
    roles: dict[str, str],
    warnings: list[LayoutWarning],
) -> None:
    role_values = set(roles.values())
    if "entrance" not in role_values:
        warnings.append(LayoutWarning(
            category="MISSING_ENTRANCE_ROLE",
            severity="medium",
            message="No room has the 'entrance' role — layout start is ambiguous.",
        ))
    objective_roles = {"boss", "objective", "exit"}
    if not (role_values & objective_roles):
        warnings.append(LayoutWarning(
            category="MISSING_OBJECTIVE_ROLE",
            severity="medium",
            message="No room has a boss/objective/exit role — layout destination is ambiguous.",
        ))


# ---------------------------------------------------------------------------
# Internal — per-edge/label feedback
# ---------------------------------------------------------------------------

def _route_feedback(
    edges: list[RoutedEdge],
    warnings: list[LayoutWarning],
) -> list[RouteFeedback]:
    result: list[RouteFeedback] = []
    for edge in edges:
        points = edge.points
        length = _route_length(points)
        direct = math.dist(points[0], points[-1]) if len(points) >= 2 else 0.0
        ratio = (length / direct) if direct > 0.1 else 1.0
        edge_warns: list[str] = []
        if ratio > 2.5:
            edge_warns.append("EXCESSIVE_DETOUR")
        if edge.bend_count > 3:
            edge_warns.append("TOO_MANY_BENDS")
        result.append(RouteFeedback(
            connection_id=edge.connection_id,
            source_port=edge.source_port,
            target_port=edge.target_port,
            bend_count=edge.bend_count,
            route_length=round(length, 2),
            direct_distance=round(direct, 2),
            detour_ratio=round(ratio, 2),
            score=edge.score,
            warnings=edge_warns,
        ))
    return result


def _label_feedback(
    labels: list[LabelBox],
    rooms: dict[str, RoomRect],
) -> list[LabelFeedback]:
    result: list[LabelFeedback] = []
    for lb in labels:
        overlaps_room = any(_label_overlaps_room(lb, r) for r in rooms.values())
        result.append(LabelFeedback(
            connection_id=lb.connection_id,
            label=lb.text,
            overlaps_room=overlaps_room,
        ))
    return result


def _camera_feedback(
    bounds: LayoutBounds,
    rooms: dict[str, RoomRect],
    edges: list[RoutedEdge],
    labels: list[LabelBox],
    warnings: list[LayoutWarning],
) -> CameraFeedback:
    all_rooms_in = all(_room_in_bounds(r, bounds) for r in rooms.values())
    all_routes_in = all(
        all(
            bounds.min_x <= px <= bounds.max_x and bounds.min_y <= py <= bounds.max_y
            for px, py in e.points
        )
        for e in edges
    )
    all_labels_in = all(
        bounds.min_x <= lb.x and lb.right <= bounds.max_x
        and bounds.min_y <= lb.y and lb.top <= bounds.max_y
        for lb in labels
    )

    if not all_rooms_in or not all_routes_in or not all_labels_in:
        warnings.append(LayoutWarning(
            category="CAMERA_BOUNDS_INCOMPLETE",
            severity="high",
            message="Camera bounds do not contain all layout geometry.",
        ))

    return CameraFeedback(
        fit_bounds=(bounds.min_x, bounds.min_y, bounds.max_x, bounds.max_y),
        contains_all_rooms=all_rooms_in,
        contains_all_routes=all_routes_in,
        contains_all_labels=all_labels_in,
    )


# ---------------------------------------------------------------------------
# Internal — geometry helpers
# ---------------------------------------------------------------------------

def _rects_overlap(a: RoomRect, b: RoomRect) -> bool:
    return (
        a.left < b.right
        and a.right > b.left
        and a.bottom < b.top
        and a.top > b.bottom
    )


def _room_in_bounds(room: RoomRect, bounds: LayoutBounds) -> bool:
    return (
        room.left >= bounds.min_x
        and room.right <= bounds.max_x
        and room.bottom >= bounds.min_y
        and room.top <= bounds.max_y
    )


def _label_overlaps_room(lb: LabelBox, room: RoomRect) -> bool:
    return (
        lb.x < room.right
        and lb.right > room.left
        and lb.y < room.top
        and lb.top > room.bottom
    )


def _route_length(points: list[tuple[float, float]]) -> float:
    return sum(math.dist(points[i], points[i + 1]) for i in range(len(points) - 1))


def _parse_connection_id(connection_id: str) -> tuple[str, str]:
    """Parse 'a→b' into ('a', 'b'). Falls back to (connection_id, '') on failure."""
    if "→" in connection_id:
        parts = connection_id.split("→", 1)
        return parts[0], parts[1]
    return connection_id, ""


def _polyline_intersects_rect(
    points: list[tuple[float, float]],
    rect: RoomRect,
) -> bool:
    for i in range(len(points) - 1):
        if _segment_intersects_rect(points[i], points[i + 1], rect):
            return True
    return False


def _segment_intersects_rect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    rect: RoomRect,
) -> bool:
    x1, y1 = p1
    x2, y2 = p2
    seg_left   = min(x1, x2)
    seg_right  = max(x1, x2)
    seg_bottom = min(y1, y2)
    seg_top    = max(y1, y2)
    return (
        seg_left   < rect.right
        and seg_right  > rect.left
        and seg_bottom < rect.top
        and seg_top    > rect.bottom
    )


def _segments_cross(
    a1: tuple[float, float], a2: tuple[float, float],
    b1: tuple[float, float], b2: tuple[float, float],
) -> bool:
    """Return True if axis-aligned segment a crosses axis-aligned segment b (not at endpoints)."""
    # Both segments must be axis-aligned (orthogonal routing output)
    ax1, ay1 = min(a1[0], a2[0]), min(a1[1], a2[1])
    ax2, ay2 = max(a1[0], a2[0]), max(a1[1], a2[1])
    bx1, by1 = min(b1[0], b2[0]), min(b1[1], b2[1])
    bx2, by2 = max(b1[0], b2[0]), max(b1[1], b2[1])

    a_horiz = (ay1 == ay2)
    b_horiz = (by1 == by2)

    if a_horiz == b_horiz:
        return False  # parallel segments don't cross

    # One horizontal, one vertical
    if a_horiz:
        h_y = ay1
        h_x1, h_x2 = ax1, ax2
        v_x = bx1
        v_y1, v_y2 = by1, by2
    else:
        h_y = by1
        h_x1, h_x2 = bx1, bx2
        v_x = ax1
        v_y1, v_y2 = ay1, ay2

    return h_x1 < v_x < h_x2 and v_y1 < h_y < v_y2


def _polylines_cross(
    pts_a: list[tuple[float, float]],
    pts_b: list[tuple[float, float]],
) -> bool:
    for i in range(len(pts_a) - 1):
        for j in range(len(pts_b) - 1):
            if _segments_cross(pts_a[i], pts_a[i + 1], pts_b[j], pts_b[j + 1]):
                return True
    return False


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def _human_review_checklist(
    report: LayoutFeedbackReport,
    visual_report: "VisualHierarchyFeedbackReport | None" = None,
) -> list[str]:
    name = report.fixture_name
    lines = [
        f"\n### Human Review: {name}\n",
        "- [ ] Does the entrance feel like the start of the map?",
        "- [ ] Does the objective/exit feel like the destination?",
        "- [ ] Are normal connections readable as corridors rather than arbitrary graph lines?",
        "- [ ] Are there any giant rectangular detours?",
        "- [ ] Do connection labels sit in understandable places?",
        "- [ ] Does the camera frame the entire floor on load?",
        "- [ ] Did any layout choice make the map uglier even though tests passed?",
    ]
    if visual_report is not None:
        lines += [
            "- [ ] Are boss/objective rooms visually more important than ordinary rooms?",
            "- [ ] Are hub rooms visually stable and central?",
            "- [ ] Are key rooms visually distinct without overpowering the map?",
            "- [ ] Are locked rooms or locked connections understandable?",
            "- [ ] Are secret/shortcut connections visually distinct from normal corridors?",
            "- [ ] Are vertical travel connections visually distinct?",
            "- [ ] Does the critical path read more clearly than optional branches?",
            "- [ ] Did any Phase 2 styling make the map noisier or uglier?",
            "- [ ] Does Graph Mode remain cleaner and more useful than Grid Mode for overview reading?",
        ]
    return lines


# Resolve MetadataQualityFeedback forward reference after this module is fully loaded.
# The deferred import breaks the circular dependency:
#   validation → metadata_quality_feedback → metadata_validator → validation (LayoutWarning)
def _rebuild() -> None:
    from dungeon_daddy.map.dungeon_layout.metadata_quality_feedback import MetadataQualityFeedback  # noqa: F401
    LayoutFeedbackReport.model_rebuild()

_rebuild()
