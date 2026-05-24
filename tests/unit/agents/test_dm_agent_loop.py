"""Tests for DungeonMasterAgent loop context injection (Phase 17 LV-1)."""
import pytest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class _MockProvider:
    def __init__(self, response="Shadows stir beyond the arch."):
        self._response = response
        self.last_system = ""
        self.last_messages = []
        self.last_max_tokens = None

    def complete(self, messages, system="", max_tokens=512):
        self.last_system = system
        self.last_messages = messages
        self.last_max_tokens = max_tokens
        return self._response

    @property
    def model_id(self):
        return "mock"


def _make_rooms():
    from dungeon_daddy.data.models import Room
    return [
        Room(id="1-A", num=1, name="Entry Hall",   x=0, y=0, w=3, h=3, type="hall",   note=""),
        Room(id="1-B", num=2, name="Guard Post",   x=5, y=0, w=4, h=3, type="shrine", note=""),
        Room(id="1-C", num=3, name="Vault Chamber",x=10,y=0, w=3, h=3, type="vault",  note=""),
        Room(id="1-D", num=4, name="Altar Room",   x=5, y=5, w=4, h=3, type="shrine", note=""),
    ]


def _make_level(current_room_id="1-B"):
    from dungeon_daddy.data.models import Level, Connection
    return Level(
        id=1, name="The Sunken Vestibule", summary="Flooded entry.",
        ecology="4 goblin archers", loop="lock_key",
        width=12, height=10, entries=[],
        rooms=_make_rooms(),
        connections=[Connection(from_room="1-A", to_room="1-B", type="door")],
    )


def _make_dungeon():
    from dungeon_daddy.data.models import Dungeon, DungeonMeta
    return Dungeon(
        meta=DungeonMeta(
            title="Tomb of the Forgotten King", theme="Undead",
            setting="A collapsed royal tomb.", party="4 adventurers",
            quest="Recover the Crown of Kings.",
        ),
        levels=[_make_level()],
    )


def _make_loop(path_a=None, path_b=None):
    from dungeon_daddy.data.models import Loop
    return Loop(
        id="loop-1",
        pattern="lock_key",
        note="The guardian blocks the vault.",
        entry="1-A",
        goal="1-C",
        path_a=path_a or ["1-A", "1-B", "1-C"],
        path_b=path_b or ["1-A", "1-D", "1-C"],
        explanation="Two routes to the vault: through the guard post or the altar.",
    )


def _make_room():
    from dungeon_daddy.data.models import Room
    return Room(
        id="1-B", num=2, name="Guard Post",
        x=5, y=0, w=4, h=3, type="shrine",
        note="Four guards doze at a stone table.",
    )


# ---------------------------------------------------------------------------
# Behavior 1: no active_loop → system prompt contains no loop section
# ---------------------------------------------------------------------------

def test_respond_without_loop_omits_loop_section():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    agent.respond(
        history=[], room=_make_room(),
        level=_make_level(), dungeon=_make_dungeon(),
        active_loop=None,
    )
    assert "Active Loop" not in provider.last_system


# ---------------------------------------------------------------------------
# Behavior 2: active_loop provided → system prompt contains loop section
# ---------------------------------------------------------------------------

def test_respond_with_loop_includes_loop_section():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    agent.respond(
        history=[], room=_make_room(),
        level=_make_level(), dungeon=_make_dungeon(),
        active_loop=_make_loop(),
    )
    assert "Active Loop" in provider.last_system


# ---------------------------------------------------------------------------
# Behavior 3: loop context includes pattern key and explanation
# ---------------------------------------------------------------------------

def test_loop_context_includes_pattern_and_explanation():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    agent.respond(
        history=[], room=_make_room(),
        level=_make_level(), dungeon=_make_dungeon(),
        active_loop=_make_loop(),
    )
    assert "lock_key" in provider.last_system
    assert "Two routes to the vault" in provider.last_system


# ---------------------------------------------------------------------------
# Behavior 4: loop context includes entry and goal as room names
# ---------------------------------------------------------------------------

def test_loop_context_includes_entry_and_goal():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    # Loop: entry=1-A ("Entry Hall"), goal=1-C ("Vault Chamber")
    agent.respond(
        history=[], room=_make_room(),
        level=_make_level(), dungeon=_make_dungeon(),
        active_loop=_make_loop(),
    )
    assert "Entry Hall" in provider.last_system
    assert "Vault Chamber" in provider.last_system


# ---------------------------------------------------------------------------
# Behaviors 5-8: current room placement on paths
# ---------------------------------------------------------------------------

def _respond_with_room_on(room_id, path_a, path_b):
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.data.models import Room
    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    room = Room(id=room_id, num=1, name="Test Room", x=0, y=0, w=3, h=3, type="hall", note="")
    agent.respond(
        history=[], room=room,
        level=_make_level(), dungeon=_make_dungeon(),
        active_loop=_make_loop(path_a=path_a, path_b=path_b),
    )
    return provider.last_system


def _current_room_line(system):
    """Extract the 'Current Room: ...' value from the Active Loop section."""
    return system.split("Current Room:")[1].split("\n")[0].strip()


def test_current_room_on_path_a_only():
    system = _respond_with_room_on("1-B", path_a=["1-A", "1-B", "1-C"], path_b=["1-A", "1-D", "1-C"])
    line = _current_room_line(system)
    assert "Path A" in line
    assert "Path B" not in line


def test_current_room_on_path_b_only():
    system = _respond_with_room_on("1-D", path_a=["1-A", "1-B", "1-C"], path_b=["1-A", "1-D", "1-C"])
    line = _current_room_line(system)
    assert "Path B" in line
    assert "Path A" not in line


def test_current_room_on_both_paths():
    system = _respond_with_room_on("1-A", path_a=["1-A", "1-B", "1-C"], path_b=["1-A", "1-D", "1-C"])
    line = _current_room_line(system)
    assert "Path A" in line
    assert "Path B" in line


def test_current_room_on_neither_path():
    from dungeon_daddy.data.models import Room
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    room = Room(id="1-X", num=9, name="Secret Alcove", x=0, y=0, w=2, h=2, type="hall", note="")
    agent.respond(
        history=[], room=room,
        level=_make_level(), dungeon=_make_dungeon(),
        active_loop=_make_loop(),
    )
    line = _current_room_line(provider.last_system)
    assert "neither" in line.lower()


# ---------------------------------------------------------------------------
# Behavior 9: path_a and path_b room IDs are resolved to room names
# ---------------------------------------------------------------------------

def test_path_rooms_resolved_to_names():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    # path_a: [1-A, 1-B, 1-C] → ["Entry Hall", "Guard Post", "Vault Chamber"]
    # path_b: [1-A, 1-D, 1-C] → ["Entry Hall", "Altar Room", "Vault Chamber"]
    agent.respond(
        history=[], room=_make_room(),
        level=_make_level(), dungeon=_make_dungeon(),
        active_loop=_make_loop(),
    )
    assert "Guard Post" in provider.last_system     # path_a room name
    assert "Altar Room" in provider.last_system     # path_b room name
    assert "1-B" not in provider.last_system        # IDs replaced by names
    assert "1-D" not in provider.last_system
