"""Integration tests — real LLM calls, one per agent. Skipped without OPENAI_API_KEY."""
from __future__ import annotations

import os

import pytest

from dungeon_daddy.data.models import (
    Dungeon,
    DungeonMeta,
    Level,
    LoopPatternCatalog,
    Room,
)
from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent
from dungeon_daddy.llm.agents.wizard_agent import DungeonBrief, DungeonWizardAgent, LevelBrief
from dungeon_daddy.llm.openai_provider import OpenAIProvider
from dungeon_daddy.llm.provider import LLMMessage

_NEEDS_KEY = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)


def _provider() -> OpenAIProvider:
    return OpenAIProvider()


def _minimal_room() -> Room:
    return Room(id="r1", num=1, name="Entry Hall", x=0, y=0, w=3, h=3, type="hall", note="Dusty.")


def _minimal_level() -> Level:
    return Level(
        id=1, name="The Depths", summary="", ecology="Goblins",
        loop="lock_key", loops=[], width=10, height=10,
        entries=[], rooms=[_minimal_room()], connections=[],
    )


def _minimal_dungeon() -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="Test Keep", theme="dark", setting="cave", party="4 adventurers", quest="Find the relic"),
        levels=[_minimal_level()],
    )


@pytest.mark.live_api
@_NEEDS_KEY
def test_dm_agent_responds():
    agent = DungeonMasterAgent(provider=_provider())
    result = agent.respond(
        history=[],
        room=_minimal_room(),
        level=_minimal_level(),
        dungeon=_minimal_dungeon(),
        room_memory="",
    )
    assert isinstance(result, str)
    assert len(result) > 0
    assert not result.startswith("⚠")
    assert any(len(w) > 2 for w in result.split())


@pytest.mark.live_api
@_NEEDS_KEY
def test_wizard_agent_responds():
    catalog = LoopPatternCatalog.load_bundled()
    agent = DungeonWizardAgent(provider=_provider(), loop_patterns=catalog.patterns)
    history = [LLMMessage(role="user", content="Hello, let's design a dungeon.")]
    result = agent.chat(history, phase=1)
    assert isinstance(result, str)
    assert len(result) > 0
    assert not result.startswith("⚠")
    assert any(len(w) > 2 for w in result.split())


@pytest.mark.live_api
@_NEEDS_KEY
def test_generator_agent_responds():
    agent = DungeonGeneratorAgent(provider=_provider())
    brief = DungeonBrief(
        title="Test Keep", theme="dark fantasy", setting="ancient cave",
        party="4 adventurers", quest="Recover the lost relic", num_levels=1,
    )
    level_brief = LevelBrief(
        level_number=1, ecology="Goblins", main_loop_pattern="lock_key",
        sub_loop_pattern=None, gm_notes="A central vault with traps.",
    )
    result = agent.generate_level(
        brief=brief,
        level_brief=level_brief,
        dungeon_so_far=None,
    )
    assert isinstance(result, str)
    assert len(result) > 0
    assert not result.startswith("⚠")
    assert any(len(w) > 2 for w in result.split())
