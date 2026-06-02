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
from dungeon_daddy.map.dungeon_layout import run_layout_pipeline
from dungeon_daddy.map.dungeon_layout.atmosphere import build_atmosphere_spec
from dungeon_daddy.map.dungeon_layout.camera_fit import compute_layout_bounds
from dungeon_daddy.map.dungeon_layout.connection_markers import resolve_connection_marker
from dungeon_daddy.map.dungeon_layout.connection_style import GraphConnectionStyleResolver
from dungeon_daddy.map.dungeon_layout.critical_path_style import CriticalPathPresenter
from dungeon_daddy.map.dungeon_layout.detail_panel_renderer import format_detail_panel
from dungeon_daddy.map.dungeon_layout.endpoint_emphasis import EndpointEmphasisDetector
from dungeon_daddy.map.dungeon_layout.graph_presentation_config import GraphPresentationConfig
from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState
from dungeon_daddy.map.dungeon_layout.labels import place_labels
from dungeon_daddy.map.dungeon_layout.metadata_quality_feedback import (
    generate_metadata_quality_feedback,
)
from dungeon_daddy.map.dungeon_layout.ports import generate_ports
from dungeon_daddy.map.dungeon_layout.room_detail_panel import build_room_detail
from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyleResolver
from dungeon_daddy.map.dungeon_layout.route_orthogonal import route_connections
from dungeon_daddy.map.dungeon_layout.seed_layout import (
    compute_critical_path,
    compute_seed_layout,
)
from dungeon_daddy.map.dungeon_layout.semantics import classify_all_roles, classify_template
from dungeon_daddy.map.dungeon_layout.style_resolver import resolve_room_render_style
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


# ---------------------------------------------------------------------------
# Phase 3 — Interaction Polish integration tests
# ---------------------------------------------------------------------------

_SEMANTIC_BASELINES = {
    "crucible_l1": 78.0,
    "crucible_l2": 82.2,
    "crucible_l3": 82.8,
    "tomb_l1": 81.0,
}
_METADATA_BASELINE = 85.0

_FIXTURE_SPECS = [
    ("crucible", 0, "crucible_l1"),
    ("crucible", 1, "crucible_l2"),
    ("crucible", 2, "crucible_l3"),
    ("tomb", 0, "tomb_l1"),
]


def test_phase3_semantic_scores_do_not_regress() -> None:
    """Semantic scores for all target fixtures stay at or above Phase 2.5 baselines."""
    for dungeon_name, level_idx, fixture_name in _FIXTURE_SPECS:
        dungeon = _load_dungeon(dungeon_name)
        level = dungeon.levels[level_idx]
        report = _run_pipeline(level, fixture_name=fixture_name)
        vhf = report.visual_hierarchy_feedback
        assert vhf is not None, f"{fixture_name}: visual_hierarchy_feedback is None"
        score = vhf.semantic_score
        baseline = _SEMANTIC_BASELINES[fixture_name]
        assert score >= baseline, (
            f"{fixture_name}: semantic score {score:.1f} regressed below {baseline}"
        )


def test_phase3_metadata_scores_do_not_regress() -> None:
    """Metadata scores for all target fixtures stay at or above 85.0."""
    for dungeon_name, level_idx, fixture_name in _FIXTURE_SPECS:
        dungeon = _load_dungeon(dungeon_name)
        level = dungeon.levels[level_idx]
        report = _run_pipeline(level, fixture_name=fixture_name)
        mqf = report.metadata_quality_feedback
        assert mqf is not None, f"{fixture_name}: metadata_quality_feedback is None"
        score = mqf.metadata_score
        assert score >= _METADATA_BASELINE, (
            f"{fixture_name}: metadata score {score:.1f} regressed below {_METADATA_BASELINE}"
        )


def test_phase3_interactive_states_render_without_exception() -> None:
    """resolve_room_render_style raises no exceptions for any room when a selection is active."""
    resolver = GraphRoomStyleResolver()
    for dungeon_name, level_idx, fixture_name in _FIXTURE_SPECS:
        dungeon = _load_dungeon(dungeon_name)
        level = dungeon.levels[level_idx]
        result = run_layout_pipeline(level)

        entrance_id = (
            level.layout_metadata.entrance_room_id
            if level.layout_metadata is not None
            else None
        ) or next(iter(result.rooms), None)

        view_state = GraphViewState()
        view_state.select_room(entrance_id)
        view_state.hover_room(None)

        critical_ids = set(result.critical_path)
        connected_ids = {
            c.to_room if c.from_room == entrance_id else c.from_room
            for c in level.connections
            if c.from_room == entrance_id or c.to_room == entrance_id
        }

        for room_id in result.rooms:
            base_style = resolver.resolve(result.room_roles.get(room_id, "unknown"))  # type: ignore[arg-type]
            resolved = resolve_room_render_style(
                room_id=room_id,
                base_style=base_style,
                view_state=view_state,
                critical_path_room_ids=critical_ids,
                connected_room_ids=connected_ids,
            )
            assert resolved is not None, f"{fixture_name}/{room_id}: resolved style is None"


def test_phase3_detail_panel_produces_data_for_entrance_room() -> None:
    """build_room_detail returns populated panel data for the entrance room of each fixture."""
    for dungeon_name, level_idx, fixture_name in _FIXTURE_SPECS:
        dungeon = _load_dungeon(dungeon_name)
        level = dungeon.levels[level_idx]
        result = run_layout_pipeline(level)

        entrance_id = (
            level.layout_metadata.entrance_room_id
            if level.layout_metadata is not None
            else None
        )
        if entrance_id is None:
            entrance_id = next(
                (rid for rid, role in result.room_roles.items() if str(role) == "entrance"),
                next(iter(result.rooms), None),
            )

        assert entrance_id is not None, f"{fixture_name}: could not determine entrance room"

        panel = build_room_detail(entrance_id, level, result)
        assert panel is not None, f"{fixture_name}: build_room_detail returned None for {entrance_id}"
        assert panel.room_name, f"{fixture_name}: panel.room_name is empty"
        assert panel.role is not None, f"{fixture_name}: panel.role is None"
        assert isinstance(panel.connections, list), f"{fixture_name}: panel.connections is not a list"


# ---------------------------------------------------------------------------
# Phase 4 — Presentation, Detail Panel, Dungeon Personality (integration)
# ---------------------------------------------------------------------------

# --- Detail panel empty state ---

def test_phase4_detail_panel_empty_state_returns_graph_mode_header() -> None:
    """format_detail_panel(None) returns GRAPH MODE header as the first line."""
    lines = format_detail_panel(None)
    assert lines[0].text == "GRAPH MODE"
    assert lines[0].kind == "header"


# --- Detail panel renders entrance room for all fixtures ---

def test_phase4_detail_panel_renders_entrance_room_for_all_fixtures() -> None:
    """format_detail_panel returns ROOM header and room name for each fixture's entrance."""
    for dungeon_name, level_idx, fixture_name in _FIXTURE_SPECS:
        dungeon = _load_dungeon(dungeon_name)
        level = dungeon.levels[level_idx]
        result = run_layout_pipeline(level)
        entrance_id = (
            level.layout_metadata.entrance_room_id
            if level.layout_metadata is not None
            else next(iter(result.rooms))
        )
        panel_data = build_room_detail(entrance_id, level, result)
        assert panel_data is not None, f"{fixture_name}: build_room_detail returned None"
        lines = format_detail_panel(panel_data)
        texts = [ln.text for ln in lines]
        assert "ROOM" in texts, f"{fixture_name}: missing ROOM header in panel"
        assert any(panel_data.room_name in t for t in texts), (
            f"{fixture_name}: room name {panel_data.room_name!r} missing from panel lines"
        )


# --- GraphPresentationConfig: defaults all enabled ---

def test_phase4_presentation_config_defaults_all_enabled() -> None:
    """GraphPresentationConfig default instance has all presentation flags enabled."""
    config = GraphPresentationConfig()
    assert config.show_detail_panel is True
    assert config.show_role_markers is True
    assert config.show_connection_markers is True
    assert config.enable_atmosphere is True
    assert config.enable_hover_glow is True
    assert config.enable_selection_glow is True
    assert config.fade_unrelated_on_selection is True
    assert config.detail_panel_position == "right"


# --- Hover state is stronger than base ---

def test_phase4_hover_style_is_stronger_than_base() -> None:
    """Hovered room receives wider border and non-zero glow_alpha versus base style."""
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[0]
    result = run_layout_pipeline(level)
    resolver = GraphRoomStyleResolver()
    entrance_id = level.layout_metadata.entrance_room_id  # type: ignore[union-attr]
    base_style = resolver.resolve(result.room_roles.get(entrance_id, "unknown"))  # type: ignore[arg-type]

    view_state = GraphViewState()
    view_state.hover_room(entrance_id)

    hover_style = resolve_room_render_style(
        room_id=entrance_id,
        base_style=base_style,
        view_state=view_state,
        critical_path_room_ids=set(result.critical_path),
        connected_room_ids=set(),
    )
    assert hover_style.border_width > base_style.border_width
    assert hover_style.glow_alpha > 0


# --- Selected state dominates hover ---

def test_phase4_selected_style_dominates_hover() -> None:
    """Selected room gets border_width+2, glow_alpha=140, and has_second_outline."""
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[0]
    result = run_layout_pipeline(level)
    resolver = GraphRoomStyleResolver()
    entrance_id = level.layout_metadata.entrance_room_id  # type: ignore[union-attr]
    base_style = resolver.resolve(result.room_roles.get(entrance_id, "unknown"))  # type: ignore[arg-type]

    view_state = GraphViewState()
    view_state.select_room(entrance_id)

    selected_style = resolve_room_render_style(
        room_id=entrance_id,
        base_style=base_style,
        view_state=view_state,
        critical_path_room_ids=set(result.critical_path),
        connected_room_ids=set(),
    )
    assert selected_style.border_width == base_style.border_width + 2.0
    assert selected_style.glow_alpha == 140
    assert selected_style.has_second_outline is True


# --- Unrelated rooms fade on selection ---

def test_phase4_unrelated_rooms_fade_on_selection() -> None:
    """Rooms unconnected to the selected room and not on critical path receive lower border_alpha."""
    dungeon = _load_dungeon("crucible")
    level = dungeon.levels[0]
    result = run_layout_pipeline(level)
    resolver = GraphRoomStyleResolver()
    entrance_id = level.layout_metadata.entrance_room_id  # type: ignore[union-attr]

    connected_ids = {
        c.to_room if c.from_room == entrance_id else c.from_room
        for c in level.connections
        if c.from_room == entrance_id or c.to_room == entrance_id
    }
    critical_ids = set(result.critical_path)

    unrelated_id = next(
        rid for rid in result.rooms
        if rid != entrance_id and rid not in connected_ids and rid not in critical_ids
    )
    base_style = resolver.resolve(result.room_roles.get(unrelated_id, "unknown"))  # type: ignore[arg-type]

    view_state = GraphViewState()
    view_state.select_room(entrance_id)

    faded_style = resolve_room_render_style(
        room_id=unrelated_id,
        base_style=base_style,
        view_state=view_state,
        critical_path_room_ids=critical_ids,
        connected_room_ids=connected_ids,
    )
    assert faded_style.border_alpha < base_style.border_alpha


# --- Connection markers for special roles ---

def test_phase4_locked_connection_has_lock_glyph() -> None:
    """layout_connection_role='locked' produces midpoint_glyph='LOCK'."""
    style = GraphConnectionStyleResolver().resolve("door", layout_connection_role="locked")
    marker = resolve_connection_marker(style)
    assert marker.midpoint_glyph == "LOCK"
    assert marker.is_dashed is False


def test_phase4_secret_connection_is_dashed() -> None:
    """layout_connection_role='secret' produces a dashed marker with no midpoint glyph."""
    style = GraphConnectionStyleResolver().resolve("door", layout_connection_role="secret")
    marker = resolve_connection_marker(style)
    assert marker.is_dashed is True
    assert marker.dash_length == 8.0


def test_phase4_shortcut_connection_is_dashed() -> None:
    """layout_connection_role='shortcut' produces a dashed marker (distinct from normal)."""
    style = GraphConnectionStyleResolver().resolve("door", layout_connection_role="shortcut")
    marker = resolve_connection_marker(style)
    assert marker.is_dashed is True


def test_phase4_vertical_connection_has_transition_glyph() -> None:
    """layout_connection_role='vertical' produces midpoint_glyph=up-down arrow."""
    style = GraphConnectionStyleResolver().resolve("stair", layout_connection_role="vertical")
    marker = resolve_connection_marker(style)
    assert marker.midpoint_glyph == "↕"  # ↕


# --- Connection markers appear in actual fixture connections ---

def test_phase4_fixture_special_connections_resolve_correct_markers() -> None:
    """Known special connections in fixtures produce correct markers end-to-end."""
    cases = [
        ("crucible", 0, "R2", "R4", "locked", "LOCK", False),
        ("crucible", 2, "r4", "r5", "secret", None, True),
        ("tomb", 0, "1-C", "1-E", "shortcut", None, True),
        ("tomb", 0, "1-E", "2-A", "vertical", "↕", False),
    ]
    conn_resolver = GraphConnectionStyleResolver()
    for dungeon_name, level_idx, from_id, to_id, expected_role, expected_glyph, expected_dashed in cases:
        dungeon = _load_dungeon(dungeon_name)
        level = dungeon.levels[level_idx]
        conn = next(
            (c for c in level.connections if c.from_room == from_id and c.to_room == to_id),
            None,
        )
        assert conn is not None, f"{dungeon_name}_l{level_idx+1}: connection {from_id}->{to_id} not found"
        assert conn.layout_connection_role == expected_role, (
            f"{from_id}->{to_id}: expected role {expected_role!r}, got {conn.layout_connection_role!r}"
        )
        style = conn_resolver.resolve(
            conn.type,
            connection_style=conn.connection_style,
            layout_connection_role=conn.layout_connection_role,
        )
        marker = resolve_connection_marker(style)
        assert marker.midpoint_glyph == expected_glyph, (
            f"{from_id}->{to_id}: expected glyph {expected_glyph!r}, got {marker.midpoint_glyph!r}"
        )
        assert marker.is_dashed == expected_dashed, (
            f"{from_id}->{to_id}: expected is_dashed={expected_dashed}, got {marker.is_dashed}"
        )


# --- Grid Mode untouched ---

def test_phase4_grid_renderer_is_untouched_and_constructable() -> None:
    """GridRenderer can still be imported and instantiated after Phase 4 changes."""
    from dungeon_daddy.map.grid_renderer import GridRenderer
    renderer = GridRenderer()
    assert renderer is not None
    assert callable(getattr(renderer, "draw", None))
    assert callable(getattr(renderer, "hit_test_connection", None))


# --- Atmosphere spec ---

def test_phase4_atmosphere_spec_is_enabled_by_default() -> None:
    """build_atmosphere_spec() returns an enabled spec with frame and corner ticks.

    Vignette bands are intentionally disabled (alpha=0, bands=0): the stacking
    algorithm darkens the center more than edges on a near-black background,
    producing visible concentric-rectangle artefacts.
    """
    spec = build_atmosphere_spec()
    assert spec.enabled is True
    assert spec.vignette_alpha == 0
    assert spec.vignette_bands == 0
    assert spec.show_corner_ticks is True


def test_phase4_atmosphere_spec_disabled_by_config() -> None:
    """build_atmosphere_spec with enable_atmosphere=False returns a fully disabled spec."""
    config = GraphPresentationConfig(enable_atmosphere=False)
    spec = build_atmosphere_spec(config)
    assert spec.enabled is False
    assert spec.vignette_alpha == 0


# --- Phase 4 score regressions ---

def test_phase4_geometry_score_does_not_regress() -> None:
    """Phase 4 presentation work must not degrade geometry scores below 100.0."""
    for dungeon_name, level_idx, fixture_name in _FIXTURE_SPECS:
        dungeon = _load_dungeon(dungeon_name)
        level = dungeon.levels[level_idx]
        report = _run_pipeline(level, fixture_name=fixture_name)
        score = report.layout_metrics.layout_score
        assert score == 100.0, f"{fixture_name}: geometry score regressed to {score} after Phase 4"


def test_phase4_semantic_scores_do_not_regress() -> None:
    """Phase 4 presentation work must not degrade semantic visual hierarchy scores."""
    for dungeon_name, level_idx, fixture_name in _FIXTURE_SPECS:
        dungeon = _load_dungeon(dungeon_name)
        level = dungeon.levels[level_idx]
        report = _run_pipeline(level, fixture_name=fixture_name)
        vhf = report.visual_hierarchy_feedback
        assert vhf is not None, f"{fixture_name}: visual_hierarchy_feedback missing"
        baseline = _SEMANTIC_BASELINES[fixture_name]
        assert vhf.semantic_score >= baseline, (
            f"{fixture_name}: semantic score {vhf.semantic_score:.1f} regressed below {baseline}"
        )


def test_phase4_metadata_scores_do_not_regress() -> None:
    """Phase 4 work must not degrade metadata quality scores below the Phase 3 baseline."""
    for dungeon_name, level_idx, fixture_name in _FIXTURE_SPECS:
        dungeon = _load_dungeon(dungeon_name)
        level = dungeon.levels[level_idx]
        report = _run_pipeline(level, fixture_name=fixture_name)
        mqf = report.metadata_quality_feedback
        assert mqf is not None, f"{fixture_name}: metadata_quality_feedback missing"
        assert mqf.metadata_score >= _METADATA_BASELINE, (
            f"{fixture_name}: metadata score {mqf.metadata_score:.1f} regressed below {_METADATA_BASELINE}"
        )


def test_phase4_interactive_states_render_without_exception() -> None:
    """Phase 4 modules must not break style resolution for any room under selection state."""
    resolver = GraphRoomStyleResolver()
    for dungeon_name, level_idx, fixture_name in _FIXTURE_SPECS:
        dungeon = _load_dungeon(dungeon_name)
        level = dungeon.levels[level_idx]
        result = run_layout_pipeline(level)
        entrance_id = (
            level.layout_metadata.entrance_room_id
            if level.layout_metadata is not None
            else next(iter(result.rooms))
        )
        view_state = GraphViewState()
        view_state.select_room(entrance_id)
        critical_ids = set(result.critical_path)
        connected_ids = {
            c.to_room if c.from_room == entrance_id else c.from_room
            for c in level.connections
            if c.from_room == entrance_id or c.to_room == entrance_id
        }
        for room_id in result.rooms:
            base_style = resolver.resolve(result.room_roles.get(room_id, "unknown"))  # type: ignore[arg-type]
            resolved = resolve_room_render_style(
                room_id=room_id,
                base_style=base_style,
                view_state=view_state,
                critical_path_room_ids=critical_ids,
                connected_room_ids=connected_ids,
            )
            assert resolved is not None, f"{fixture_name}/{room_id}: resolved style is None"
