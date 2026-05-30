"""Fixture-based integration tests for the full dungeon layout pipeline.

Runs semantics → seed_layout → ports → route_orthogonal → labels → camera_fit
→ validation on real dungeon JSON fixtures, asserts layout invariants, and
writes JSON feedback reports + a Markdown summary to test_outputs/layout_feedback/
and artifacts/layout/phase2/.
"""
from __future__ import annotations

import json
from pathlib import Path

from dungeon_daddy.data.models import Dungeon, Level
from dungeon_daddy.map.dungeon_layout.camera_fit import compute_layout_bounds
from dungeon_daddy.map.dungeon_layout.critical_path_style import CriticalPathPresenter
from dungeon_daddy.map.dungeon_layout.endpoint_emphasis import EndpointEmphasisDetector
from dungeon_daddy.map.dungeon_layout.labels import place_labels
from dungeon_daddy.map.dungeon_layout.metadata_quality_feedback import (
    generate_metadata_quality_feedback,
)
from dungeon_daddy.map.dungeon_layout.ports import generate_ports
from dungeon_daddy.map.dungeon_layout.route_orthogonal import route_connections
from dungeon_daddy.map.dungeon_layout.seed_layout import (
    compute_critical_path,
    compute_seed_layout,
)
from dungeon_daddy.map.dungeon_layout.semantics import classify_all_roles, classify_template
from dungeon_daddy.map.dungeon_layout.validation import (
    LayoutFeedbackReport,
    validate_layout,
    write_feedback_report,
    write_summary,
)
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_config import VisualHierarchyConfig
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_feedback import (
    VisualHierarchyFeedbackReport,
    generate_visual_hierarchy_feedback,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_FIXTURES = Path(__file__).parent.parent / "fixtures"
_OUTPUT_DIR = Path(__file__).parent.parent.parent / "test_outputs" / "layout_feedback"
_PHASE2_DIR = Path(__file__).parent.parent.parent / "artifacts" / "layout" / "phase2"

# ---------------------------------------------------------------------------
# Pipeline helper
# ---------------------------------------------------------------------------

def _run_pipeline(level: Level, fixture_name: str, seed: int = 42) -> LayoutFeedbackReport:
    """Drive the full layout pipeline for *level* and return a LayoutFeedbackReport."""
    # Filter out cross-level connections (e.g. stair_down to a room on another floor)
    room_ids = {r.id for r in level.rooms}
    connections = [c for c in level.connections
                   if c.from_room in room_ids and c.to_room in room_ids]

    roles = classify_all_roles(level)
    template = classify_template(level, roles)
    rooms = compute_seed_layout(level, roles, template)
    ports = generate_ports(rooms, connections)
    edges = route_connections(rooms, ports, connections)
    label_texts = {
        f"{c.from_room}→{c.to_room}": c.type for c in connections
    }
    label_boxes = place_labels(edges, rooms, label_texts)
    bounds = compute_layout_bounds(list(rooms.values()), edges, label_boxes, margin=80.0)
    critical_path = compute_critical_path(level, roles)

    report = validate_layout(
        fixture_name=fixture_name,
        seed=seed,
        template=template,
        template_confidence=0.8,
        roles=roles,
        critical_path=critical_path,
        optional_branches=[],
        rooms=rooms,
        edges=edges,
        labels=label_boxes,
        bounds=bounds,
    )

    config = VisualHierarchyConfig()
    explicit_endpoint_id = (
        level.layout_metadata.endpoint_room_id
        if level.layout_metadata is not None
        else None
    )
    endpoint_result = EndpointEmphasisDetector().detect(
        roles=roles,
        rooms=rooms,
        connections=connections,
        critical_path=critical_path or None,
        endpoint_room_id=explicit_endpoint_id,
    )
    cp_result = CriticalPathPresenter().present(
        critical_path=critical_path or None,
        emphasize_critical_path=config.emphasize_critical_path,
    )
    room_names = {r.id: r.name for r in level.rooms}
    conn_pairs = [(f"{c.from_room}→{c.to_room}", c.type) for c in connections]
    report.visual_hierarchy_feedback = generate_visual_hierarchy_feedback(
        rooms=roles,
        room_names=room_names,
        connections=conn_pairs,
        endpoint_result=endpoint_result,
        critical_path_result=cp_result,
        config=config,
    )
    report.metadata_quality_feedback = generate_metadata_quality_feedback(level)
    return report


def _load_dungeon(name: str) -> Dungeon:
    data = json.loads((_FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return Dungeon.model_validate(data)


# ---------------------------------------------------------------------------
# Crucible L1 — freeform layout, lock_key structure
# ---------------------------------------------------------------------------

def test_crucible_l1_pipeline_returns_report_with_correct_fixture_name() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[0]
    report = _run_pipeline(level, fixture_name="crucible_l1")
    assert report.fixture_name == "crucible_l1"
    assert report.layout_template in {"linear", "hub_spoke", "branch_merge", "lock_key", "boss_endcap", "loop", "freeform"}


def test_crucible_l1_has_no_room_overlaps() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[0]
    report = _run_pipeline(level, fixture_name="crucible_l1")
    assert report.layout_metrics.room_overlap_count == 0, (
        f"Rooms overlap: {[w.message for w in report.warnings if w.category == 'ROOM_OVERLAP']}"
    )


def test_crucible_l1_has_no_illegal_connection_crossings() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[0]
    report = _run_pipeline(level, fixture_name="crucible_l1")
    assert report.layout_metrics.illegal_connection_crossing_count == 0, (
        f"Illegal crossings: {[w.message for w in report.warnings if w.category == 'ILLEGAL_ROOM_CROSSING']}"
    )


def test_crucible_l1_camera_contains_all_rooms() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[0]
    report = _run_pipeline(level, fixture_name="crucible_l1")
    assert report.camera_feedback.contains_all_rooms is True


def test_crucible_l1_layout_is_deterministic() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[0]
    r1 = _run_pipeline(level, fixture_name="crucible_l1")
    r2 = _run_pipeline(level, fixture_name="crucible_l1")
    assert r1.room_roles == r2.room_roles
    assert r1.critical_path == r2.critical_path
    assert r1.layout_metrics.room_overlap_count == r2.layout_metrics.room_overlap_count


# ---------------------------------------------------------------------------
# Crucible L2 — hub_spoke structure
# ---------------------------------------------------------------------------

def test_crucible_l2_has_no_room_overlaps() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[1]
    report = _run_pipeline(level, fixture_name="crucible_l2")
    assert report.layout_metrics.room_overlap_count == 0, (
        f"Rooms overlap: {[w.message for w in report.warnings if w.category == 'ROOM_OVERLAP']}"
    )


def test_crucible_l2_has_no_illegal_connection_crossings() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[1]
    report = _run_pipeline(level, fixture_name="crucible_l2")
    assert report.layout_metrics.illegal_connection_crossing_count == 0, (
        f"Illegal crossings: {[w.message for w in report.warnings if w.category == 'ILLEGAL_ROOM_CROSSING']}"
    )


def test_crucible_l2_template_is_hub_spoke() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[1]
    report = _run_pipeline(level, fixture_name="crucible_l2")
    assert report.layout_template == "hub_spoke"


# ---------------------------------------------------------------------------
# Crucible L3 — secret_shortcut structure
# ---------------------------------------------------------------------------

def test_crucible_l3_has_no_room_overlaps() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[2]
    report = _run_pipeline(level, fixture_name="crucible_l3")
    assert report.layout_metrics.room_overlap_count == 0, (
        f"Rooms overlap: {[w.message for w in report.warnings if w.category == 'ROOM_OVERLAP']}"
    )


def test_crucible_l3_has_no_illegal_connection_crossings() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[2]
    report = _run_pipeline(level, fixture_name="crucible_l3")
    assert report.layout_metrics.illegal_connection_crossing_count == 0, (
        f"Illegal crossings: {[w.message for w in report.warnings if w.category == 'ILLEGAL_ROOM_CROSSING']}"
    )


# ---------------------------------------------------------------------------
# Tomb fixtures
# ---------------------------------------------------------------------------

def test_tomb_l1_has_no_room_overlaps() -> None:
    dungeon = _load_dungeon("tomb")
    level = dungeon.levels[0]
    report = _run_pipeline(level, fixture_name="tomb_l1")
    assert report.layout_metrics.room_overlap_count == 0, (
        f"Rooms overlap: {[w.message for w in report.warnings if w.category == 'ROOM_OVERLAP']}"
    )


def test_tomb_l1_has_no_illegal_connection_crossings() -> None:
    dungeon = _load_dungeon("tomb")
    level = dungeon.levels[0]
    report = _run_pipeline(level, fixture_name="tomb_l1")
    assert report.layout_metrics.illegal_connection_crossing_count == 0, (
        f"Illegal crossings: {[w.message for w in report.warnings if w.category == 'ILLEGAL_ROOM_CROSSING']}"
    )


# ---------------------------------------------------------------------------
# Feedback report output (all fixtures together)
# ---------------------------------------------------------------------------

def test_feedback_reports_written_to_disk_for_all_fixtures() -> None:
    crucible = _load_dungeon("crucible")
    tomb = _load_dungeon("tomb")

    fixture_specs = [
        (crucible.levels[0], "crucible_l1"),
        (crucible.levels[1], "crucible_l2"),
        (crucible.levels[2], "crucible_l3"),
        (tomb.levels[0],     "tomb_l1"),
    ]

    reports: list[LayoutFeedbackReport] = []
    visual_reports: dict[str, VisualHierarchyFeedbackReport] = {}

    for level, name in fixture_specs:
        report = _run_pipeline(level, fixture_name=name)
        reports.append(report)
        if report.visual_hierarchy_feedback is not None:
            visual_reports[name] = report.visual_hierarchy_feedback

        out_file = write_feedback_report(report, _OUTPUT_DIR)
        assert out_file.exists(), f"Expected {out_file} to be written"
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert data["fixture_name"] == name
        assert "visual_hierarchy_feedback" in data

        # Mirror to phase2 artifacts dir
        phase2_file = _PHASE2_DIR / out_file.name
        _PHASE2_DIR.mkdir(parents=True, exist_ok=True)
        phase2_file.write_text(out_file.read_text(encoding="utf-8"), encoding="utf-8")

    summary = write_summary(reports, _OUTPUT_DIR, visual_reports=visual_reports)
    assert summary.exists()
    content = summary.read_text(encoding="utf-8")
    for _, name in fixture_specs:
        assert name in content

    # Mirror summary to phase2 dir
    phase2_summary = _PHASE2_DIR / "layout_feedback_summary.md"
    phase2_summary.write_text(summary.read_text(encoding="utf-8"), encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 2.5 — Semantic Metadata Backfill integration tests
# ---------------------------------------------------------------------------

_PHASE25_DIR = Path(__file__).parent.parent.parent / "artifacts" / "layout" / "phase2_5"


def test_pipeline_report_carries_metadata_quality_feedback() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[0]
    report = _run_pipeline(level, fixture_name="crucible_l1")
    assert report.metadata_quality_feedback is not None


def test_crucible_l2_endpoint_is_maintenance_tunnel_via_explicit_metadata() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[1]
    report = _run_pipeline(level, fixture_name="crucible_l2")
    mqf = report.metadata_quality_feedback
    assert mqf is not None
    assert mqf.explicit_endpoint is True
    # The visual hierarchy endpoint should match the explicit endpoint_room_id (r06)
    vhf = report.visual_hierarchy_feedback
    assert vhf is not None
    endpoint_data = vhf.endpoint_feedback
    assert endpoint_data.endpoint_room_id == "r06"


def test_crucible_l3_endpoint_is_power_core_not_prime_golem() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[2]
    report = _run_pipeline(level, fixture_name="crucible_l3")
    vhf = report.visual_hierarchy_feedback
    assert vhf is not None
    endpoint_data = vhf.endpoint_feedback
    assert endpoint_data.endpoint_room_id == "r8", (
        f"Expected r8 (Power Core Chamber) but got {endpoint_data.endpoint_room_id}"
    )
    assert endpoint_data.endpoint_room_id != "r7", "r7 (Prime Golem Lair) must not be endpoint"


def test_all_target_fixtures_have_explicit_entrance_and_endpoint() -> None:
    crucible = _load_dungeon("crucible")
    tomb = _load_dungeon("tomb")
    fixture_specs = [
        (crucible.levels[0], "crucible_l1"),
        (crucible.levels[1], "crucible_l2"),
        (crucible.levels[2], "crucible_l3"),
        (tomb.levels[0],     "tomb_l1"),
    ]
    for level, name in fixture_specs:
        report = _run_pipeline(level, fixture_name=name)
        mqf = report.metadata_quality_feedback
        assert mqf is not None, f"{name}: metadata_quality_feedback is None"
        assert mqf.explicit_entrance is True, f"{name}: explicit_entrance is False"
        assert mqf.explicit_endpoint is True, f"{name}: explicit_endpoint is False"
        assert mqf.explicit_critical_path is True, f"{name}: explicit_critical_path is False"


def test_all_target_fixtures_geometry_score_does_not_regress() -> None:
    crucible = _load_dungeon("crucible")
    tomb = _load_dungeon("tomb")
    fixture_specs = [
        (crucible.levels[0], "crucible_l1"),
        (crucible.levels[1], "crucible_l2"),
        (crucible.levels[2], "crucible_l3"),
        (tomb.levels[0],     "tomb_l1"),
    ]
    for level, name in fixture_specs:
        report = _run_pipeline(level, fixture_name=name)
        score = report.layout_metrics.layout_score
        assert score == 100.0, f"{name}: geometry score regressed to {score}"


def test_all_target_fixtures_visual_hierarchy_feedback_still_present() -> None:
    crucible = _load_dungeon("crucible")
    tomb = _load_dungeon("tomb")
    fixture_specs = [
        (crucible.levels[0], "crucible_l1"),
        (crucible.levels[1], "crucible_l2"),
        (crucible.levels[2], "crucible_l3"),
        (tomb.levels[0],     "tomb_l1"),
    ]
    for level, name in fixture_specs:
        report = _run_pipeline(level, fixture_name=name)
        assert report.visual_hierarchy_feedback is not None, (
            f"{name}: visual_hierarchy_feedback is None after metadata backfill"
        )


def test_metadata_quality_feedback_in_written_json_report() -> None:
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[0]
    report = _run_pipeline(level, fixture_name="crucible_l1")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        out = write_feedback_report(report, Path(tmp))
        data = json.loads(out.read_text(encoding="utf-8"))
    assert "metadata_quality_feedback" in data
    mqf = data["metadata_quality_feedback"]
    assert "metadata_score" in mqf
    assert "explicit_entrance" in mqf
    assert "explicit_endpoint" in mqf


def test_phase25_feedback_reports_written_to_artifacts() -> None:
    crucible = _load_dungeon("crucible")
    tomb = _load_dungeon("tomb")
    fixture_specs = [
        (crucible.levels[0], "crucible_l1"),
        (crucible.levels[1], "crucible_l2"),
        (crucible.levels[2], "crucible_l3"),
        (tomb.levels[0],     "tomb_l1"),
    ]
    reports: list[LayoutFeedbackReport] = []
    visual_reports: dict[str, VisualHierarchyFeedbackReport] = {}
    for level, name in fixture_specs:
        report = _run_pipeline(level, fixture_name=name)
        reports.append(report)
        if report.visual_hierarchy_feedback is not None:
            visual_reports[name] = report.visual_hierarchy_feedback
        out_file = write_feedback_report(report, _PHASE25_DIR)
        assert out_file.exists()
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert "metadata_quality_feedback" in data
    summary = write_summary(reports, _PHASE25_DIR, visual_reports=visual_reports)
    assert summary.exists()
