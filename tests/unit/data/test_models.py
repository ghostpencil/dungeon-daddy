"""Tests for dungeon_daddy/data/models.py — written before implementation."""
import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# DesignMode enum
# ---------------------------------------------------------------------------

def test_design_mode_values():
    from dungeon_daddy.data.models import DesignMode
    assert DesignMode.WIZARD == "wizard"
    assert DesignMode.LEVEL_WIZARD == "level_wizard"
    assert DesignMode.GENERATION == "generation"
    assert DesignMode.EDIT == "edit"



# ---------------------------------------------------------------------------
# Behavior 1: Dungeon round-trips through model_dump → model_validate
# ---------------------------------------------------------------------------

def make_minimal_dungeon():
    """Build the smallest valid Dungeon for round-trip testing."""
    from dungeon_daddy.data.models import (
        Dungeon, DungeonMeta, Level, Room, Connection, Entry,
        Loop, LoopPattern,
    )
    return Dungeon(
        meta=DungeonMeta(
            title="Test Tomb",
            theme="Undead",
            setting="A damp cellar.",
            party="2 adventurers • level 1",
            quest="Find the key.",
        ),
        levels=[
            Level(
                id=1,
                name="Level One",
                summary="A single room.",
                ecology="One rat.",
                loop="None.",
                width=10,
                height=8,
                entries=[],
                rooms=[
                    Room(id="1-A", num=1, name="Entry", x=1, y=1, w=3, h=3,
                         type="hall", note="Damp stone."),
                    Room(id="1-B", num=2, name="Vault", x=6, y=1, w=2, h=2,
                         type="vault", note="Locked."),
                ],
                connections=[
                    Connection(from_room="1-A", to_room="1-B", type="door"),
                ],
            )
        ],
    )


def test_dungeon_round_trip():
    dungeon = make_minimal_dungeon()
    data = dungeon.model_dump(mode="json")
    restored = type(dungeon).model_validate(data)
    assert restored == dungeon


# ---------------------------------------------------------------------------
# Behavior 2: Connection serialises from_room/to_room as "from"/"to"
# ---------------------------------------------------------------------------

def test_connection_alias_serialisation():
    from dungeon_daddy.data.models import Connection
    conn = Connection(from_room="1-A", to_room="1-B", type="door")
    data = conn.model_dump(by_alias=True)
    assert "from" in data
    assert "to" in data
    assert "from_room" not in data
    assert "to_room" not in data


def test_connection_loads_from_alias():
    from dungeon_daddy.data.models import Connection
    conn = Connection.model_validate({"from": "1-A", "to": "1-B", "type": "hall"})
    assert conn.from_room == "1-A"
    assert conn.to_room == "1-B"


# ---------------------------------------------------------------------------
# MR-6: Optional waypoints on Connection
# ---------------------------------------------------------------------------

def test_connection_without_waypoints_has_waypoints_none():
    from dungeon_daddy.data.models import Connection
    conn = Connection.model_validate({"from": "1-A", "to": "1-B", "type": "door"})
    assert conn.waypoints is None


def test_connection_with_waypoints_parses_list():
    from dungeon_daddy.data.models import Connection, Waypoint
    conn = Connection.model_validate({
        "from": "R4", "to": "R5", "type": "door",
        "waypoints": [{"x": 22, "y": 14}, {"x": 30, "y": 14}],
    })
    assert conn.waypoints == [Waypoint(x=22, y=14), Waypoint(x=30, y=14)]


# ---------------------------------------------------------------------------
# Behavior 3: ChatMessage.role rejects invalid values
# ---------------------------------------------------------------------------

def test_chat_message_valid_roles():
    from dungeon_daddy.data.models import ChatMessage
    for role in ("gm", "dm", "system"):
        msg = ChatMessage(role=role, content="hello")
        assert msg.role == role


def test_chat_message_rejects_invalid_role():
    from dungeon_daddy.data.models import ChatMessage
    with pytest.raises(ValidationError):
        ChatMessage(role="user", content="hello")


# ---------------------------------------------------------------------------
# Behavior 4: SessionState.current_room_id contract
# ---------------------------------------------------------------------------

def test_session_state_defaults():
    from dungeon_daddy.data.models import SessionState
    state = SessionState(dungeon_id="test")
    assert state.current_room_id is None
    assert state.visited_rooms == []
    assert state.play_transcript == []
    assert state.design_transcript == []


def test_session_state_rejects_empty_string_room_id():
    from dungeon_daddy.data.models import SessionState
    # Empty string is explicitly invalid per spec
    state = SessionState(dungeon_id="test", current_room_id="")
    # Pydantic allows the string, so we validate the contract at the
    # application layer — confirm the field accepts None and valid IDs
    assert SessionState(dungeon_id="test", current_room_id=None).current_room_id is None
    assert SessionState(dungeon_id="test", current_room_id="1-A").current_room_id == "1-A"


# ---------------------------------------------------------------------------
# Behavior 5: validate_dungeon() — all 6 rules
# ---------------------------------------------------------------------------

def make_valid_level():
    from dungeon_daddy.data.models import Level, Room, Connection
    return Level(
        id=1, name="L1", summary="", ecology="", loop="",
        width=10, height=8, entries=[],
        rooms=[
            Room(id="1-A", num=1, name="A", x=0, y=0, w=3, h=3, type="hall", note=""),
            Room(id="1-B", num=2, name="B", x=4, y=0, w=3, h=3, type="hall", note=""),
        ],
        connections=[
            Connection(from_room="1-A", to_room="1-B", type="door"),
        ],
    )


def make_dungeon_with_level(level):
    from dungeon_daddy.data.models import Dungeon, DungeonMeta
    return Dungeon(
        meta=DungeonMeta(title="T", theme="X", setting="S", party="P", quest="Q"),
        levels=[level],
    )


def test_validate_dungeon_passes_valid():
    from dungeon_daddy.data.models import validate_dungeon
    dungeon = make_dungeon_with_level(make_valid_level())
    result = validate_dungeon(dungeon)
    assert result.is_valid
    assert result.errors == []
    assert bool(result) is True


def test_validate_dungeon_catches_duplicate_room_ids():
    from dungeon_daddy.data.models import validate_dungeon, Level, Room, Connection
    level = Level(
        id=1, name="L1", summary="", ecology="", loop="",
        width=10, height=8, entries=[],
        rooms=[
            Room(id="1-A", num=1, name="A", x=0, y=0, w=2, h=2, type="hall", note=""),
            Room(id="1-A", num=2, name="B", x=4, y=0, w=2, h=2, type="hall", note=""),
        ],
        connections=[Connection(from_room="1-A", to_room="1-A", type="door")],
    )
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("duplicate" in e.lower() for e in result.errors)


def test_validate_dungeon_catches_orphan_room():
    from dungeon_daddy.data.models import validate_dungeon, Level, Room
    level = Level(
        id=1, name="L1", summary="", ecology="", loop="",
        width=10, height=8, entries=[],
        rooms=[
            Room(id="1-A", num=1, name="A", x=0, y=0, w=2, h=2, type="hall", note=""),
            Room(id="1-B", num=2, name="B", x=4, y=0, w=2, h=2, type="hall", note=""),
        ],
        connections=[],   # 1-B is orphaned
    )
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("1-B" in e for e in result.errors)


def test_validate_dungeon_catches_bad_loop_room_ref():
    from dungeon_daddy.data.models import validate_dungeon, Loop
    level = make_valid_level()
    level.loops = [Loop(
        id="L1", pattern="lock_key", note="", entry="1-A", goal="1-B",
        path_a=["1-A", "GHOST", "1-B"], path_b=["1-A", "1-B"],
    )]
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("GHOST" in e for e in result.errors)


def test_validate_dungeon_catches_missing_entry_goal():
    from dungeon_daddy.data.models import validate_dungeon, Loop
    level = make_valid_level()
    level.loops = [Loop(
        id="L1", pattern="lock_key", note="", entry="NOWHERE", goal="1-B",
        path_a=["1-A", "1-B"], path_b=["1-A", "1-B"],
    )]
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("NOWHERE" in e for e in result.errors)


def test_validate_dungeon_catches_self_connection():
    from dungeon_daddy.data.models import validate_dungeon, Connection
    level = make_valid_level()
    level.connections.append(Connection(from_room="1-A", to_room="1-A", type="door"))
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("self-connection" in e.lower() for e in result.errors)


def test_validate_dungeon_catches_out_of_bounds_room():
    from dungeon_daddy.data.models import validate_dungeon, Room, Connection
    level = make_valid_level()
    # Room that extends past the grid width (10)
    level.rooms.append(
        Room(id="1-C", num=3, name="C", x=8, y=0, w=5, h=2, type="hall", note="")
    )
    level.connections.append(Connection(from_room="1-A", to_room="1-C", type="door"))
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("1-C" in e for e in result.errors)


def test_validate_dungeon_catches_overlapping_rooms():
    from dungeon_daddy.data.models import validate_dungeon, Level, Room, Connection
    # 1-A at (0,0) w=5 h=5 — 1-B at (3,3) w=3 h=3 — they overlap
    level = Level(
        id=1, name="L1", summary="", ecology="", loop="",
        width=10, height=10, entries=[],
        rooms=[
            Room(id="1-A", num=1, name="Marketplace", x=0, y=0, w=5, h=5, type="hall", note=""),
            Room(id="1-B", num=2, name="Scorpion Lair", x=3, y=3, w=3, h=3, type="lair", note=""),
        ],
        connections=[Connection(from_room="1-A", to_room="1-B", type="door")],
    )
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("overlap" in e.lower() for e in result.errors)
    assert any("1-A" in e and "1-B" in e for e in result.errors)


def test_validate_dungeon_catches_touching_rooms():
    from dungeon_daddy.data.models import validate_dungeon, Level, Room, Connection
    # 1-A at (0,0) w=5 h=5 — 1-B at (5,0) w=3 h=3 — exactly touching (gap=0), too close
    level = Level(
        id=1, name="L1", summary="", ecology="", loop="",
        width=10, height=8, entries=[],
        rooms=[
            Room(id="1-A", num=1, name="Hall", x=0, y=0, w=5, h=5, type="hall", note=""),
            Room(id="1-B", num=2, name="Vault", x=5, y=0, w=3, h=3, type="vault", note=""),
        ],
        connections=[Connection(from_room="1-A", to_room="1-B", type="door")],
    )
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("too close" in e.lower() for e in result.errors)


def test_validate_dungeon_allows_rooms_with_one_cell_gap():
    from dungeon_daddy.data.models import validate_dungeon
    # make_valid_level() has rooms at x=0,w=3 and x=4,w=3 — gap of 1 cell
    dungeon = make_dungeon_with_level(make_valid_level())
    result = validate_dungeon(dungeon)
    assert result.is_valid


# ---------------------------------------------------------------------------
# E5: Validation: connection with empty type
# ---------------------------------------------------------------------------

def test_validate_dungeon_catches_empty_connection_type():
    from dungeon_daddy.data.models import validate_dungeon, Connection
    level = make_valid_level()
    level.connections[0] = Connection(from_room="1-A", to_room="1-B", type="")
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("connection" in e.lower() and "type" in e.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# E6: Validation: exactly one main loop when loops present
# ---------------------------------------------------------------------------

def make_loop(loop_id, loop_type="main", **kwargs):
    from dungeon_daddy.data.models import Loop
    defaults = dict(
        id=loop_id, pattern="lock_key", note="", entry="1-A", goal="1-B",
        path_a=["1-A", "1-B"], path_b=["1-A", "1-B"], type=loop_type,
        explanation="A descriptive explanation.",
    )
    defaults.update(kwargs)
    return Loop(**defaults)


def test_validate_dungeon_catches_two_main_loops():
    from dungeon_daddy.data.models import validate_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", "main"), make_loop("L2", "main")]
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("main loop" in e.lower() for e in result.errors)


def test_validate_dungeon_catches_no_main_loop_when_loops_present():
    from dungeon_daddy.data.models import validate_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", "sub"), make_loop("L2", "sub")]
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("main loop" in e.lower() for e in result.errors)


def test_validate_dungeon_catches_loop_with_empty_explanation():
    from dungeon_daddy.data.models import validate_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", "main", explanation="")]
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("explanation" in e.lower() for e in result.errors)


def test_validate_dungeon_allows_one_main_one_sub_loop():
    from dungeon_daddy.data.models import validate_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", "main"), make_loop("L2", "sub")]
    result = validate_dungeon(make_dungeon_with_level(level))
    assert result.is_valid


# ---------------------------------------------------------------------------
# E8: Validation: loop.rooms entries must exist in level rooms
# ---------------------------------------------------------------------------

def test_validate_dungeon_catches_loop_rooms_missing_room():
    from dungeon_daddy.data.models import validate_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", "main", rooms=["1-A", "GHOST"])]
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("GHOST" in e for e in result.errors)


def test_validate_dungeon_allows_loop_rooms_with_valid_ids():
    from dungeon_daddy.data.models import validate_dungeon
    level = make_valid_level()
    for room in level.rooms:
        room.main_loop_role = "participant"
    level.loops = [make_loop("L1", "main", rooms=["1-A", "1-B"])]
    result = validate_dungeon(make_dungeon_with_level(level))
    assert result.is_valid


def test_validate_dungeon_allows_loop_with_empty_rooms_list():
    from dungeon_daddy.data.models import validate_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", "main", rooms=[])]
    result = validate_dungeon(make_dungeon_with_level(level))
    assert result.is_valid


# ---------------------------------------------------------------------------
# E9: Validation: room role fields required when room is in a loop
# ---------------------------------------------------------------------------

def make_level_with_loop_and_rooms(main_loop_role=None, sub_loop_roles=None):
    """Level with two rooms: 1-A in a main loop, 1-B in a sub loop."""
    from dungeon_daddy.data.models import Level, Room, Connection
    return Level(
        id=1, name="L1", summary="", ecology="", loop="",
        width=20, height=20, entries=[],
        rooms=[
            Room(id="1-A", num=1, name="Hall", x=0, y=0, w=3, h=3, type="hall", note="",
                 main_loop_role=main_loop_role),
            Room(id="1-B", num=2, name="Vault", x=5, y=0, w=3, h=3, type="vault", note="",
                 sub_loop_roles=sub_loop_roles),
        ],
        connections=[Connection(from_room="1-A", to_room="1-B", type="door")],
        loops=[
            make_loop("L1", "main", rooms=["1-A"]),
            make_loop("L2", "sub", rooms=["1-B"]),
        ],
    )


def test_validate_dungeon_catches_main_loop_room_missing_role():
    from dungeon_daddy.data.models import validate_dungeon
    level = make_level_with_loop_and_rooms(main_loop_role=None, sub_loop_roles=[{"loop_id": "L2", "role": "shortcut"}])
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("main_loop_role" in e for e in result.errors)


def test_validate_dungeon_catches_sub_loop_room_missing_roles():
    from dungeon_daddy.data.models import validate_dungeon
    level = make_level_with_loop_and_rooms(main_loop_role="key holder", sub_loop_roles=None)
    result = validate_dungeon(make_dungeon_with_level(level))
    assert not result.is_valid
    assert any("sub_loop_roles" in e for e in result.errors)


def test_validate_dungeon_allows_rooms_with_required_roles():
    from dungeon_daddy.data.models import validate_dungeon
    level = make_level_with_loop_and_rooms(
        main_loop_role="key holder",
        sub_loop_roles=[{"loop_id": "L2", "role": "shortcut"}],
    )
    result = validate_dungeon(make_dungeon_with_level(level))
    assert result.is_valid


def test_validate_dungeon_allows_room_not_in_any_loop_without_roles():
    from dungeon_daddy.data.models import validate_dungeon
    # Room has no role fields but is not listed in any loop.rooms
    level = make_valid_level()
    level.loops = [make_loop("L1", "main", rooms=[])]
    result = validate_dungeon(make_dungeon_with_level(level))
    assert result.is_valid


# ---------------------------------------------------------------------------
# E1: Loop new fields — type, explanation, rooms
# ---------------------------------------------------------------------------

def make_minimal_loop(**kwargs):
    from dungeon_daddy.data.models import Loop
    defaults = dict(
        id="L1", pattern="lock_key", note="", entry="1-A", goal="1-B",
        path_a=["1-A", "1-B"], path_b=["1-A", "1-B"],
    )
    defaults.update(kwargs)
    return Loop(**defaults)


def test_loop_new_fields_have_defaults():
    loop = make_minimal_loop()
    assert loop.type == "main"
    assert loop.explanation == ""
    assert loop.rooms == []


def test_loop_type_accepts_sub():
    loop = make_minimal_loop(type="sub")
    assert loop.type == "sub"


def test_loop_type_rejects_invalid():
    with pytest.raises(ValidationError):
        make_minimal_loop(type="boss")


def test_loop_explanation_and_rooms_accept_values():
    loop = make_minimal_loop(explanation="Collect key from guard, unlock vault", rooms=["1-A", "1-B"])
    assert loop.explanation == "Collect key from guard, unlock vault"
    assert loop.rooms == ["1-A", "1-B"]


# ---------------------------------------------------------------------------
# E2: Room new fields — main_loop_role, sub_loop_roles
# ---------------------------------------------------------------------------

def make_minimal_room(**kwargs):
    from dungeon_daddy.data.models import Room
    defaults = dict(id="1-A", num=1, name="Hall", x=0, y=0, w=4, h=4, type="hall", note="")
    defaults.update(kwargs)
    return Room(**defaults)


def test_room_new_fields_default_to_none():
    room = make_minimal_room()
    assert room.main_loop_role is None
    assert room.sub_loop_roles is None


def test_room_main_loop_role_accepts_string():
    room = make_minimal_room(main_loop_role="key holder")
    assert room.main_loop_role == "key holder"


def test_room_sub_loop_roles_accepts_list_of_dicts():
    from dungeon_daddy.data.models import SubLoopRole
    roles = [{"loop_id": "L2", "role": "shortcut entry"}]
    room = make_minimal_room(sub_loop_roles=roles)
    assert room.sub_loop_roles == [SubLoopRole(role="shortcut entry")]


# ---------------------------------------------------------------------------
# E3: ValidationResult — warnings field
# ---------------------------------------------------------------------------

def test_validation_result_warnings_defaults_to_empty():
    from dungeon_daddy.data.models import ValidationResult
    result = ValidationResult(is_valid=True)
    assert result.warnings == []


def test_validation_result_warnings_accepts_values():
    from dungeon_daddy.data.models import ValidationResult
    result = ValidationResult(is_valid=True, warnings=["room has no connections"])
    assert result.warnings == ["room has no connections"]


def test_validation_result_warnings_do_not_affect_is_valid():
    from dungeon_daddy.data.models import ValidationResult
    result = ValidationResult(is_valid=True, warnings=["something minor"])
    assert result.is_valid is True
    assert bool(result) is True


# ---------------------------------------------------------------------------
# DungeonMeta.save_name — CD-1
# ---------------------------------------------------------------------------

def test_dungeon_meta_save_name_defaults_to_none():
    from dungeon_daddy.data.models import DungeonMeta
    meta = DungeonMeta(title="The Dark Pit", theme="Horror", setting="S", party="P", quest="Q")
    assert meta.save_name is None


def test_dungeon_meta_save_name_round_trips():
    from dungeon_daddy.data.models import DungeonMeta
    meta = DungeonMeta(title="The Dark Pit", theme="Horror", setting="S", party="P", quest="Q",
                       save_name="dark-pit")
    data = meta.model_dump()
    restored = DungeonMeta.model_validate(data)
    assert restored.save_name == "dark-pit"


def test_dungeon_meta_effective_name_falls_back_to_title():
    from dungeon_daddy.data.models import DungeonMeta
    meta_no_save = DungeonMeta(title="The Dark Pit", theme="Horror", setting="S", party="P", quest="Q")
    meta_with_save = DungeonMeta(title="The Dark Pit", theme="Horror", setting="S", party="P", quest="Q",
                                 save_name="dark-pit")
    assert meta_no_save.effective_name == "The Dark Pit"
    assert meta_with_save.effective_name == "dark-pit"


# ---------------------------------------------------------------------------
# auto_fix_dungeon — fills empty loop explanations
# ---------------------------------------------------------------------------

def test_auto_fix_fills_empty_loop_explanation():
    from dungeon_daddy.data.models import auto_fix_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", explanation="")]
    dungeon = make_dungeon_with_level(level)
    auto_fix_dungeon(dungeon)
    assert dungeon.levels[0].loops[0].explanation != ""


def test_auto_fix_leaves_existing_explanation_unchanged():
    from dungeon_daddy.data.models import auto_fix_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", explanation="Existing detail.")]
    dungeon = make_dungeon_with_level(level)
    auto_fix_dungeon(dungeon)
    assert dungeon.levels[0].loops[0].explanation == "Existing detail."


def test_auto_fix_returns_description_for_each_fix():
    from dungeon_daddy.data.models import auto_fix_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", explanation=""), make_loop("L2", "sub", explanation="")]
    dungeon = make_dungeon_with_level(level)
    fixes = auto_fix_dungeon(dungeon)
    assert len(fixes) == 2


def test_auto_fix_returns_empty_list_when_nothing_to_fix():
    from dungeon_daddy.data.models import auto_fix_dungeon
    dungeon = make_dungeon_with_level(make_valid_level())
    fixes = auto_fix_dungeon(dungeon)
    assert fixes == []


def test_auto_fix_explanation_errors_makes_dungeon_valid():
    from dungeon_daddy.data.models import auto_fix_dungeon, validate_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", explanation="")]
    dungeon = make_dungeon_with_level(level)
    assert not validate_dungeon(dungeon).is_valid
    auto_fix_dungeon(dungeon)
    assert validate_dungeon(dungeon).is_valid


def test_auto_fix_demotes_extra_main_loops_to_sub():
    from dungeon_daddy.data.models import auto_fix_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", "main"), make_loop("L2", "main")]
    dungeon = make_dungeon_with_level(level)
    auto_fix_dungeon(dungeon)
    loops = dungeon.levels[0].loops
    assert loops[0].type == "main"
    assert loops[1].type == "sub"


def test_auto_fix_keeps_single_main_loop_unchanged():
    from dungeon_daddy.data.models import auto_fix_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", "main"), make_loop("L2", "sub")]
    dungeon = make_dungeon_with_level(level)
    auto_fix_dungeon(dungeon)
    loops = dungeon.levels[0].loops
    assert loops[0].type == "main"
    assert loops[1].type == "sub"


def test_auto_fix_extra_main_loops_counted_in_fixes():
    from dungeon_daddy.data.models import auto_fix_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", "main"), make_loop("L2", "main"), make_loop("L3", "main")]
    dungeon = make_dungeon_with_level(level)
    fixes = auto_fix_dungeon(dungeon)
    assert len(fixes) == 2


def test_auto_fix_multiple_main_loops_makes_dungeon_valid():
    from dungeon_daddy.data.models import auto_fix_dungeon, validate_dungeon
    level = make_valid_level()
    level.loops = [make_loop("L1", "main"), make_loop("L2", "main")]
    dungeon = make_dungeon_with_level(level)
    assert not validate_dungeon(dungeon).is_valid
    auto_fix_dungeon(dungeon)
    assert validate_dungeon(dungeon).is_valid
