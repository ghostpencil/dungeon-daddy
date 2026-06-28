"""Tests for DungeonVoiceAgent (Phase 51 Slice 6).

The dungeon-voice channel is pure narration — no mechanics, no proposals (D6).
The agent only assembles the §4.4 bundle and calls the injected provider; all
retrieval/filtering (reveal_knowledge, MemoryRetriever) happens in the caller.
Tested with a fake provider — never a live API call (spec/TESTING.md mock policy).
"""
from __future__ import annotations

import pytest


class _MockProvider:
    def __init__(self, response="The walls remember your name."):
        self._response = response
        self.last_system = ""
        self.last_messages = []
        self.last_max_tokens = None

    def complete(self, messages, system="", max_tokens=1024, response_format=None):
        self.last_system = system
        self.last_messages = messages
        self.last_max_tokens = max_tokens
        return self._response

    @property
    def model_id(self):
        return "mock"


def _make_memory(title="The Sealing", summary="The architects bound something below."):
    from dungeon_daddy.memory.models import MemoryEntry
    return MemoryEntry(
        memory_id="mem-1",
        campaign_id="camp-1",
        type="dungeon_state",
        title=title,
        summary=summary,
        status="approved",
        importance=5,
        markdown_path="",
        checksum="",
    )


def _respond(agent, **overrides):
    kwargs = dict(
        dungeon_voice="cold, industrial, analytical — speaks in diagnostics",
        intimacy_filled=4,
        intimacy_segments=6,
        dungeon_knowledge=["The core is dying.", "The warden is a copy."],
        player_message="What are you?",
        actor="kira",
        recent_memories=[_make_memory()],
    )
    kwargs.update(overrides)
    return agent.respond(**kwargs)


# ---------------------------------------------------------------------------
# Cycle 1: respond() returns the provider's reply text
# ---------------------------------------------------------------------------

def test_respond_returns_provider_response():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider(response="I am the weight above you.")
    agent = DungeonVoiceAgent(provider=provider)
    assert _respond(agent) == "I am the weight above you."


# ---------------------------------------------------------------------------
# Cycle 2: the dungeon_voice personality is carried into the prompt
# ---------------------------------------------------------------------------

def test_prompt_carries_dungeon_voice_personality():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(agent, dungeon_voice="warm but predatory — purrs in half-truths")
    assert "warm but predatory — purrs in half-truths" in provider.last_system


# ---------------------------------------------------------------------------
# Cycle 3: intimacy level (filled/segments) is carried into the prompt
# ---------------------------------------------------------------------------

def test_prompt_carries_intimacy_level():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(agent, intimacy_filled=4, intimacy_segments=6)
    assert "4/6" in provider.last_system


# ---------------------------------------------------------------------------
# Cycle 4: the dungeon_knowledge slice is carried into the prompt
# ---------------------------------------------------------------------------

def test_prompt_carries_dungeon_knowledge_slice():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(agent, dungeon_knowledge=["The core is dying.", "The warden is a copy."])
    assert "The core is dying." in provider.last_system
    assert "The warden is a copy." in provider.last_system


def test_prompt_omits_knowledge_section_when_slice_empty():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(agent, dungeon_knowledge=[])
    assert "Knowledge" not in provider.last_system


# ---------------------------------------------------------------------------
# Cycle 5: the player's message and acting actor reach the provider
# ---------------------------------------------------------------------------

def test_player_message_and_actor_sent_as_user_turn():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(agent, player_message="Why do you keep us here?", actor="talvas")

    user_text = " ".join(m.content for m in provider.last_messages if m.role == "user")
    assert "Why do you keep us here?" in user_text
    assert "talvas" in user_text


# ---------------------------------------------------------------------------
# Cycle 6: recent memories are summarized into the prompt
# ---------------------------------------------------------------------------

def test_prompt_carries_recent_memories():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    mem = _make_memory(title="The Sealing", summary="The architects bound something below.")
    _respond(agent, recent_memories=[mem])
    assert "The Sealing" in provider.last_system
    assert "The architects bound something below." in provider.last_system


def test_prompt_omits_memory_section_when_none():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(agent, recent_memories=[])
    assert "Recent Memories" not in provider.last_system


# ---------------------------------------------------------------------------
# Cycle 7: respond() propagates LLMError (does not swallow it)
# ---------------------------------------------------------------------------

def test_respond_propagates_llm_error():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent
    from dungeon_daddy.llm.provider import LLMError

    class _FailingProvider:
        def complete(self, messages, system="", max_tokens=1024, response_format=None):
            raise LLMError("connection refused")

        @property
        def model_id(self):
            return "boom"

    agent = DungeonVoiceAgent(provider=_FailingProvider())
    with pytest.raises(LLMError):
        _respond(agent)


# ---------------------------------------------------------------------------
# Phase 51.5 Slice 8 — agent context (§4.4)
# ---------------------------------------------------------------------------

# Cycle 8: # Who Is Speaking carries the actor's name, playbook and tags

def test_prompt_carries_who_is_speaking():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(
        agent,
        actor_name="Kira Vale",
        actor_playbook="Artificer",
        actor_tags=["machine-touched", "exiled"],
    )
    assert "# Who Is Speaking" in provider.last_system
    assert "Kira Vale" in provider.last_system
    assert "Artificer" in provider.last_system
    assert "machine-touched" in provider.last_system


def test_prompt_omits_who_is_speaking_when_no_name():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(agent)
    assert "# Who Is Speaking" not in provider.last_system


# Cycle 9: # Systems Status carries the (subsystem, state) pairs

def test_prompt_carries_systems_status():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(
        agent,
        systems_status=[("Coolant Loop", "damaged"), ("Forge Core", "online")],
    )
    assert "# Systems Status" in provider.last_system
    assert "Coolant Loop" in provider.last_system
    assert "damaged" in provider.last_system
    assert "Forge Core" in provider.last_system
    assert "online" in provider.last_system


def test_prompt_omits_systems_status_when_empty():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(agent)
    assert "# Systems Status" not in provider.last_system


# Cycle 10: # What You Want Next carries the active objective hint

def test_prompt_carries_what_you_want_next():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(
        agent,
        next_objective="Restore the coolant loop and I will grant the next authorization.",
    )
    assert "# What You Want Next" in provider.last_system
    assert "Restore the coolant loop" in provider.last_system


def test_prompt_omits_what_you_want_next_when_none():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(agent)
    assert "# What You Want Next" not in provider.last_system


# Cycle 11: in-session dialogue turns are carried so the dungeon has no amnesia

def test_prompt_carries_session_turns():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(
        agent,
        session_turns=[
            ("kira", "Who built you?"),
            ("dungeon", "Hands long since rusted."),
        ],
    )
    assert "Who built you?" in provider.last_system
    assert "Hands long since rusted." in provider.last_system


def test_prompt_omits_session_turns_section_when_empty():
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _MockProvider()
    agent = DungeonVoiceAgent(provider=provider)
    _respond(agent, session_turns=[])
    assert "# This Conversation" not in provider.last_system
