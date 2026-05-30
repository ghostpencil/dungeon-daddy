"""Tests for dungeon_layout.metadata_validator — semantic metadata validation."""

from dungeon_daddy.data.models import Connection, LayoutMetadata, Level, Room
from dungeon_daddy.map.dungeon_layout.metadata_validator import validate_metadata

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


def _level(
    rooms: list[Room],
    connections: list[Connection] | None = None,
    layout_metadata: LayoutMetadata | None = None,
    **kwargs: object,
) -> Level:
    defaults: dict[str, object] = {
        "id": 1,
        "name": "Test Level",
        "summary": "",
        "ecology": "",
        "loop": "",
        "width": 1000,
        "height": 800,
        "entries": [],
        "connections": connections or [],
        "layout_metadata": layout_metadata,
    }
    defaults.update(kwargs)
    return Level(rooms=rooms, **defaults)  # type: ignore[arg-type]


def _conn(
    from_id: str,
    to_id: str,
    kind: str = "normal",
    **kwargs: object,
) -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": kind, **kwargs})


def _categories(warnings: list) -> list[str]:
    return [w.category for w in warnings]


# ---------------------------------------------------------------------------
# Slice 1 — clean level produces no warnings
# ---------------------------------------------------------------------------

def test_no_warnings_for_level_without_metadata() -> None:
    level = _level(rooms=[_room()])
    assert validate_metadata(level) == []


def test_no_warnings_for_level_with_valid_metadata() -> None:
    r1 = _room(id="r1", layout_role="entrance")
    r2 = _room(id="r2", layout_role="exit")
    meta = LayoutMetadata(
        graph_template="linear",
        entrance_room_id="r1",
        endpoint_room_id="r2",
        critical_path=["r1", "r2"],
    )
    level = _level(rooms=[r1, r2], layout_metadata=meta)
    assert validate_metadata(level) == []


# ---------------------------------------------------------------------------
# Slice 2 — invalid layout_role on room
# ---------------------------------------------------------------------------

def test_invalid_layout_role_produces_warning() -> None:
    room = _room(id="r1", layout_role="dungeon_master")
    level = _level(rooms=[room])
    warnings = validate_metadata(level)
    assert "INVALID_LAYOUT_ROLE" in _categories(warnings)


def test_valid_layout_role_produces_no_warning() -> None:
    for role in ("entrance", "hub", "boss", "objective", "exit", "descent",
                 "elevator", "stairs", "key_room", "lock_room", "treasure",
                 "hazard", "secret", "corridor", "hall", "library", "forge",
                 "utility", "study", "transition", "side_room", "unknown"):
        room = _room(id="r1", layout_role=role)
        level = _level(rooms=[room])
        warnings = validate_metadata(level)
        assert "INVALID_LAYOUT_ROLE" not in _categories(warnings), f"role={role!r} flagged incorrectly"


# ---------------------------------------------------------------------------
# Slice 3 — invalid graph_template in layout_metadata
# ---------------------------------------------------------------------------

def test_invalid_graph_template_produces_warning() -> None:
    meta = LayoutMetadata(graph_template="death_spiral")
    level = _level(rooms=[_room()], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "INVALID_GRAPH_TEMPLATE" in _categories(warnings)


def test_valid_graph_template_produces_no_warning() -> None:
    for tmpl in ("linear", "freeform", "hub_spoke", "branch_and_merge",
                 "lock_key", "split_path", "boss_endcap", "loop"):
        meta = LayoutMetadata(graph_template=tmpl)
        level = _level(rooms=[_room()], layout_metadata=meta)
        warnings = validate_metadata(level)
        assert "INVALID_GRAPH_TEMPLATE" not in _categories(warnings), f"template={tmpl!r} flagged incorrectly"


# ---------------------------------------------------------------------------
# Slice 4 — invalid connection_style on connection
# ---------------------------------------------------------------------------

def test_invalid_connection_style_produces_warning() -> None:
    conn = _conn("r1", "r2", connection_style="rainbow_bridge")
    level = _level(rooms=[_room(id="r1"), _room(id="r2")], connections=[conn])
    warnings = validate_metadata(level)
    assert "INVALID_CONNECTION_STYLE" in _categories(warnings)


def test_valid_connection_style_produces_no_warning() -> None:
    for style in ("normal", "critical", "optional", "secret", "locked",
                  "vertical", "shortcut", "hazard"):
        conn = _conn("r1", "r2", connection_style=style)
        level = _level(rooms=[_room(id="r1"), _room(id="r2")], connections=[conn])
        warnings = validate_metadata(level)
        assert "INVALID_CONNECTION_STYLE" not in _categories(warnings), f"style={style!r} flagged incorrectly"


# ---------------------------------------------------------------------------
# Slice 5 — invalid layout_connection_role on connection
# ---------------------------------------------------------------------------

def test_invalid_layout_connection_role_produces_warning() -> None:
    conn = _conn("r1", "r2", layout_connection_role="warp_gate")
    level = _level(rooms=[_room(id="r1"), _room(id="r2")], connections=[conn])
    warnings = validate_metadata(level)
    assert "INVALID_CONNECTION_ROLE" in _categories(warnings)


def test_valid_layout_connection_role_produces_no_warning() -> None:
    for role in ("critical", "optional", "secret", "locked", "vertical", "shortcut", "normal"):
        conn = _conn("r1", "r2", layout_connection_role=role)
        level = _level(rooms=[_room(id="r1"), _room(id="r2")], connections=[conn])
        warnings = validate_metadata(level)
        assert "INVALID_CONNECTION_ROLE" not in _categories(warnings), f"role={role!r} flagged incorrectly"


# ---------------------------------------------------------------------------
# Slice 6 — entrance_room_id not found in rooms
# ---------------------------------------------------------------------------

def test_entrance_room_id_not_found_produces_warning() -> None:
    meta = LayoutMetadata(entrance_room_id="ghost")
    level = _level(rooms=[_room(id="r1")], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "ENTRANCE_ROOM_NOT_FOUND" in _categories(warnings)


def test_entrance_room_id_found_produces_no_warning() -> None:
    meta = LayoutMetadata(entrance_room_id="r1")
    level = _level(rooms=[_room(id="r1")], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "ENTRANCE_ROOM_NOT_FOUND" not in _categories(warnings)


# ---------------------------------------------------------------------------
# Slice 7 — endpoint_room_id not found in rooms
# ---------------------------------------------------------------------------

def test_endpoint_room_id_not_found_produces_warning() -> None:
    meta = LayoutMetadata(endpoint_room_id="ghost")
    level = _level(rooms=[_room(id="r1")], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "ENDPOINT_ROOM_NOT_FOUND" in _categories(warnings)


def test_endpoint_room_id_found_produces_no_warning() -> None:
    meta = LayoutMetadata(endpoint_room_id="r1")
    level = _level(rooms=[_room(id="r1")], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "ENDPOINT_ROOM_NOT_FOUND" not in _categories(warnings)


# ---------------------------------------------------------------------------
# Slice 8 — critical_path contains unknown room ID
# ---------------------------------------------------------------------------

def test_critical_path_missing_room_produces_warning() -> None:
    meta = LayoutMetadata(critical_path=["r1", "ghost"])
    level = _level(rooms=[_room(id="r1")], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "CRITICAL_PATH_ROOM_NOT_FOUND" in _categories(warnings)


def test_critical_path_all_rooms_present_produces_no_warning() -> None:
    r1, r2 = _room(id="r1"), _room(id="r2")
    meta = LayoutMetadata(critical_path=["r1", "r2"])
    level = _level(rooms=[r1, r2], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "CRITICAL_PATH_ROOM_NOT_FOUND" not in _categories(warnings)


# ---------------------------------------------------------------------------
# Slice 9 — duplicate room IDs in critical_path
# ---------------------------------------------------------------------------

def test_critical_path_duplicate_produces_warning() -> None:
    r1 = _room(id="r1")
    meta = LayoutMetadata(critical_path=["r1", "r1"])
    level = _level(rooms=[r1], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "CRITICAL_PATH_DUPLICATE" in _categories(warnings)


def test_critical_path_no_duplicates_produces_no_warning() -> None:
    r1, r2 = _room(id="r1"), _room(id="r2")
    meta = LayoutMetadata(critical_path=["r1", "r2"])
    level = _level(rooms=[r1, r2], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "CRITICAL_PATH_DUPLICATE" not in _categories(warnings)


# ---------------------------------------------------------------------------
# Slice 10 — critical path does not start with entrance
# ---------------------------------------------------------------------------

def test_critical_path_entrance_mismatch_produces_warning() -> None:
    r1, r2, r3 = _room(id="r1"), _room(id="r2"), _room(id="r3")
    meta = LayoutMetadata(
        entrance_room_id="r1",
        critical_path=["r2", "r3"],
    )
    level = _level(rooms=[r1, r2, r3], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "CRITICAL_PATH_ENTRANCE_MISMATCH" in _categories(warnings)


def test_critical_path_starts_with_entrance_produces_no_warning() -> None:
    r1, r2 = _room(id="r1"), _room(id="r2")
    meta = LayoutMetadata(entrance_room_id="r1", critical_path=["r1", "r2"])
    level = _level(rooms=[r1, r2], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "CRITICAL_PATH_ENTRANCE_MISMATCH" not in _categories(warnings)


# ---------------------------------------------------------------------------
# Slice 11 — critical path does not end with endpoint
# ---------------------------------------------------------------------------

def test_critical_path_endpoint_mismatch_produces_warning() -> None:
    r1, r2, r3 = _room(id="r1"), _room(id="r2"), _room(id="r3")
    meta = LayoutMetadata(
        endpoint_room_id="r3",
        critical_path=["r1", "r2"],
    )
    level = _level(rooms=[r1, r2, r3], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "CRITICAL_PATH_ENDPOINT_MISMATCH" in _categories(warnings)


def test_critical_path_ends_with_endpoint_produces_no_warning() -> None:
    r1, r2 = _room(id="r1"), _room(id="r2")
    meta = LayoutMetadata(endpoint_room_id="r2", critical_path=["r1", "r2"])
    level = _level(rooms=[r1, r2], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "CRITICAL_PATH_ENDPOINT_MISMATCH" not in _categories(warnings)


# ---------------------------------------------------------------------------
# Slice 12 — critical connection not represented in critical path
# ---------------------------------------------------------------------------

def test_critical_connection_not_in_path_produces_warning() -> None:
    r1, r2, r3 = _room(id="r1"), _room(id="r2"), _room(id="r3")
    conn = _conn("r2", "r3", layout_connection_role="critical")
    meta = LayoutMetadata(critical_path=["r1", "r2"])
    level = _level(rooms=[r1, r2, r3], connections=[conn], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "CRITICAL_CONNECTION_NOT_IN_PATH" in _categories(warnings)


def test_critical_connection_in_path_produces_no_warning() -> None:
    r1, r2 = _room(id="r1"), _room(id="r2")
    conn = _conn("r1", "r2", layout_connection_role="critical")
    meta = LayoutMetadata(critical_path=["r1", "r2"])
    level = _level(rooms=[r1, r2], connections=[conn], layout_metadata=meta)
    warnings = validate_metadata(level)
    assert "CRITICAL_CONNECTION_NOT_IN_PATH" not in _categories(warnings)
