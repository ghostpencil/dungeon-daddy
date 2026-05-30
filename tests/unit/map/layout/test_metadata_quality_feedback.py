"""Tests for dungeon_layout.metadata_quality_feedback."""
from dungeon_daddy.data.models import Connection, LayoutMetadata, Level, Room
from dungeon_daddy.map.dungeon_layout.metadata_quality_feedback import (
    MetadataQualityFeedback,
    generate_metadata_quality_feedback,
    format_summary_row,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _room(**kwargs: object) -> Room:
    defaults: dict[str, object] = {
        "id": "r1",
        "num": 1,
        "name": "Test Room",
        "x": 0,
        "y": 0,
        "w": 100,
        "h": 80,
        "type": "normal",
        "note": "",
    }
    defaults.update(kwargs)
    return Room(**defaults)  # type: ignore[arg-type]


def _conn(
    from_id: str,
    to_id: str,
    kind: str = "normal",
    **kwargs: object,
) -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": kind, **kwargs})


def _level(
    rooms: list[Room],
    connections: list[Connection] | None = None,
    layout_metadata: LayoutMetadata | None = None,
) -> Level:
    return Level(
        id=1,
        name="Test Level",
        summary="",
        ecology="",
        loop="",
        width=1000,
        height=800,
        entries=[],
        rooms=rooms,
        connections=connections or [],
        layout_metadata=layout_metadata,
    )


# ---------------------------------------------------------------------------
# Slice 1 — MetadataQualityFeedback model has correct fields and defaults
# ---------------------------------------------------------------------------

def test_metadata_quality_feedback_model_defaults() -> None:
    fb = MetadataQualityFeedback(
        explicit_room_role_count=0,
        inferred_room_role_count=0,
        unknown_room_role_count=0,
        explicit_connection_style_count=0,
        inferred_connection_style_count=0,
        explicit_critical_path=False,
        explicit_endpoint=False,
        explicit_entrance=False,
        metadata_score=0.0,
    )
    assert fb.warnings == []
    assert fb.metadata_score == 0.0
    assert fb.explicit_critical_path is False


# ---------------------------------------------------------------------------
# Slice 2 — room role counts
# ---------------------------------------------------------------------------

def test_all_rooms_explicit_roles() -> None:
    rooms = [
        _room(id="r1", layout_role="entrance"),
        _room(id="r2", layout_role="boss"),
    ]
    fb = generate_metadata_quality_feedback(_level(rooms))
    assert fb.explicit_room_role_count == 2
    assert fb.inferred_room_role_count == 0
    assert fb.unknown_room_role_count == 0


def test_rooms_inferred_from_name() -> None:
    rooms = [
        _room(id="r1", name="Entry Hall"),   # inferred as entrance
        _room(id="r2", name="Trap Room"),    # inferred as hazard
    ]
    fb = generate_metadata_quality_feedback(_level(rooms))
    assert fb.explicit_room_role_count == 0
    assert fb.inferred_room_role_count == 2
    assert fb.unknown_room_role_count == 0


def test_room_with_no_inference_is_unknown() -> None:
    rooms = [_room(id="r1", name="Generic Room")]
    fb = generate_metadata_quality_feedback(_level(rooms))
    assert fb.unknown_room_role_count == 1
    assert fb.inferred_room_role_count == 0
    assert fb.explicit_room_role_count == 0


# ---------------------------------------------------------------------------
# Slice 3 — connection style counts
# ---------------------------------------------------------------------------

def test_explicit_connection_style_counted() -> None:
    rooms = [_room(id="r1"), _room(id="r2")]
    connections = [_conn("r1", "r2", connection_style="critical")]
    fb = generate_metadata_quality_feedback(_level(rooms, connections))
    assert fb.explicit_connection_style_count == 1
    assert fb.inferred_connection_style_count == 0


def test_explicit_connection_role_counted() -> None:
    rooms = [_room(id="r1"), _room(id="r2")]
    connections = [_conn("r1", "r2", layout_connection_role="locked")]
    fb = generate_metadata_quality_feedback(_level(rooms, connections))
    assert fb.explicit_connection_style_count == 1
    assert fb.inferred_connection_style_count == 0


def test_connection_with_no_explicit_style_is_inferred() -> None:
    rooms = [_room(id="r1"), _room(id="r2")]
    connections = [_conn("r1", "r2")]
    fb = generate_metadata_quality_feedback(_level(rooms, connections))
    assert fb.explicit_connection_style_count == 0
    assert fb.inferred_connection_style_count == 1


# ---------------------------------------------------------------------------
# Slice 4 — explicit flags (entrance / endpoint / critical path)
# ---------------------------------------------------------------------------

def test_no_layout_metadata_all_flags_false() -> None:
    fb = generate_metadata_quality_feedback(_level([_room()]))
    assert fb.explicit_entrance is False
    assert fb.explicit_endpoint is False
    assert fb.explicit_critical_path is False


def test_explicit_entrance_flag_set_when_entrance_room_id_present() -> None:
    meta = LayoutMetadata(entrance_room_id="r1")
    fb = generate_metadata_quality_feedback(_level([_room(id="r1")], layout_metadata=meta))
    assert fb.explicit_entrance is True


def test_explicit_endpoint_flag_set_when_endpoint_room_id_present() -> None:
    meta = LayoutMetadata(endpoint_room_id="r1")
    fb = generate_metadata_quality_feedback(_level([_room(id="r1")], layout_metadata=meta))
    assert fb.explicit_endpoint is True


def test_explicit_critical_path_flag_set_when_path_nonempty() -> None:
    meta = LayoutMetadata(critical_path=["r1", "r2"])
    rooms = [_room(id="r1"), _room(id="r2")]
    fb = generate_metadata_quality_feedback(_level(rooms, layout_metadata=meta))
    assert fb.explicit_critical_path is True


def test_empty_critical_path_flag_is_false() -> None:
    meta = LayoutMetadata(critical_path=[])
    fb = generate_metadata_quality_feedback(_level([_room()], layout_metadata=meta))
    assert fb.explicit_critical_path is False


# ---------------------------------------------------------------------------
# Slice 5 — metadata_score
# ---------------------------------------------------------------------------

def test_fully_explicit_level_scores_high() -> None:
    r1 = _room(id="r1", layout_role="entrance")
    r2 = _room(id="r2", layout_role="boss")
    conn = _conn("r1", "r2", connection_style="critical")
    meta = LayoutMetadata(
        entrance_room_id="r1",
        endpoint_room_id="r2",
        critical_path=["r1", "r2"],
    )
    fb = generate_metadata_quality_feedback(_level([r1, r2], [conn], meta))
    assert fb.metadata_score >= 80.0


def test_no_metadata_level_scores_low() -> None:
    rooms = [_room(id="r1", name="Generic Room")]
    fb = generate_metadata_quality_feedback(_level(rooms))
    assert fb.metadata_score < 50.0


def test_metadata_score_in_valid_range() -> None:
    fb = generate_metadata_quality_feedback(_level([_room()]))
    assert 0.0 <= fb.metadata_score <= 100.0


# ---------------------------------------------------------------------------
# Slice 6 — warnings forwarded from validate_metadata
# ---------------------------------------------------------------------------

def test_no_warnings_for_clean_level() -> None:
    r1 = _room(id="r1", layout_role="entrance")
    r2 = _room(id="r2", layout_role="boss")
    meta = LayoutMetadata(
        entrance_room_id="r1",
        endpoint_room_id="r2",
        critical_path=["r1", "r2"],
    )
    fb = generate_metadata_quality_feedback(_level([r1, r2], layout_metadata=meta))
    assert fb.warnings == []


def test_invalid_role_produces_warning_in_feedback() -> None:
    room = _room(id="r1", layout_role="not_a_role")
    fb = generate_metadata_quality_feedback(_level([room]))
    assert any("not_a_role" in w for w in fb.warnings)


def test_missing_entrance_id_produces_warning_in_feedback() -> None:
    meta = LayoutMetadata(entrance_room_id="ghost")
    fb = generate_metadata_quality_feedback(_level([_room(id="r1")], layout_metadata=meta))
    assert any("ghost" in w for w in fb.warnings)


# ---------------------------------------------------------------------------
# Slice 7 — format_summary_row
# ---------------------------------------------------------------------------

def _make_full_feedback(*, unknown: int = 0, score: float = 80.0) -> MetadataQualityFeedback:
    return MetadataQualityFeedback(
        explicit_room_role_count=2,
        inferred_room_role_count=0,
        unknown_room_role_count=unknown,
        explicit_connection_style_count=1,
        inferred_connection_style_count=0,
        explicit_critical_path=True,
        explicit_endpoint=True,
        explicit_entrance=True,
        metadata_score=score,
    )


def test_summary_row_contains_dungeon_and_level_name() -> None:
    row = format_summary_row("The Crucible", "Level 1", 100.0, 75.0, _make_full_feedback())
    assert "The Crucible" in row
    assert "Level 1" in row


def test_summary_row_pass_status_when_no_unknowns_and_good_score() -> None:
    row = format_summary_row("Dungeon", "L1", 100.0, 80.0, _make_full_feedback(unknown=0, score=60.0))
    assert "PASS" in row


def test_summary_row_warn_status_when_unknowns_present() -> None:
    row = format_summary_row("Dungeon", "L1", 100.0, 50.0, _make_full_feedback(unknown=2, score=80.0))
    assert "WARN" in row


def test_summary_row_warn_status_when_score_below_threshold() -> None:
    row = format_summary_row("Dungeon", "L1", 100.0, 30.0, _make_full_feedback(unknown=0, score=40.0))
    assert "WARN" in row


def test_summary_row_is_pipe_delimited() -> None:
    row = format_summary_row("Dungeon", "L1", 100.0, 70.0, _make_full_feedback())
    assert row.startswith("|")
    assert row.endswith("|")
    assert row.count("|") >= 10
