"""Tests for dungeon_layout.semantics — room role classification and template selection."""
import pytest

from dungeon_daddy.data.models import Connection, Level, Room
from dungeon_daddy.map.dungeon_layout.semantics import (
    classify_all_roles,
    classify_room_role,
    classify_template,
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


def _level(rooms: list[Room], connections: list[Connection] | None = None, **kwargs: object) -> Level:
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
    }
    defaults.update(kwargs)
    return Level(rooms=rooms, **defaults)  # type: ignore[arg-type]


def _conn(from_id: str, to_id: str, kind: str = "normal") -> Connection:
    return Connection(**{"from": from_id, "to": to_id, "type": kind})


# ---------------------------------------------------------------------------
# Slice 1 — explicit layout_role wins
# ---------------------------------------------------------------------------

def test_explicit_layout_role_is_returned_as_is() -> None:
    room = _room(layout_role="boss")
    assert classify_room_role(room, degree=1) == "boss"


def test_explicit_layout_role_beats_name_keyword() -> None:
    # Name would infer "entrance" but explicit metadata wins
    room = _room(name="Grand Entrance Hall", layout_role="hub")
    assert classify_room_role(room, degree=1) == "hub"


# ---------------------------------------------------------------------------
# Slice 2 — entrance keyword inference
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "Grand Entrance",
    "Entry Corridor",
    "Arrival Chamber",
    "Upper Landing",
])
def test_entrance_inferred_from_name(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "entrance"


def test_entrance_inferred_from_tag() -> None:
    room = _room(name="North Wing", tags=["entry"])
    assert classify_room_role(room, degree=1) == "entrance"


# ---------------------------------------------------------------------------
# Slice 3 — boss keyword inference
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "Boss Chamber",
    "Prime Golem Lair",
    "Throne of Bone",
    "Core Reactor",
    "Final Reckoning",
])
def test_boss_inferred_from_name(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "boss"


def test_boss_inferred_from_tag() -> None:
    room = _room(name="Deep Sanctum", tags=["boss"])
    assert classify_room_role(room, degree=1) == "boss"


# ---------------------------------------------------------------------------
# Slice 4 — hub inferred from high graph degree
# ---------------------------------------------------------------------------

def test_hub_inferred_from_high_degree() -> None:
    room = _room(name="Central Hall")
    assert classify_room_role(room, degree=3) == "hub"


def test_degree_2_is_not_hub() -> None:
    room = _room(name="Connecting Passage")
    assert classify_room_role(room, degree=2) == "unknown"


# ---------------------------------------------------------------------------
# Slice 5 — key_room keyword inference
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "Key Storage",
    "Control Room",
    "Lever Chamber",
    "Mechanism Vault",
])
def test_key_room_inferred_from_name(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "key_room"


# ---------------------------------------------------------------------------
# Slice 6 — lock_room keyword inference
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "Locked Antechamber",
    "Sealed Gate",
])
def test_lock_room_inferred_from_name(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "lock_room"


# ---------------------------------------------------------------------------
# Slice 6b — descent role (Phase 2)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "Descent to the Depths",
    "Elevator Shaft",
    "Sealed Descent",
])
def test_descent_inferred_from_name(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "descent"


def test_elevator_inferred_from_name() -> None:
    room = _room(name="Elevator Chamber")
    assert classify_room_role(room, degree=1) == "elevator"


@pytest.mark.parametrize("name", [
    "Stair Landing",
    "Spiral Staircase",
    "Stairs to Upper Level",
])
def test_stairs_inferred_from_name(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "stairs"


@pytest.mark.parametrize("name", [
    "Primary Objective Chamber",
    "Inner Sanctum",
])
def test_objective_inferred_from_name(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "objective"


@pytest.mark.parametrize("name", [
    "Receiving Hall",
    "Approach Corridor",
])
def test_entrance_expanded_keywords(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "entrance"


@pytest.mark.parametrize("name", [
    "Central Nexus",
    "Junction Room",
    "The Crossroads",
])
def test_hub_inferred_from_name_keywords(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "hub"


@pytest.mark.parametrize("name", [
    "The Treasury",
    "Reliquary of Bones",
    "Vault of Secrets",
])
def test_treasure_inferred_from_name(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "treasure"


@pytest.mark.parametrize("name", [
    "Trap Chamber",
    "Hazard Zone",
    "Electrified Pit",
])
def test_hazard_inferred_from_name(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "hazard"


@pytest.mark.parametrize("name", [
    "Grand Processional",
    "The Great Hallway",
])
def test_hall_inferred_from_name(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "hall"


@pytest.mark.parametrize("name", [
    "The Great Library",
    "Scriptorium",
    "Archive Chamber",
])
def test_library_inferred_from_name(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "library"


@pytest.mark.parametrize("name", [
    "Forge Room",
    "The Foundry",
    "Molten Works",
])
def test_forge_inferred_from_name(name: str) -> None:
    room = _room(name=name)
    assert classify_room_role(room, degree=1) == "forge"


# ---------------------------------------------------------------------------
# Slice 7 — unknown fallback
# ---------------------------------------------------------------------------

def test_unknown_when_no_keyword_matches() -> None:
    room = _room(name="Storage Alcove")
    assert classify_room_role(room, degree=1) == "unknown"


def test_unknown_for_generic_room_low_degree() -> None:
    room = _room(name="Room 7")
    assert classify_room_role(room, degree=0) == "unknown"


# ---------------------------------------------------------------------------
# Slice 8 — classify_all_roles covers every room and uses connection degrees
# ---------------------------------------------------------------------------

def test_classify_all_roles_returns_entry_for_every_room() -> None:
    rooms = [
        _room(id="r1", name="Entry Hall"),
        _room(id="r2", name="Guard Post"),
        _room(id="r3", name="Boss Lair"),
    ]
    level = _level(rooms)
    roles = classify_all_roles(level)
    assert set(roles.keys()) == {"r1", "r2", "r3"}


def test_classify_all_roles_uses_connection_degree_for_hub() -> None:
    rooms = [
        _room(id="r1", name="North Wing"),
        _room(id="r2", name="Central Hall"),   # will get degree 3
        _room(id="r3", name="South Wing"),
        _room(id="r4", name="East Wing"),
    ]
    connections = [
        _conn("r1", "r2"),
        _conn("r2", "r3"),
        _conn("r2", "r4"),
    ]
    level = _level(rooms, connections)
    roles = classify_all_roles(level)
    assert roles["r2"] == "hub"
    assert roles["r1"] == "unknown"


# ---------------------------------------------------------------------------
# Slice 9 — classify_template uses explicit floor_tags first
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tag,expected", [
    ("hub_spoke", "hub_spoke"),
    ("linear", "linear"),
    ("branch_merge", "branch_merge"),
    ("lock_key", "lock_key"),
    ("boss_endcap", "boss_endcap"),
    ("loop", "loop"),
    ("freeform", "freeform"),
])
def test_explicit_floor_tag_wins(tag: str, expected: str) -> None:
    rooms = [_room(id="r1"), _room(id="r2")]
    level = _level(rooms, floor_tags=[tag])
    roles = classify_all_roles(level)
    assert classify_template(level, roles) == expected


def test_first_valid_floor_tag_wins() -> None:
    rooms = [_room(id="r1"), _room(id="r2")]
    level = _level(rooms, floor_tags=["pursuit", "linear"])
    roles = classify_all_roles(level)
    # "pursuit" is not a valid template so first valid one wins
    assert classify_template(level, roles) == "linear"


# ---------------------------------------------------------------------------
# Slice 10 — infer hub_spoke when one room dominates by degree
# ---------------------------------------------------------------------------

def test_infers_hub_spoke_from_degree_distribution() -> None:
    # r2 has degree 4 (avg would be ~1.3), clearly dominant
    rooms = [_room(id=f"r{i}") for i in range(1, 6)]
    connections = [
        _conn("r1", "r2"),
        _conn("r2", "r3"),
        _conn("r2", "r4"),
        _conn("r2", "r5"),
    ]
    level = _level(rooms, connections)
    roles = classify_all_roles(level)
    assert classify_template(level, roles) == "hub_spoke"


# ---------------------------------------------------------------------------
# Slice 11 — infer linear from low-degree chain
# ---------------------------------------------------------------------------

def test_infers_linear_from_chain() -> None:
    # r1—r2—r3—r4: endpoints degree 1, middle rooms degree 2
    rooms = [_room(id=f"r{i}") for i in range(1, 5)]
    connections = [
        _conn("r1", "r2"),
        _conn("r2", "r3"),
        _conn("r3", "r4"),
    ]
    level = _level(rooms, connections)
    roles = classify_all_roles(level)
    assert classify_template(level, roles) == "linear"


# ---------------------------------------------------------------------------
# Slice 12 — freeform fallback
# ---------------------------------------------------------------------------

def test_freeform_fallback_for_irregular_graph() -> None:
    # Mixed degrees, no strong hub, not a chain
    rooms = [_room(id=f"r{i}") for i in range(1, 6)]
    connections = [
        _conn("r1", "r2"),
        _conn("r1", "r3"),
        _conn("r2", "r4"),
        _conn("r3", "r4"),
        _conn("r4", "r5"),
    ]
    level = _level(rooms, connections)
    roles = classify_all_roles(level)
    assert classify_template(level, roles) == "freeform"


def test_freeform_fallback_for_empty_level() -> None:
    level = _level([])
    roles = classify_all_roles(level)
    assert classify_template(level, roles) == "freeform"
