"""Tests for DungeonGeneratorAgent."""
import json

import pytest

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class _MockProvider:
    def __init__(self, response=""):
        self._response = response
        self.last_system = ""
        self.last_messages = []
        self.last_response_format: dict | None = None

    def complete(self, messages, system="", max_tokens=1024, response_format=None):
        self.last_system = system
        self.last_messages = messages
        self.last_response_format = response_format
        return self._response

    @property
    def model_id(self):
        return "mock"


def _make_brief():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonBrief
    return DungeonBrief(
        title="Tomb of the Forgotten King",
        theme="Undead",
        setting="A collapsed royal tomb.",
        party="4 adventurers, level 3",
        quest="Recover the Crown.",
        num_levels=3,
        gm_notes="",
    )


def _make_level_brief(level_number=1, sub_loop_pattern=None, gm_notes=""):
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    return LevelBrief(
        level_number=level_number,
        ecology="Undead — 4 skeleton warriors",
        main_loop_pattern="lock_key",
        sub_loop_pattern=sub_loop_pattern,
        gm_notes=gm_notes,
    )


def _make_empty_dungeon():
    from dungeon_daddy.data.models import Dungeon, DungeonMeta
    return Dungeon(
        meta=DungeonMeta(
            title="Tomb of the Forgotten King",
            theme="Undead", setting="A tomb.", party="4 adventurers", quest="Find the key.",
        ),
        levels=[],
    )


def _make_valid_level_json() -> str:
    level = {
        "id": 1,
        "name": "The Sunken Vestibule",
        "summary": "A flooded entry hall.",
        "ecology": "4 goblin archers",
        "loop": "lock_key",
        "width": 12,
        "height": 10,
        "entries": [],
        "rooms": [
            {"id": "1-A", "num": 1, "name": "Entry Hall",
             "x": 0, "y": 0, "w": 3, "h": 3, "type": "hall", "note": ""},
            {"id": "1-B", "num": 2, "name": "Guard Room",
             "x": 5, "y": 0, "w": 3, "h": 3, "type": "hall", "note": ""},
        ],
        "connections": [
            {"from": "1-A", "to": "1-B", "type": "door", "note": ""},
        ],
        "loops": [],
    }
    return f"```json\n{json.dumps(level, indent=2)}\n```"


def _make_minimal_level_json_raw() -> str:
    """Same level dict as _make_valid_level_json but returned as raw JSON (no markdown fence)."""
    level = {
        "id": 1,
        "name": "The Sunken Vestibule",
        "summary": "A flooded entry hall.",
        "ecology": "4 goblin archers",
        "loop": "lock_key",
        "width": 12,
        "height": 10,
        "entries": [],
        "rooms": [
            {"id": "1-A", "num": 1, "name": "Entry Hall",
             "x": 0, "y": 0, "w": 3, "h": 3, "type": "hall", "note": ""},
            {"id": "1-B", "num": 2, "name": "Guard Room",
             "x": 5, "y": 0, "w": 3, "h": 3, "type": "hall", "note": ""},
        ],
        "connections": [
            {"from": "1-A", "to": "1-B", "type": "door", "note": ""},
        ],
        "loops": [],
    }
    return json.dumps(level)


# ---------------------------------------------------------------------------
# Behavior 1: generate_level() calls provider.complete() and returns response
# ---------------------------------------------------------------------------

def test_generate_level_calls_provider():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    provider = _MockProvider(response=_make_valid_level_json())
    agent = DungeonGeneratorAgent(provider=provider)
    result = agent.generate_level(_make_brief(), _make_level_brief(), _make_empty_dungeon())
    assert result == _make_valid_level_json()


def test_generate_level_sends_empty_messages():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    provider = _MockProvider(response=_make_valid_level_json())
    agent = DungeonGeneratorAgent(provider=provider)
    agent.generate_level(_make_brief(), _make_level_brief(), _make_empty_dungeon())
    assert provider.last_messages == []


def test_generate_level_uses_large_max_tokens():
    """Generator needs at least 4096 tokens for valid JSON output."""
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    calls = []

    class _TrackingProvider:
        def complete(self, messages, system="", max_tokens=1024, response_format=None):
            calls.append(max_tokens)
            return _make_valid_level_json()

        @property
        def model_id(self):
            return "mock"

    agent = DungeonGeneratorAgent(provider=_TrackingProvider())
    agent.generate_level(_make_brief(), _make_level_brief(), _make_empty_dungeon())
    assert calls[0] >= 4096


# ---------------------------------------------------------------------------
# Behavior 2: parse_level() returns a Level from a valid ```json``` block
# ---------------------------------------------------------------------------

def test_parse_level_returns_level_object():
    from dungeon_daddy.data.models import Level
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    level = agent.parse_level(_make_valid_level_json())
    assert isinstance(level, Level)


def test_parse_level_extracts_correct_fields():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    level = agent.parse_level(_make_valid_level_json())
    assert level.id == 1
    assert level.name == "The Sunken Vestibule"
    assert len(level.rooms) == 2
    assert len(level.connections) == 1


# ---------------------------------------------------------------------------
# Behavior 3: parse_level() raises ValueError when no ```json``` block present
# ---------------------------------------------------------------------------

def test_parse_level_raises_on_missing_block():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    with pytest.raises(ValueError):
        agent.parse_level("Here is a dungeon, but no JSON block.")


def test_parse_level_raises_on_empty_string():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    with pytest.raises(ValueError):
        agent.parse_level("")


def _make_level_json_with_null_sub_loop_roles() -> str:
    level = {
        "id": 1,
        "name": "The Crucible",
        "summary": "s",
        "ecology": "e",
        "loop": "pursuit",
        "width": 30,
        "height": 20,
        "entries": [],
        "rooms": [
            {"id": "R1", "num": 1, "name": "Entry", "x": 0, "y": 0, "w": 3, "h": 3,
             "type": "hall", "note": "", "main_loop_role": "entry", "sub_loop_roles": None},
            {"id": "R2", "num": 2, "name": "Mid", "x": 5, "y": 0, "w": 3, "h": 3,
             "type": "hall", "note": "", "main_loop_role": "obstacle", "sub_loop_roles": None},
            {"id": "R3", "num": 3, "name": "Goal", "x": 10, "y": 0, "w": 3, "h": 3,
             "type": "hall", "note": "", "main_loop_role": "goal", "sub_loop_roles": None},
        ],
        "connections": [
            {"from": "R1", "to": "R2", "type": "door", "note": ""},
            {"from": "R2", "to": "R3", "type": "door", "note": ""},
        ],
        "loops": [
            {
                "id": "L1", "pattern": "pursuit", "note": "main", "type": "main",
                "entry": "R1", "goal": "R3", "explanation": "main loop",
                "path_a": ["R1", "R2", "R3"], "path_b": ["R1", "R3"],
                "rooms": ["R1", "R2", "R3"],
            },
            {
                "id": "L2", "pattern": "pursuit", "note": "sub", "type": "sub",
                "entry": "R1", "goal": "R2", "explanation": "sub loop",
                "path_a": ["R1", "R2"], "path_b": ["R1", "R2"],
                "rooms": ["R1", "R2"],
            },
        ],
    }
    return f"```json\n{json.dumps(level, indent=2)}\n```"


def test_parse_level_coerces_null_sub_loop_roles_for_sub_loop_entry():
    """Room that is the entry of a sub-loop gets sub_loop_roles=[{role:entry}]."""
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    result = agent.parse_level(_make_level_json_with_null_sub_loop_roles())
    room_by_id = {r.id: r for r in result.rooms}
    assert room_by_id["R1"].sub_loop_roles is not None
    assert any(d.role == "entry" for d in room_by_id["R1"].sub_loop_roles)


def test_parse_level_coerces_null_sub_loop_roles_for_sub_loop_goal():
    """Room that is the goal of a sub-loop gets sub_loop_roles=[{role:goal}]."""
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    result = agent.parse_level(_make_level_json_with_null_sub_loop_roles())
    room_by_id = {r.id: r for r in result.rooms}
    assert room_by_id["R2"].sub_loop_roles is not None
    assert any(d.role == "goal" for d in room_by_id["R2"].sub_loop_roles)


def test_parse_level_leaves_sub_loop_roles_null_for_rooms_not_in_sub_loop():
    """Room not in any sub-loop keeps sub_loop_roles=None."""
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    result = agent.parse_level(_make_level_json_with_null_sub_loop_roles())
    room_by_id = {r.id: r for r in result.rooms}
    # R3 is only in the main loop (L1), not in the sub-loop (L2)
    assert room_by_id["R3"].sub_loop_roles is None


def test_parse_level_does_not_overwrite_existing_sub_loop_roles():
    """Room that already has sub_loop_roles set is not overwritten."""
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    level = {
        "id": 1, "name": "T", "summary": "s", "ecology": "e", "loop": "pursuit",
        "width": 20, "height": 10, "entries": [],
        "rooms": [
            {"id": "R1", "num": 1, "name": "A", "x": 0, "y": 0, "w": 3, "h": 3,
             "type": "hall", "note": "", "main_loop_role": "entry",
             "sub_loop_roles": [{"role": "custom"}]},
            {"id": "R2", "num": 2, "name": "B", "x": 5, "y": 0, "w": 3, "h": 3,
             "type": "hall", "note": "", "main_loop_role": "goal",
             "sub_loop_roles": None},
        ],
        "connections": [{"from": "R1", "to": "R2", "type": "door", "note": ""}],
        "loops": [
            {
                "id": "L1", "pattern": "pursuit", "note": "", "type": "main",
                "entry": "R1", "goal": "R2", "explanation": "main",
                "path_a": ["R1", "R2"], "path_b": ["R1", "R2"],
                "rooms": ["R1", "R2"],
            },
            {
                "id": "L2", "pattern": "pursuit", "note": "", "type": "sub",
                "entry": "R1", "goal": "R2", "explanation": "sub",
                "path_a": ["R1", "R2"], "path_b": ["R1", "R2"],
                "rooms": ["R1", "R2"],
            },
        ],
    }
    json_str = f"```json\n{json.dumps(level, indent=2)}\n```"
    agent = DungeonGeneratorAgent(provider=_MockProvider())
    result = agent.parse_level(json_str)
    room_by_id = {r.id: r for r in result.rooms}
    from dungeon_daddy.data.models import SubLoopRole
    # R1 already had custom role — must not be overwritten
    assert room_by_id["R1"].sub_loop_roles == [SubLoopRole(role="custom")]
    # R2 had null but is the goal of L2
    assert any(d.role == "goal" for d in room_by_id["R2"].sub_loop_roles)


# ---------------------------------------------------------------------------
# Behavior 4: _build_context() includes brief, schema, and level number
# ---------------------------------------------------------------------------

def test_build_context_includes_brief_title():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), _make_level_brief(), _make_empty_dungeon(), None)
    assert "Tomb of the Forgotten King" in ctx


def test_build_context_includes_level_number():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), _make_level_brief(level_number=2), _make_empty_dungeon(), None)
    assert "2" in ctx


def test_build_context_includes_validation_errors_when_provided():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    errors = ["Room '1-A' is unreachable.", "Self-connection on room '1-B'."]
    ctx = agent._build_context(_make_brief(), _make_level_brief(), _make_empty_dungeon(), errors)
    assert "1-A" in ctx
    assert "1-B" in ctx


def test_build_context_no_errors_section_when_none():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), _make_level_brief(), _make_empty_dungeon(), None)
    assert "(none)" in ctx  # implementation appends literal "(none)" when no errors


# ---------------------------------------------------------------------------
# Behavior C2: _build_context() includes ecology from LevelBrief
# ---------------------------------------------------------------------------

def test_build_context_includes_ecology():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), _make_level_brief(), _make_empty_dungeon(), None)
    assert "Ecology: Undead — 4 skeleton warriors" in ctx


# ---------------------------------------------------------------------------
# Behavior C3: _build_context() includes main_loop_pattern from LevelBrief
# ---------------------------------------------------------------------------

def test_build_context_includes_main_loop_pattern():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), _make_level_brief(), _make_empty_dungeon(), None)
    assert "Main loop pattern: lock_key" in ctx


# ---------------------------------------------------------------------------
# Behavior C4: _build_context() includes sub_loop_pattern when present
# ---------------------------------------------------------------------------

def test_build_context_includes_sub_loop_when_present():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    lb = _make_level_brief(sub_loop_pattern="gauntlet")
    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), lb, _make_empty_dungeon(), None)
    assert "Sub-loop pattern: gauntlet" in ctx


# ---------------------------------------------------------------------------
# Behavior C5: _build_context() marks sub_loop absent when None
# ---------------------------------------------------------------------------

def test_build_context_marks_sub_loop_absent_when_none():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    lb = _make_level_brief(sub_loop_pattern=None)
    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), lb, _make_empty_dungeon(), None)
    assert "Sub-loop pattern: none" in ctx


# ---------------------------------------------------------------------------
# Behavior C6: _build_context() includes gm_notes when non-empty
# ---------------------------------------------------------------------------

def test_build_context_includes_gm_notes_when_set():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    lb = _make_level_brief(gm_notes="Hidden lever behind the altar, spike trap at entrance")
    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), lb, _make_empty_dungeon(), None)
    assert "Hidden lever behind the altar" in ctx


def test_build_context_omits_gm_notes_when_empty():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    lb = _make_level_brief(gm_notes="")
    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), lb, _make_empty_dungeon(), None)
    assert "GM notes" not in ctx


# ---------------------------------------------------------------------------
# E13: _build_context() schema includes new Loop fields
# ---------------------------------------------------------------------------

def test_build_context_schema_includes_new_loop_fields():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), _make_level_brief(), _make_empty_dungeon(), None)
    assert "type" in ctx
    assert "explanation" in ctx
    assert "rooms" in ctx


# ---------------------------------------------------------------------------
# E13: _build_context() schema includes new Room fields
# ---------------------------------------------------------------------------

def test_build_context_schema_includes_new_room_fields():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), _make_level_brief(), _make_empty_dungeon(), None)
    assert "main_loop_role" in ctx
    assert "sub_loop_roles" in ctx


# ---------------------------------------------------------------------------
# Spacing rule in SYSTEM_PROMPT
# ---------------------------------------------------------------------------

def test_system_prompt_mentions_gap_rule():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    prompt = DungeonGeneratorAgent.SYSTEM_PROMPT
    assert "1 empty cell" in prompt


def test_system_prompt_includes_concrete_gap_example():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    prompt = DungeonGeneratorAgent.SYSTEM_PROMPT
    # Must show a numeric example: a right-edge value and minimum start for next room
    assert "right edge" in prompt.lower()
    assert "x≥" in prompt


# ---------------------------------------------------------------------------
# Loop room role rule in _build_context()
# ---------------------------------------------------------------------------

def test_build_context_includes_loop_room_role_rule():
    """Context must tell the LLM that every room in loop.rooms needs its role set."""
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), _make_level_brief(), _make_empty_dungeon(), None)
    assert "loop.rooms" in ctx
    assert "main_loop_role" in ctx
    assert "sub_loop_roles" in ctx


def test_build_context_loop_role_rule_covers_both_loop_types():
    """Context must cover both main and sub loop type requirements."""
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_brief(), _make_level_brief(), _make_empty_dungeon(), None)
    assert '"main"' in ctx
    assert '"sub"' in ctx


# ---------------------------------------------------------------------------
# SI-5 Behavior 1: parse_level() raises pydantic.ValidationError for
# valid JSON that fails the Level schema (missing required field)
# ---------------------------------------------------------------------------

def _make_level_json_missing_name() -> str:
    """Valid JSON structure but missing required 'name' field."""
    level = {
        "id": 1,
        # "name" intentionally omitted
        "summary": "A flooded entry hall.",
        "ecology": "4 goblin archers",
        "loop": "lock_key",
        "width": 12,
        "height": 10,
        "entries": [],
        "rooms": [
            {"id": "1-A", "num": 1, "name": "Entry Hall",
             "x": 0, "y": 0, "w": 3, "h": 3, "type": "hall", "note": ""},
        ],
        "connections": [],
        "loops": [],
    }
    return f"```json\n{json.dumps(level, indent=2)}\n```"


def test_parse_level_missing_required_field_raises_pydantic_validation_error():
    """JSON that parses fine but fails Level schema raises pydantic.ValidationError."""
    from pydantic import ValidationError

    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    with pytest.raises(ValidationError):
        agent.parse_level(_make_level_json_missing_name())


# ---------------------------------------------------------------------------
# SI-5 Behavior 2: parse_level() raises ValueError when two rooms in the
# same loop claim the same main_loop_role (conflicting roles)
# ---------------------------------------------------------------------------

def _make_level_json_duplicate_main_loop_role() -> str:
    """Two rooms in the main loop both claim main_loop_role='goal'."""
    level = {
        "id": 1,
        "name": "The Sunken Vestibule",
        "summary": "A flooded entry hall.",
        "ecology": "4 goblin archers",
        "loop": "lock_key",
        "width": 20,
        "height": 10,
        "entries": [],
        "rooms": [
            {"id": "R1", "num": 1, "name": "Entry",
             "x": 0, "y": 0, "w": 3, "h": 3, "type": "hall", "note": "",
             "main_loop_role": "entry", "sub_loop_roles": None},
            {"id": "R2", "num": 2, "name": "First Goal",
             "x": 5, "y": 0, "w": 3, "h": 3, "type": "hall", "note": "",
             "main_loop_role": "goal", "sub_loop_roles": None},
            {"id": "R3", "num": 3, "name": "Second Goal",
             "x": 10, "y": 0, "w": 3, "h": 3, "type": "hall", "note": "",
             "main_loop_role": "goal", "sub_loop_roles": None},
        ],
        "connections": [
            {"from": "R1", "to": "R2", "type": "door", "note": ""},
            {"from": "R2", "to": "R3", "type": "door", "note": ""},
        ],
        "loops": [
            {
                "id": "L1", "pattern": "lock_key", "note": "", "type": "main",
                "entry": "R1", "goal": "R2", "explanation": "main loop",
                "path_a": ["R1", "R2", "R3"], "path_b": ["R1", "R3"],
                "rooms": ["R1", "R2", "R3"],
            },
        ],
    }
    return f"```json\n{json.dumps(level, indent=2)}\n```"


def test_parse_level_duplicate_main_loop_role_in_same_loop_raises():
    """Two rooms in the same loop with identical main_loop_role must raise ValueError."""
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    with pytest.raises(ValueError, match="duplicate.*main_loop_role|main_loop_role.*duplicate"):
        agent.parse_level(_make_level_json_duplicate_main_loop_role())


# ---------------------------------------------------------------------------
# Behavior: generate_level calls provider with response_format=json_object
# ---------------------------------------------------------------------------

def test_generate_level_passes_json_object_response_format():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    provider = _MockProvider(response=_make_minimal_level_json_raw())
    agent = DungeonGeneratorAgent(provider=provider)
    agent.generate_level(_make_brief(), _make_level_brief(), _make_empty_dungeon())

    assert provider.last_response_format == {"type": "json_object"}


# ---------------------------------------------------------------------------
# Behavior: parse_level() handles raw JSON (no markdown fence)
# ---------------------------------------------------------------------------

def test_parse_level_handles_raw_json_without_markdown_fence():
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent

    agent = DungeonGeneratorAgent(provider=_MockProvider())
    level = agent.parse_level(_make_minimal_level_json_raw())

    assert level.id == 1
    assert level.name == "The Sunken Vestibule"
