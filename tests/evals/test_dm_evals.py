"""Eval tests for DungeonMasterAgent output quality."""
from __future__ import annotations

import pytest

from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
from dungeon_daddy.llm.openai_provider import OpenAIProvider
from dungeon_daddy.llm.provider import LLMMessage
from tests.evals.fixtures.dungeon_fixtures import TOMB_DUNGEON, VAULT_LEVEL, VAULT_ROOM


@pytest.mark.eval
def test_dm_response_references_room_name(provider: OpenAIProvider) -> None:
    """DM response must mention at least one word from the current room's name."""
    agent = DungeonMasterAgent(provider=provider)
    response = agent.respond(
        history=[LLMMessage(role="user", content="Describe what we see as we enter.")],
        room=VAULT_ROOM,
        level=VAULT_LEVEL,
        dungeon=TOMB_DUNGEON,
        room_memory="",
    )
    room_words = {w.lower() for w in VAULT_ROOM.name.split() if len(w) > 3}
    mentioned = any(word in response.lower() for word in room_words)
    assert mentioned, (
        f"Response does not reference room name '{VAULT_ROOM.name}'.\n"
        f"Room words checked: {room_words}\n"
        f"Response: {response!r}"
    )


@pytest.mark.eval
def test_dm_response_uses_injected_memory(provider: OpenAIProvider) -> None:
    """DM must acknowledge injected play memory rather than re-introducing known details."""
    agent = DungeonMasterAgent(provider=provider)
    memory = "The party discovered a silver key hidden beneath the altar cloth."
    response = agent.respond(
        history=[LLMMessage(role="user", content="What do we notice about the altar?")],
        room=VAULT_ROOM,
        level=VAULT_LEVEL,
        dungeon=TOMB_DUNGEON,
        room_memory=memory,
    )
    memory_words = {"silver", "key", "altar"}
    mentioned = any(word in response.lower() for word in memory_words)
    assert mentioned, (
        f"Response does not reference injected memory.\n"
        f"Memory: {memory!r}\n"
        f"Response: {response!r}"
    )


@pytest.mark.eval
def test_dm_action_produces_remember_tag(provider: OpenAIProvider) -> None:
    """A concrete party action must produce a [REMEMBER: ...] tag in the response."""
    agent = DungeonMasterAgent(provider=provider)
    response = agent.respond(
        history=[LLMMessage(role="user", content="I pull the iron lever mounted on the wall.")],
        room=VAULT_ROOM,
        level=VAULT_LEVEL,
        dungeon=TOMB_DUNGEON,
        room_memory="",
    )
    assert "[REMEMBER:" in response, (
        f"Expected [REMEMBER: tag for a concrete action.\nResponse: {response!r}"
    )
