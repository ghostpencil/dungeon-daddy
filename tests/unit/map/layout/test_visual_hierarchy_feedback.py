"""Tests for dungeon_layout.visual_hierarchy_feedback — VisualHierarchyFeedbackReport."""
from dungeon_daddy.map.dungeon_layout.endpoint_emphasis import EndpointEmphasisResult
from dungeon_daddy.map.dungeon_layout.critical_path_style import CriticalPathPresentationResult
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_config import VisualHierarchyConfig
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_feedback import (
    generate_visual_hierarchy_feedback,
    VisualHierarchyFeedbackReport,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_ROOMS = {"R1": "entrance", "R2": "hub", "R3": "boss"}
_NAMES = {"R1": "Front Hall", "R2": "Central Chamber", "R3": "Throne Room"}
_CONNECTIONS = [("R1→R2", "arch"), ("R2→R3", "door")]


def _endpoint(emphasized: bool = True) -> EndpointEmphasisResult:
    return EndpointEmphasisResult(
        endpoint_room_id="R3",
        endpoint_role="boss",
        is_emphasized=emphasized,
        has_sufficient_spacing=True,
        warnings=[],
    )


def _critical_path(distinguished: bool = True) -> CriticalPathPresentationResult:
    return CriticalPathPresentationResult(
        critical_path_room_ids={"R1", "R2", "R3"},
        critical_path_connection_ids={"R1→R2", "R2→R3"},
        is_visually_distinguished=distinguished,
    )


def _config(**overrides: object) -> VisualHierarchyConfig:
    return VisualHierarchyConfig(**overrides)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cycle 1 — function returns a VisualHierarchyFeedbackReport with all fields
# ---------------------------------------------------------------------------

def test_returns_report_with_all_expected_fields():
    report = generate_visual_hierarchy_feedback(
        rooms=_ROOMS,
        room_names=_NAMES,
        connections=_CONNECTIONS,
        endpoint_result=_endpoint(),
        critical_path_result=_critical_path(),
        config=_config(),
    )
    assert isinstance(report, VisualHierarchyFeedbackReport)
    assert isinstance(report.roles_styled, bool)
    assert isinstance(report.connection_styles_applied, bool)
    assert isinstance(report.critical_path_emphasized, bool)
    assert isinstance(report.endpoint_emphasized, bool)
    assert isinstance(report.semantic_score, float)
    assert isinstance(report.room_style_feedback, list)
    assert isinstance(report.connection_style_feedback, list)
    assert report.endpoint_feedback is not None
    assert report.critical_path_feedback is not None
    assert isinstance(report.warnings, list)


# ---------------------------------------------------------------------------
# Cycle 2 — room_style_feedback has one entry per room with correct style_key
# ---------------------------------------------------------------------------

def test_room_style_feedback_has_one_entry_per_room_with_correct_style_key():
    report = generate_visual_hierarchy_feedback(
        rooms=_ROOMS,
        room_names=_NAMES,
        connections=_CONNECTIONS,
        endpoint_result=_endpoint(),
        critical_path_result=_critical_path(),
        config=_config(),
    )
    assert len(report.room_style_feedback) == 3
    by_id = {e.room_id: e for e in report.room_style_feedback}
    assert by_id["R1"].style_key == "entrance"
    assert by_id["R2"].style_key == "hub"
    assert by_id["R3"].style_key == "boss"
    assert by_id["R3"].expected_visual_priority == "high"
    assert by_id["R3"].room_name == "Throne Room"


# ---------------------------------------------------------------------------
# Cycle 3 — connection_style_feedback has one entry per connection
# ---------------------------------------------------------------------------

def test_connection_style_feedback_has_one_entry_per_connection():
    report = generate_visual_hierarchy_feedback(
        rooms=_ROOMS,
        room_names=_NAMES,
        connections=_CONNECTIONS,
        endpoint_result=_endpoint(),
        critical_path_result=_critical_path(),
        config=_config(),
    )
    assert len(report.connection_style_feedback) == 2
    by_id = {e.connection_id: e for e in report.connection_style_feedback}
    assert "R1→R2" in by_id
    assert "R2→R3" in by_id
    # "arch" resolves to its own key; "door" also has its own
    assert by_id["R1→R2"].label == "arch"
    assert by_id["R2→R3"].label == "door"


# ---------------------------------------------------------------------------
# Cycle 4 — semantic_score is 100.0 when all rooms have high roles, endpoint
#            emphasized, and critical path distinguished
# ---------------------------------------------------------------------------

def test_semantic_score_is_100_when_all_components_ideal():
    # boss + hub are high-priority, entrance is medium — use all-high-priority setup
    rooms = {"R1": "boss", "R2": "hub"}
    names = {"R1": "Sanctum", "R2": "Nexus"}
    ep = EndpointEmphasisResult(
        endpoint_room_id="R1",
        endpoint_role="boss",
        is_emphasized=True,
        has_sufficient_spacing=True,
        warnings=[],
    )
    cp = CriticalPathPresentationResult(
        critical_path_room_ids={"R1", "R2"},
        critical_path_connection_ids={"R1→R2"},
        is_visually_distinguished=True,
    )
    report = generate_visual_hierarchy_feedback(
        rooms=rooms,
        room_names=names,
        connections=[],
        endpoint_result=ep,
        critical_path_result=cp,
        config=_config(),
    )
    assert report.semantic_score == 100.0


# ---------------------------------------------------------------------------
# Cycle 5 — MISSING_SEMANTIC_ROLE warning emitted when a room has "unknown" role
# ---------------------------------------------------------------------------

def test_missing_semantic_role_warning_when_room_has_unknown_role():
    rooms = {"R1": "entrance", "R2": "unknown"}
    names = {"R1": "Hall", "R2": "Room 2"}
    report = generate_visual_hierarchy_feedback(
        rooms=rooms,
        room_names=names,
        connections=[],
        endpoint_result=_endpoint(),
        critical_path_result=_critical_path(),
        config=_config(),
    )
    assert "MISSING_SEMANTIC_ROLE" in report.warnings


# ---------------------------------------------------------------------------
# Cycle 6 — ENDPOINT_NOT_EMPHASIZED warning propagated from EndpointEmphasisResult
# ---------------------------------------------------------------------------

def test_endpoint_not_emphasized_warning_is_propagated():
    ep = EndpointEmphasisResult(
        endpoint_room_id="R3",
        endpoint_role="boss",
        is_emphasized=True,
        has_sufficient_spacing=False,
        warnings=["ENDPOINT_NOT_EMPHASIZED"],
    )
    report = generate_visual_hierarchy_feedback(
        rooms=_ROOMS,
        room_names=_NAMES,
        connections=_CONNECTIONS,
        endpoint_result=ep,
        critical_path_result=_critical_path(),
        config=_config(),
    )
    assert "ENDPOINT_NOT_EMPHASIZED" in report.warnings


# ---------------------------------------------------------------------------
# Cycle 7 — CRITICAL_PATH_NOT_DISTINGUISHED warning propagated from
#            CriticalPathPresentationResult
# ---------------------------------------------------------------------------

def test_critical_path_not_distinguished_warning_is_propagated():
    cp = CriticalPathPresentationResult(
        critical_path_room_ids=set(),
        critical_path_connection_ids=set(),
        is_visually_distinguished=False,
        warnings=["CRITICAL_PATH_NOT_DISTINGUISHED"],
    )
    report = generate_visual_hierarchy_feedback(
        rooms=_ROOMS,
        room_names=_NAMES,
        connections=_CONNECTIONS,
        endpoint_result=_endpoint(),
        critical_path_result=cp,
        config=_config(),
    )
    assert "CRITICAL_PATH_NOT_DISTINGUISHED" in report.warnings


# ---------------------------------------------------------------------------
# Cycle 8 — HUB_NOT_EMPHASIZED warning when hub exists and config disables
#            role styling
# ---------------------------------------------------------------------------

def test_hub_not_emphasized_warning_when_role_styling_disabled():
    report = generate_visual_hierarchy_feedback(
        rooms=_ROOMS,
        room_names=_NAMES,
        connections=_CONNECTIONS,
        endpoint_result=_endpoint(),
        critical_path_result=_critical_path(),
        config=_config(style_room_roles=False),
    )
    assert "HUB_NOT_EMPHASIZED" in report.warnings


# ---------------------------------------------------------------------------
# Cycle 9 — SECRET_CONNECTION_NOT_DISTINCT warning when secret connections
#            exist but config disables secret styling
# ---------------------------------------------------------------------------

def test_secret_connection_not_distinct_when_secret_styling_disabled():
    connections = [("R1→R2", "secret_shortcut"), ("R2→R3", "door")]
    report = generate_visual_hierarchy_feedback(
        rooms=_ROOMS,
        room_names=_NAMES,
        connections=connections,
        endpoint_result=_endpoint(),
        critical_path_result=_critical_path(),
        config=_config(style_secret_connections=False),
    )
    assert "SECRET_CONNECTION_NOT_DISTINCT" in report.warnings


# ---------------------------------------------------------------------------
# Cycle 10 — semantic_score is reduced when rooms have low-priority roles
# ---------------------------------------------------------------------------

def test_semantic_score_reduced_when_rooms_have_low_priority_roles():
    # All rooms "unknown" → all low priority → score < 100
    rooms = {"R1": "unknown", "R2": "unknown"}
    names = {"R1": "Room A", "R2": "Room B"}
    ep = EndpointEmphasisResult(
        endpoint_room_id=None,
        endpoint_role=None,
        is_emphasized=False,
        has_sufficient_spacing=True,
        warnings=["AMBIGUOUS_ENDPOINT_ROLE"],
    )
    cp = CriticalPathPresentationResult(
        critical_path_room_ids=set(),
        critical_path_connection_ids=set(),
        is_visually_distinguished=False,
        warnings=["CRITICAL_PATH_NOT_DISTINGUISHED"],
    )
    report = generate_visual_hierarchy_feedback(
        rooms=rooms,
        room_names=names,
        connections=[],
        endpoint_result=ep,
        critical_path_result=cp,
        config=_config(),
    )
    assert report.semantic_score < 100.0
