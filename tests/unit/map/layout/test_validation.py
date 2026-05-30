"""Tests for dungeon_daddy.map.dungeon_layout.validation."""
from __future__ import annotations

import json
from pathlib import Path

from dungeon_daddy.map.dungeon_layout.models import LabelBox, LayoutBounds, RoomRect, RoutedEdge
from dungeon_daddy.map.dungeon_layout.validation import (
    validate_layout,
    write_feedback_report,
    write_summary,
)
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_feedback import (
    CriticalPathFeedback,
    EndpointFeedback,
    VisualHierarchyFeedbackReport,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _room(room_id: str, x: float, y: float, w: float = 100.0, h: float = 60.0) -> RoomRect:
    return RoomRect(room_id=room_id, x=x, y=y, w=w, h=h)


def _edge(
    connection_id: str,
    points: list[tuple[float, float]],
    score: float = 1.0,
) -> RoutedEdge:
    return RoutedEdge(
        connection_id=connection_id,
        points=points,
        source_port="src",
        target_port="tgt",
        score=score,
    )


def _bounds(min_x: float, min_y: float, max_x: float, max_y: float) -> LayoutBounds:
    return LayoutBounds(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)


def _minimal_layout(
    rooms: dict[str, RoomRect] | None = None,
    edges: list[RoutedEdge] | None = None,
    labels: list[LabelBox] | None = None,
    bounds: LayoutBounds | None = None,
    roles: dict[str, str] | None = None,
) -> dict:
    r = rooms or {"a": _room("a", 0, 0)}
    return dict(
        fixture_name="test",
        seed=42,
        template="linear",
        template_confidence=0.9,
        roles=roles or {"a": "entrance"},
        critical_path=list(r.keys())[:1],
        optional_branches=[],
        rooms=r,
        edges=edges or [],
        labels=labels or [],
        bounds=bounds or _bounds(0, 0, 200, 100),
    )


# ---------------------------------------------------------------------------
# Cycle 1 — tracer: validate_layout returns a LayoutFeedbackReport
# ---------------------------------------------------------------------------

def test_validate_layout_returns_report_with_fixture_name_and_seed() -> None:
    report = validate_layout(**_minimal_layout())
    assert report.fixture_name == "test"
    assert report.seed == 42


# ---------------------------------------------------------------------------
# Cycle 2 — non-overlapping rooms → room_overlap_count == 0
# ---------------------------------------------------------------------------

def test_non_overlapping_rooms_have_zero_overlap_count() -> None:
    rooms = {"a": _room("a", 0, 0), "b": _room("b", 200, 0)}
    report = validate_layout(**_minimal_layout(rooms=rooms))
    assert report.layout_metrics.room_overlap_count == 0
    assert not any(w.category == "ROOM_OVERLAP" for w in report.warnings)


# ---------------------------------------------------------------------------
# Cycle 3 — overlapping rooms → room_overlap_count == 1 + ROOM_OVERLAP warning
# ---------------------------------------------------------------------------

def test_overlapping_rooms_detected_and_warned() -> None:
    # "a" occupies x 0–100, "b" starts at x 50 (overlaps by 50 px)
    rooms = {"a": _room("a", 0, 0), "b": _room("b", 50, 0)}
    report = validate_layout(**_minimal_layout(rooms=rooms))
    assert report.layout_metrics.room_overlap_count == 1
    assert any(w.category == "ROOM_OVERLAP" for w in report.warnings)


# ---------------------------------------------------------------------------
# Cycle 4 — clean route → illegal_connection_crossing_count == 0
# ---------------------------------------------------------------------------

def test_clear_connection_has_zero_illegal_crossings() -> None:
    rooms = {"a": _room("a", 0, 0), "b": _room("b", 300, 0)}
    # Route goes straight between the two rooms, no obstacle
    edges = [_edge("a→b", [(100.0, 30.0), (300.0, 30.0)])]
    report = validate_layout(**_minimal_layout(rooms=rooms, edges=edges))
    assert report.layout_metrics.illegal_connection_crossing_count == 0


# ---------------------------------------------------------------------------
# Cycle 5 — route through obstacle room → count == 1 + ILLEGAL_ROOM_CROSSING
# ---------------------------------------------------------------------------

def test_route_through_unrelated_room_is_detected() -> None:
    rooms = {
        "a":    _room("a",     0,   0, w=100, h=60),
        "b":    _room("b",     300, 0, w=100, h=60),
        "wall": _room("wall",  150, 0, w=60,  h=60),  # sits between a and b
    }
    # Route passes through "wall" (x 150–210)
    edges = [_edge("a→b", [(100.0, 30.0), (300.0, 30.0)])]
    report = validate_layout(**_minimal_layout(rooms=rooms, edges=edges))
    assert report.layout_metrics.illegal_connection_crossing_count == 1
    assert any(w.category == "ILLEGAL_ROOM_CROSSING" for w in report.warnings)


# ---------------------------------------------------------------------------
# Cycle 6 — bounds that contain all rooms → contains_all_rooms True, no warning
# ---------------------------------------------------------------------------

def test_bounds_containing_all_rooms_reports_no_camera_warning() -> None:
    rooms = {"a": _room("a", 10, 10, w=80, h=50)}
    bounds = _bounds(0, 0, 200, 100)  # room fits entirely inside
    report = validate_layout(**_minimal_layout(rooms=rooms, bounds=bounds))
    assert report.camera_feedback.contains_all_rooms is True
    assert not any(w.category == "CAMERA_BOUNDS_INCOMPLETE" for w in report.warnings)


# ---------------------------------------------------------------------------
# Cycle 7 — bounds too small for a room → CAMERA_BOUNDS_INCOMPLETE warning
# ---------------------------------------------------------------------------

def test_bounds_excluding_a_room_adds_camera_warning() -> None:
    rooms = {"a": _room("a", 0, 0, w=300, h=100)}
    bounds = _bounds(0, 0, 100, 100)  # room extends to x=300, bounds only to x=100
    report = validate_layout(**_minimal_layout(rooms=rooms, bounds=bounds))
    assert report.camera_feedback.contains_all_rooms is False
    assert any(w.category == "CAMERA_BOUNDS_INCOMPLETE" for w in report.warnings)


# ---------------------------------------------------------------------------
# Cycle 8 — route with detour_ratio > 2.5 → EXCESSIVE_DETOUR warning
# ---------------------------------------------------------------------------

def test_high_detour_ratio_adds_excessive_detour_warning() -> None:
    # Direct distance A→B is 100 px; route takes a huge rectangular detour (600 px total)
    edges = [_edge("a→b", [(0.0, 0.0), (0.0, 300.0), (100.0, 300.0), (100.0, 0.0)])]
    report = validate_layout(**_minimal_layout(edges=edges))
    assert report.layout_metrics.excessive_detour_count == 1
    assert any(w.category == "EXCESSIVE_DETOUR" for w in report.warnings)


def test_short_direct_route_has_no_excessive_detour_warning() -> None:
    edges = [_edge("a→b", [(0.0, 0.0), (100.0, 0.0), (100.0, 50.0)])]
    report = validate_layout(**_minimal_layout(edges=edges))
    assert report.layout_metrics.excessive_detour_count == 0
    assert not any(w.category == "EXCESSIVE_DETOUR" for w in report.warnings)


# ---------------------------------------------------------------------------
# Cycle 9 — missing entrance/objective role warnings
# ---------------------------------------------------------------------------

def test_no_entrance_role_adds_missing_entrance_warning() -> None:
    roles = {"a": "hub", "b": "boss"}
    report = validate_layout(**_minimal_layout(roles=roles))
    assert any(w.category == "MISSING_ENTRANCE_ROLE" for w in report.warnings)


def test_no_objective_role_adds_missing_objective_warning() -> None:
    roles = {"a": "entrance", "b": "side_room"}
    report = validate_layout(**_minimal_layout(roles=roles))
    assert any(w.category == "MISSING_OBJECTIVE_ROLE" for w in report.warnings)


def test_roles_with_entrance_and_boss_have_no_missing_role_warnings() -> None:
    roles = {"a": "entrance", "b": "boss"}
    report = validate_layout(**_minimal_layout(roles=roles))
    assert not any(w.category == "MISSING_ENTRANCE_ROLE" for w in report.warnings)
    assert not any(w.category == "MISSING_OBJECTIVE_ROLE" for w in report.warnings)


# ---------------------------------------------------------------------------
# Cycle 10 — write_feedback_report writes valid JSON to output dir
# ---------------------------------------------------------------------------

def test_write_feedback_report_creates_json_file(tmp_path: Path) -> None:
    report = validate_layout(**_minimal_layout())
    out_file = write_feedback_report(report, tmp_path)
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["fixture_name"] == "test"
    assert data["seed"] == 42
    assert "layout_metrics" in data


def test_write_feedback_report_filename_matches_fixture_name(tmp_path: Path) -> None:
    layout = _minimal_layout()
    layout["fixture_name"] = "my_dungeon_l1"
    report = validate_layout(**layout)
    out_file = write_feedback_report(report, tmp_path)
    assert out_file.name == "my_dungeon_l1.layout_feedback.json"


# ---------------------------------------------------------------------------
# Cycle 11 — write_summary creates Markdown summary with table row per report
# ---------------------------------------------------------------------------

def test_write_summary_creates_markdown_file(tmp_path: Path) -> None:
    report = validate_layout(**_minimal_layout())
    out_file = write_summary([report], tmp_path)
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "# Layout Feedback Summary" in content
    assert "test" in content  # fixture name in table


def test_write_summary_includes_pass_for_clean_layout(tmp_path: Path) -> None:
    rooms = {"a": _room("a", 0, 0), "b": _room("b", 300, 0)}
    report = validate_layout(**_minimal_layout(rooms=rooms))
    out_file = write_summary([report], tmp_path)
    content = out_file.read_text(encoding="utf-8")
    assert "PASS" in content


def test_write_summary_includes_fail_for_overlapping_rooms(tmp_path: Path) -> None:
    rooms = {"a": _room("a", 0, 0), "b": _room("b", 50, 0)}
    report = validate_layout(**_minimal_layout(rooms=rooms))
    out_file = write_summary([report], tmp_path)
    content = out_file.read_text(encoding="utf-8")
    assert "FAIL" in content


# ---------------------------------------------------------------------------
# Phase 2 helper
# ---------------------------------------------------------------------------

def _minimal_visual_report(
    semantic_score: float = 75.0,
    warnings: list[str] | None = None,
) -> VisualHierarchyFeedbackReport:
    return VisualHierarchyFeedbackReport(
        roles_styled=True,
        connection_styles_applied=False,
        critical_path_emphasized=False,
        endpoint_emphasized=False,
        shape_grammar_applied=False,
        semantic_score=semantic_score,
        room_style_feedback=[],
        connection_style_feedback=[],
        endpoint_feedback=EndpointFeedback(
            endpoint_room_id=None,
            endpoint_role=None,
            is_emphasized=False,
            has_sufficient_spacing=True,
        ),
        critical_path_feedback=CriticalPathFeedback(
            critical_path=[],
            is_visually_distinguished=False,
        ),
        warnings=warnings or [],
    )


# ---------------------------------------------------------------------------
# Cycle 12 — write_summary with visual_reports → header includes "Semantic Score"
# ---------------------------------------------------------------------------

def test_write_summary_with_visual_reports_header_includes_semantic_score(tmp_path: Path) -> None:
    report = validate_layout(**_minimal_layout())
    visual = {"test": _minimal_visual_report(semantic_score=80.0)}
    out_file = write_summary([report], tmp_path, visual_reports=visual)
    content = out_file.read_text(encoding="utf-8")
    assert "Semantic Score" in content


# ---------------------------------------------------------------------------
# Cycle 13 — write_summary with visual_reports → row contains semantic_score value
# ---------------------------------------------------------------------------

def test_write_summary_with_visual_reports_row_contains_semantic_score_value(tmp_path: Path) -> None:
    report = validate_layout(**_minimal_layout())
    visual = {"test": _minimal_visual_report(semantic_score=87.5)}
    out_file = write_summary([report], tmp_path, visual_reports=visual)
    content = out_file.read_text(encoding="utf-8")
    assert "87.5" in content


# ---------------------------------------------------------------------------
# Cycle 14 — write_summary with visual_reports → header includes "Visual Warnings"
# ---------------------------------------------------------------------------

def test_write_summary_with_visual_reports_header_includes_visual_warnings(tmp_path: Path) -> None:
    report = validate_layout(**_minimal_layout())
    visual = {"test": _minimal_visual_report()}
    out_file = write_summary([report], tmp_path, visual_reports=visual)
    content = out_file.read_text(encoding="utf-8")
    assert "Visual Warnings" in content


# ---------------------------------------------------------------------------
# Cycle 15 — write_summary with visual_reports → row shows warnings count
# ---------------------------------------------------------------------------

def test_write_summary_with_visual_reports_row_shows_warning_count(tmp_path: Path) -> None:
    report = validate_layout(**_minimal_layout())
    visual = {"test": _minimal_visual_report(warnings=["W1", "W2", "W3"])}
    out_file = write_summary([report], tmp_path, visual_reports=visual)
    content = out_file.read_text(encoding="utf-8")
    # The table row for "test" should contain the count "3"
    assert "| 3 |" in content or "3" in content


# ---------------------------------------------------------------------------
# Cycle 16 — write_summary without visual_reports → Semantic Score shows "—"
# ---------------------------------------------------------------------------

def test_write_summary_without_visual_reports_semantic_score_shows_dash(tmp_path: Path) -> None:
    report = validate_layout(**_minimal_layout())
    out_file = write_summary([report], tmp_path)
    content = out_file.read_text(encoding="utf-8")
    assert "—" in content  # dash in Semantic Score column


# ---------------------------------------------------------------------------
# Cycle 17 — write_summary with visual_reports → Phase 2 checklist questions appear
# ---------------------------------------------------------------------------

def test_write_summary_with_visual_reports_includes_phase2_checklist_questions(tmp_path: Path) -> None:
    report = validate_layout(**_minimal_layout())
    visual = {"test": _minimal_visual_report()}
    out_file = write_summary([report], tmp_path, visual_reports=visual)
    content = out_file.read_text(encoding="utf-8")
    assert "boss/objective rooms visually more important" in content
    assert "secret/shortcut connections visually distinct" in content


# ---------------------------------------------------------------------------
# Cycle 18 — write_summary without visual_reports → Phase 2 questions absent
# ---------------------------------------------------------------------------

def test_write_summary_without_visual_reports_phase2_questions_absent(tmp_path: Path) -> None:
    report = validate_layout(**_minimal_layout())
    out_file = write_summary([report], tmp_path)
    content = out_file.read_text(encoding="utf-8")
    assert "boss/objective rooms visually more important" not in content


# ---------------------------------------------------------------------------
# Cycle 19 — write_feedback_report includes visual_hierarchy_feedback when set
# ---------------------------------------------------------------------------

def test_write_feedback_report_includes_visual_hierarchy_feedback_when_set(tmp_path: Path) -> None:
    report = validate_layout(**_minimal_layout())
    report.visual_hierarchy_feedback = _minimal_visual_report(semantic_score=72.0)
    out_file = write_feedback_report(report, tmp_path)
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "visual_hierarchy_feedback" in data
    assert data["visual_hierarchy_feedback"]["semantic_score"] == 72.0


def test_write_feedback_report_omits_visual_hierarchy_feedback_when_not_set(tmp_path: Path) -> None:
    report = validate_layout(**_minimal_layout())
    out_file = write_feedback_report(report, tmp_path)
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data.get("visual_hierarchy_feedback") is None
