"""Tests for DesignAgent."""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class _MockProvider:
    def __init__(self, response="Here is my suggestion."):
        self._response = response
        self.last_system = ""
        self.last_messages = []

    def complete(self, messages, system="", max_tokens=1024):
        self.last_system = system
        self.last_messages = messages
        return self._response

    @property
    def model_id(self):
        return "mock"


def _make_dungeon():
    from dungeon_daddy.data.models import (
        Connection,
        Dungeon,
        DungeonMeta,
        Level,
        Room,
    )
    return Dungeon(
        meta=DungeonMeta(
            title="Tomb of the Forgotten King",
            theme="Undead",
            setting="A collapsed royal tomb beneath a cursed moor.",
            party="4 adventurers, level 3",
            quest="Recover the Crown of Kings.",
        ),
        levels=[
            Level(
                id=1, name="The Sunken Vestibule", summary="Flooded entry.",
                ecology="Goblins", loop="lock_key",
                width=12, height=10, entries=[],
                rooms=[
                    Room(id="1-A", num=1, name="Entry Hall",
                         x=0, y=0, w=3, h=3, type="hall", note=""),
                    Room(id="1-B", num=2, name="Guard Room",
                         x=5, y=0, w=3, h=3, type="hall", note=""),
                ],
                connections=[Connection(from_room="1-A", to_room="1-B", type="door")],
            ),
            Level(
                id=2, name="Hall of Bound Servants", summary="Where the cursed serve.",
                ecology="Skeletons", loop="gambit",
                width=12, height=10, entries=[],
                rooms=[
                    Room(id="2-A", num=1, name="Servant Hall",
                         x=0, y=0, w=3, h=3, type="hall", note=""),
                    Room(id="2-B", num=2, name="Ossuary",
                         x=5, y=0, w=3, h=3, type="shrine", note=""),
                ],
                connections=[Connection(from_room="2-A", to_room="2-B", type="arch")],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Behavior 1: DesignAgent.chat() calls provider.complete() and returns text
# ---------------------------------------------------------------------------

def test_design_chat_returns_provider_response():
    from dungeon_daddy.llm.agents.design_agent import DesignAgent
    from dungeon_daddy.llm.provider import LLMMessage

    provider = _MockProvider(response="Consider adding a vault room here.")
    agent = DesignAgent(provider=provider)
    result = agent.chat(
        [LLMMessage(role="user", content="Can you add more tension?")],
        _make_dungeon(),
    )
    assert result == "Consider adding a vault room here."


def test_design_chat_passes_history_to_provider():
    from dungeon_daddy.llm.agents.design_agent import DesignAgent
    from dungeon_daddy.llm.provider import LLMMessage

    provider = _MockProvider()
    agent = DesignAgent(provider=provider)
    history = [
        LLMMessage(role="user", content="question"),
        LLMMessage(role="assistant", content="answer"),
    ]
    agent.chat(history, _make_dungeon())
    assert provider.last_messages == history


def test_design_chat_includes_system_prompt():
    from dungeon_daddy.llm.agents.design_agent import DesignAgent

    provider = _MockProvider()
    agent = DesignAgent(provider=provider)
    agent.chat([], _make_dungeon())
    assert len(provider.last_system) > 0


# ---------------------------------------------------------------------------
# Behavior 2: _build_context() includes dungeon title and level summaries
# ---------------------------------------------------------------------------

def test_build_context_includes_title():
    from dungeon_daddy.llm.agents.design_agent import DesignAgent

    agent = DesignAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_dungeon())
    assert "Tomb of the Forgotten King" in ctx


def test_build_context_includes_theme():
    from dungeon_daddy.llm.agents.design_agent import DesignAgent

    agent = DesignAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_dungeon())
    assert "Undead" in ctx


def test_build_context_includes_all_level_names():
    from dungeon_daddy.llm.agents.design_agent import DesignAgent

    agent = DesignAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_dungeon())
    assert "Sunken Vestibule" in ctx
    assert "Hall of Bound Servants" in ctx


def test_build_context_includes_quest():
    from dungeon_daddy.llm.agents.design_agent import DesignAgent

    agent = DesignAgent(provider=_MockProvider())
    ctx = agent._build_context(_make_dungeon())
    assert "Crown of Kings" in ctx


def test_design_chat_system_includes_context():
    from dungeon_daddy.llm.agents.design_agent import DesignAgent

    provider = _MockProvider()
    agent = DesignAgent(provider=provider)
    dungeon = _make_dungeon()
    agent.chat([], dungeon)
    # The context from _build_context should be appended to the system prompt
    assert "Tomb of the Forgotten King" in provider.last_system
