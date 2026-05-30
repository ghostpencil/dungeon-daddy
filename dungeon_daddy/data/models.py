"""All Pydantic data models for Dungeon Daddy."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContextDocType(StrEnum):
    SETTING = "setting"
    PARTY = "party"
    LEVEL_DESIGN = "level_design"


class DesignMode(StrEnum):
    WIZARD = "wizard"
    LEVEL_WIZARD = "level_wizard"
    GENERATION = "generation"
    EDIT = "edit"


# ---------------------------------------------------------------------------
# Loop pattern (loaded from bundled catalog)
# ---------------------------------------------------------------------------

class LoopPattern(BaseModel):
    key: str
    name: str
    blurb: str
    path_a_length: str
    path_b_length: str
    beats: list[str]
    source: str


# ---------------------------------------------------------------------------
# Loop instance (applied to a level)
# ---------------------------------------------------------------------------

class Loop(BaseModel):
    id: str
    pattern: str
    note: str
    entry: str
    goal: str
    path_a: list[str]
    path_b: list[str]
    type: Literal["main", "sub"] = "main"
    explanation: str = ""
    rooms: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

class SubLoopRole(BaseModel):
    role: str


class Room(BaseModel):
    id: str
    num: int
    name: str
    x: int
    y: int
    w: int
    h: int
    type: str
    note: str
    main_loop_role: str | None = None
    sub_loop_roles: list[SubLoopRole] | None = None
    layout_role: str | None = None
    tags: list[str] = Field(default_factory=list)


class Waypoint(BaseModel):
    x: float
    y: float


# ---------------------------------------------------------------------------
# Connection  (from/to aliases for JSON compatibility)
# ---------------------------------------------------------------------------

class Connection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_room: str = Field(alias="from")
    to_room: str = Field(alias="to")
    type: str
    note: str = ""
    waypoints: list[Waypoint] | None = None
    connection_style: str | None = None
    layout_connection_role: str | None = None


# ---------------------------------------------------------------------------
# Entry (staircase / access marker)
# ---------------------------------------------------------------------------

class Entry(BaseModel):
    x: float
    y: float
    type: str
    label: str


# ---------------------------------------------------------------------------
# Floor-level layout metadata (Phase 2.5 semantic backfill)
# ---------------------------------------------------------------------------

class LayoutMetadata(BaseModel):
    graph_template: str | None = None
    entrance_room_id: str | None = None
    endpoint_room_id: str | None = None
    objective_room_ids: list[str] = Field(default_factory=list)
    critical_path: list[str] = Field(default_factory=list)
    optional_branches: list[list[str]] = Field(default_factory=list)
    notes: str | None = None


# ---------------------------------------------------------------------------
# Level
# ---------------------------------------------------------------------------

class Level(BaseModel):
    id: int
    name: str
    summary: str
    ecology: str
    loop: str
    loops: list[Loop] = []
    width: int
    height: int
    entries: list[Entry]
    rooms: list[Room]
    connections: list[Connection]
    floor_tags: list[str] = Field(default_factory=list)
    layout_metadata: LayoutMetadata | None = None


# ---------------------------------------------------------------------------
# Dungeon metadata
# ---------------------------------------------------------------------------

class DungeonMeta(BaseModel):
    schema_version: str = "1.0"
    title: str
    theme: str
    setting: str
    party: str
    quest: str
    party_size: int = 0
    party_level: int = 0
    num_levels: int = 3
    complexity: str = "Moderate"
    save_name: str | None = None

    @property
    def effective_name(self) -> str:
        return self.save_name or self.title


# ---------------------------------------------------------------------------
# Root dungeon object
# ---------------------------------------------------------------------------

class Dungeon(BaseModel):
    meta: DungeonMeta
    levels: list[Level]
    loop_patterns: dict[str, LoopPattern] = {}


# ---------------------------------------------------------------------------
# Chat message (persisted transcript)
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: Literal["gm", "dm", "system"]
    content: str


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

class SessionState(BaseModel):
    dungeon_id: str
    current_level_idx: int = 0
    current_room_id: str | None = None
    visited_rooms: list[str] = []
    map_variant: str = "grid"
    active_loop_id: str | None = None
    play_transcript: list[ChatMessage] = []
    design_transcript: list[ChatMessage] = []


# ---------------------------------------------------------------------------
# Validation result (plain dataclass — never serialised)
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.is_valid


# ---------------------------------------------------------------------------
# Loop pattern catalog
# ---------------------------------------------------------------------------

class LoopPatternCatalog(BaseModel):
    patterns: dict[str, LoopPattern]

    @classmethod
    def load_bundled(cls) -> LoopPatternCatalog:
        import importlib.resources
        import json
        pkg_files = importlib.resources.files("dungeon_daddy.data")
        raw = (pkg_files / "loop_patterns.json").read_text(encoding="utf-8")
        return cls.model_validate({"patterns": json.loads(raw)})


# ---------------------------------------------------------------------------
# Dungeon validation
# ---------------------------------------------------------------------------

def validate_dungeon(dungeon: Dungeon) -> ValidationResult:
    """Run all validation rules across every level."""
    errors: list[str] = []
    for level in dungeon.levels:
        _check_no_duplicate_room_ids(level, errors)
        _check_connectivity(level, errors)
        _check_loop_room_references(level, errors)
        _check_entry_goal_exist(level, errors)
        _check_no_self_connections(level, errors)
        _check_grid_bounds(level, errors)
        _check_no_overlapping_rooms(level, errors)
        _check_room_spacing(level, errors)
        _check_connection_type(level, errors)
        _check_exactly_one_main_loop(level, errors)
        _check_loop_explanations(level, errors)
        _check_loop_rooms_exist(level, errors)
        _check_loop_room_roles(level, errors)
        if dungeon.loop_patterns:
            _check_level_loop_pattern_exists(level, dungeon.loop_patterns, errors)
    return ValidationResult(is_valid=len(errors) == 0, errors=errors)


def auto_fix_dungeon(dungeon: Dungeon) -> list[str]:
    """Apply automatic fixes for common validation errors. Returns descriptions of each fix applied."""
    fixes: list[str] = []
    for level in dungeon.levels:
        for loop in level.loops:
            if not loop.explanation:
                loop.explanation = "Explanation pending."
                fixes.append(f"Level {level.id}, loop '{loop.id}': set default explanation.")
        main_loops = [lp for lp in level.loops if lp.type == "main"]
        for loop in main_loops[1:]:
            loop.type = "sub"
            fixes.append(f"Level {level.id}, loop '{loop.id}': demoted from main to sub (only one main loop allowed).")
    return fixes


def _check_no_duplicate_room_ids(level: Level, errors: list[str]) -> None:
    seen: set[str] = set()
    for room in level.rooms:
        if room.id in seen:
            errors.append(
                f"Level {level.id}: duplicate room id '{room.id}'."
            )
        seen.add(room.id)


def _check_connectivity(level: Level, errors: list[str]) -> None:
    if not level.rooms:
        return
    room_ids = {r.id for r in level.rooms}
    adjacency: dict[str, set[str]] = {rid: set() for rid in room_ids}
    for conn in level.connections:
        if conn.from_room in adjacency and conn.to_room in adjacency:
            adjacency[conn.from_room].add(conn.to_room)
            adjacency[conn.to_room].add(conn.from_room)

    start = level.rooms[0].id
    visited: set[str] = set()
    queue = [start]
    while queue:
        node = queue.pop()
        if node in visited:
            continue
        visited.add(node)
        queue.extend(adjacency[node] - visited)

    unreachable = room_ids - visited
    for rid in sorted(unreachable):
        errors.append(
            f"Level {level.id}: room '{rid}' is not reachable from '{start}'."
        )


def _check_loop_room_references(level: Level, errors: list[str]) -> None:
    room_ids = {r.id for r in level.rooms}
    for loop in level.loops:
        for rid in loop.path_a + loop.path_b:
            if rid not in room_ids:
                errors.append(
                    f"Level {level.id}, loop '{loop.id}': "
                    f"room '{rid}' in path does not exist."
                )


def _check_entry_goal_exist(level: Level, errors: list[str]) -> None:
    room_ids = {r.id for r in level.rooms}
    for loop in level.loops:
        if loop.entry not in room_ids:
            errors.append(
                f"Level {level.id}, loop '{loop.id}': "
                f"entry room '{loop.entry}' does not exist."
            )
        if loop.goal not in room_ids:
            errors.append(
                f"Level {level.id}, loop '{loop.id}': "
                f"goal room '{loop.goal}' does not exist."
            )


def _check_no_self_connections(level: Level, errors: list[str]) -> None:
    for conn in level.connections:
        if conn.from_room == conn.to_room:
            errors.append(
                f"Level {level.id}: self-connection on room '{conn.from_room}'."
            )


def _check_grid_bounds(level: Level, errors: list[str]) -> None:
    for room in level.rooms:
        if room.x + room.w > level.width:
            errors.append(
                f"Level {level.id}, room '{room.id}': "
                f"exceeds grid width ({room.x}+{room.w} > {level.width})."
            )
        if room.y + room.h > level.height:
            errors.append(
                f"Level {level.id}, room '{room.id}': "
                f"exceeds grid height ({room.y}+{room.h} > {level.height})."
            )


def _check_no_overlapping_rooms(level: Level, errors: list[str]) -> None:
    rooms = level.rooms
    for i, a in enumerate(rooms):
        for b in rooms[i + 1:]:
            if (a.x < b.x + b.w and a.x + a.w > b.x and
                    a.y < b.y + b.h and a.y + a.h > b.y):
                errors.append(
                    f"Level {level.id}: rooms '{a.id}' ({a.name}) and "
                    f"'{b.id}' ({b.name}) overlap on the grid. "
                    "Give each room a non-overlapping (x, y, w, h) rectangle."
                )


def _check_room_spacing(level: Level, errors: list[str]) -> None:
    rooms = level.rooms
    for i, a in enumerate(rooms):
        for b in rooms[i + 1:]:
            # Skip overlapping pairs (already caught by _check_no_overlapping_rooms)
            if (a.x < b.x + b.w and a.x + a.w > b.x and
                    a.y < b.y + b.h and a.y + a.h > b.y):
                continue
            x_gap = max(a.x, b.x) - min(a.x + a.w, b.x + b.w)
            y_gap = max(a.y, b.y) - min(a.y + a.h, b.y + b.h)
            if x_gap < 1 and y_gap < 1:
                errors.append(
                    f"Level {level.id}: rooms '{a.id}' ({a.name}) and "
                    f"'{b.id}' ({b.name}) are too close (gap < 1 cell). "
                    "Leave at least 1 empty cell between rooms."
                )


def _check_loop_room_roles(level: Level, errors: list[str]) -> None:
    room_by_id = {r.id: r for r in level.rooms}
    for lp in level.loops:
        for rid in lp.rooms:
            room = room_by_id.get(rid)
            if room is None:
                continue  # already caught by _check_loop_rooms_exist
            if lp.type == "main" and room.main_loop_role is None:
                errors.append(
                    f"Level {level.id}, loop '{lp.id}': "
                    f"room '{rid}' is in the main loop but has no main_loop_role."
                )
            elif lp.type == "sub" and room.sub_loop_roles is None:
                errors.append(
                    f"Level {level.id}, loop '{lp.id}': "
                    f"room '{rid}' is in a sub-loop but has no sub_loop_roles."
                )


def _check_loop_rooms_exist(level: Level, errors: list[str]) -> None:
    room_ids = {r.id for r in level.rooms}
    for lp in level.loops:
        for rid in lp.rooms:
            if rid not in room_ids:
                errors.append(
                    f"Level {level.id}, loop '{lp.id}': "
                    f"room '{rid}' in loop.rooms does not exist."
                )


def _check_loop_explanations(level: Level, errors: list[str]) -> None:
    for lp in level.loops:
        if not lp.explanation:
            errors.append(
                f"Level {level.id}, loop '{lp.id}': explanation is empty. "
                "Every loop must have a non-empty explanation."
            )


def _check_exactly_one_main_loop(level: Level, errors: list[str]) -> None:
    if not level.loops:
        return
    main_loops = [lp for lp in level.loops if lp.type == "main"]
    if len(main_loops) != 1:
        errors.append(
            f"Level {level.id}: found {len(main_loops)} main loop(s) but exactly 1 is required "
            "when loops are present."
        )


def _check_connection_type(level: Level, errors: list[str]) -> None:
    for conn in level.connections:
        if not conn.type:
            errors.append(
                f"Level {level.id}: connection from '{conn.from_room}' to "
                f"'{conn.to_room}' has an empty type. "
                "Every connection must have a non-empty type (e.g. 'door', 'corridor')."
            )


def _check_level_loop_pattern_exists(
    level: Level, loop_patterns: dict[str, LoopPattern], errors: list[str]
) -> None:
    if level.loop not in loop_patterns:
        errors.append(
            f"Level {level.id}: loop pattern key '{level.loop}' "
            "is not present in dungeon.loop_patterns."
        )
