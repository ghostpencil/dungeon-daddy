"""Tests for DungeonMasterAgent."""
import pytest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class _MockProvider:
    def __init__(self, response="The shadows shift as you enter."):
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


def _make_room():
    from dungeon_daddy.data.models import Room
    return Room(
        id="1-B", num=2, name="Guard Post",
        x=5, y=0, w=4, h=3, type="shrine",
        note="Four guards doze at a stone table.",
    )


def _make_level():
    from dungeon_daddy.data.models import Level, Room, Connection
    return Level(
        id=1, name="The Sunken Vestibule", summary="Flooded entry.",
        ecology="4 goblin archers, 1 ogre warlord",
        loop="lock_key", width=12, height=10, entries=[],
        rooms=[
            Room(id="1-A", num=1, name="Entry Hall",
                 x=0, y=0, w=3, h=3, type="hall", note=""),
            Room(id="1-B", num=2, name="Guard Post",
                 x=5, y=0, w=4, h=3, type="shrine",
                 note="Four guards doze at a stone table."),
        ],
        connections=[Connection(from_room="1-A", to_room="1-B", type="door")],
    )


def _make_dungeon():
    from dungeon_daddy.data.models import Dungeon, DungeonMeta
    return Dungeon(
        meta=DungeonMeta(
            title="Tomb of the Forgotten King",
            theme="Undead",
            setting="A collapsed royal tomb beneath a cursed moor.",
            party="4 adventurers, level 3",
            quest="Recover the Crown of Kings before the necromantic ceremony at dawn.",
        ),
        levels=[_make_level()],
    )


# ---------------------------------------------------------------------------
# Behavior 1: respond() calls provider.complete() and returns the text
# ---------------------------------------------------------------------------

def test_dm_respond_returns_provider_response():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.llm.provider import LLMMessage

    provider = _MockProvider(response="The door creaks open.")
    agent = DungeonMasterAgent(provider=provider)
    result = agent.respond(
        history=[LLMMessage(role="user", content="I enter the room.")],
        room=_make_room(),
        level=_make_level(),
        dungeon=_make_dungeon(),
    )
    assert result == "The door creaks open."


def test_dm_respond_passes_history():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.llm.provider import LLMMessage

    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    history = [LLMMessage(role="user", content="look around")]
    agent.respond(history=history, room=_make_room(),
                  level=_make_level(), dungeon=_make_dungeon())
    assert provider.last_messages == history


# ---------------------------------------------------------------------------
# Behavior 2: respond() includes room_memory in system prompt when non-empty
# ---------------------------------------------------------------------------

def test_dm_respond_includes_play_history_when_present():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    memory = "- 2026-04-23: Party bypassed sleeping guards using Silence.\n"
    agent.respond(
        history=[], room=_make_room(), level=_make_level(),
        dungeon=_make_dungeon(), room_memory=memory,
    )
    assert "Silence" in provider.last_system


def test_dm_respond_play_history_section_heading():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    agent.respond(
        history=[], room=_make_room(), level=_make_level(),
        dungeon=_make_dungeon(),
        room_memory="- 2026-04-24: Rogue found a hidden door.\n",
    )
    assert "Play History" in provider.last_system


# ---------------------------------------------------------------------------
# Behavior 3: respond() omits Play History section when room_memory is empty
# ---------------------------------------------------------------------------

def test_dm_respond_omits_play_history_when_empty():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    agent.respond(
        history=[], room=_make_room(), level=_make_level(),
        dungeon=_make_dungeon(), room_memory="",
    )
    assert "Play History" not in provider.last_system


# ---------------------------------------------------------------------------
# Behavior 4: _build_context() includes room, level, and dungeon details
# ---------------------------------------------------------------------------

def test_build_context_includes_room_name():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    agent = DungeonMasterAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_room(), _make_level(), _make_dungeon(), "")
    assert "Guard Post" in ctx


def test_build_context_includes_room_note():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    agent = DungeonMasterAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_room(), _make_level(), _make_dungeon(), "")
    assert "guards doze" in ctx


def test_build_context_includes_level_ecology():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    agent = DungeonMasterAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_room(), _make_level(), _make_dungeon(), "")
    assert "goblin" in ctx


def test_build_context_includes_dungeon_quest():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    agent = DungeonMasterAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_room(), _make_level(), _make_dungeon(), "")
    assert "Crown of Kings" in ctx


def test_build_context_includes_dungeon_title():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    agent = DungeonMasterAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_room(), _make_level(), _make_dungeon(), "")
    assert "Tomb of the Forgotten King" in ctx


# ---------------------------------------------------------------------------
# Helpers for context_builder tests
# ---------------------------------------------------------------------------

class _MockContextBuilder:
    def __init__(self, result="# Setting\nA dark dungeon."):
        self._result = result
        self.last_dungeon = None
        self.last_level_id = None

    def build_system_prompt(self, dungeon, level_id=None):
        self.last_dungeon = dungeon
        self.last_level_id = level_id
        return self._result


# ---------------------------------------------------------------------------
# Behavior 5: context_builder wired — context prepended to system prompt
# ---------------------------------------------------------------------------

def test_dm_respond_prepends_context_when_builder_set():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    provider = _MockProvider()
    builder = _MockContextBuilder(result="# Setting\nA dark dungeon.")
    agent = DungeonMasterAgent(provider=provider, context_builder=builder)
    agent.respond(
        history=[], room=_make_room(), level=_make_level(), dungeon=_make_dungeon()
    )
    assert provider.last_system.startswith("# Setting\nA dark dungeon.")


def test_dm_respond_context_builder_called_with_dungeon_and_level_id():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    provider = _MockProvider()
    builder = _MockContextBuilder()
    dungeon = _make_dungeon()
    agent = DungeonMasterAgent(provider=provider, context_builder=builder)
    agent.respond(
        history=[], room=_make_room(), level=_make_level(), dungeon=dungeon, level_id=2
    )
    assert builder.last_dungeon is dungeon
    assert builder.last_level_id == 2


def test_dm_respond_skips_context_when_builder_returns_empty():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    provider = _MockProvider()
    builder = _MockContextBuilder(result="")
    agent = DungeonMasterAgent(provider=provider, context_builder=builder)
    agent.respond(
        history=[], room=_make_room(), level=_make_level(), dungeon=_make_dungeon()
    )
    assert provider.last_system.startswith(DungeonMasterAgent.SYSTEM_PROMPT)


def test_dm_respond_no_context_builder_system_unchanged():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    agent.respond(
        history=[], room=_make_room(), level=_make_level(), dungeon=_make_dungeon()
    )
    assert provider.last_system.startswith(DungeonMasterAgent.SYSTEM_PROMPT)


# ---------------------------------------------------------------------------
# Phase 16 — Behavior: max_tokens is 1024
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Stabilisation — REMEMBER tag instructed for concrete party actions
# ---------------------------------------------------------------------------

def test_system_prompt_instructs_remember_tag_for_concrete_actions():
    """Prompt must instruct the DM to tag physical party actions."""
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    prompt = DungeonMasterAgent.SYSTEM_PROMPT
    assert "[REMEMBER:" in prompt
    # Prompt must name concrete physical actions (marking, manipulating objects, etc.)
    assert any(kw in prompt for kw in ("marking", "manipulat", "marking a location"))


def test_system_prompt_does_not_say_use_sparingly():
    """'Use it sparingly' caused the DM to skip the tag for notable party actions."""
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    assert "sparingly" not in DungeonMasterAgent.SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Behavior 6: respond() propagates LLMError (does not swallow exceptions)
# ---------------------------------------------------------------------------

def test_dm_respond_propagates_llm_error():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.llm.provider import LLMError, LLMMessage

    class _FailingProvider:
        def complete(self, messages, system="", max_tokens=512):
            raise LLMError("connection refused")

        @property
        def model_id(self):
            return "mock"

    agent = DungeonMasterAgent(provider=_FailingProvider())
    with pytest.raises(LLMError):
        agent.respond(
            history=[LLMMessage(role="user", content="Look around.")],
            room=_make_room(),
            level=_make_level(),
            dungeon=_make_dungeon(),
        )
