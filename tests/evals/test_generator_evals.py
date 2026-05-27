"""Eval tests for DungeonGeneratorAgent output quality."""
from __future__ import annotations

import pytest

from dungeon_daddy.data.models import Dungeon, DungeonMeta, validate_dungeon
from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent
from dungeon_daddy.llm.openai_provider import OpenAIProvider
from tests.evals.fixtures.dungeon_fixtures import TOMB_BRIEF, TOMB_LEVEL_BRIEF


@pytest.fixture(scope="module")
def generated_level(provider: OpenAIProvider):
    """Single API call shared across all generator evals in this module."""
    agent = DungeonGeneratorAgent(provider=provider)
    raw = agent.generate_level(
        brief=TOMB_BRIEF,
        level_brief=TOMB_LEVEL_BRIEF,
        dungeon_so_far=None,  # type: ignore[arg-type]
    )
    return agent.parse_level(raw)


@pytest.mark.eval
def test_generator_level_is_parseable(generated_level):
    """Generator must return JSON that parses to a valid Level model."""
    assert generated_level.id is not None
    assert isinstance(generated_level.name, str)
    assert len(generated_level.name) > 0


@pytest.mark.eval
def test_generator_level_passes_validation(generated_level):
    """Generated level must pass validate_dungeon without requiring auto-fix."""
    dungeon = Dungeon(
        meta=DungeonMeta(
            title=TOMB_BRIEF.title,
            theme=TOMB_BRIEF.theme,
            setting=TOMB_BRIEF.setting,
            party=TOMB_BRIEF.party,
            quest=TOMB_BRIEF.quest,
        ),
        levels=[generated_level],
    )
    result = validate_dungeon(dungeon)
    assert result.is_valid, f"Validation errors: {result.errors}"


@pytest.mark.eval
def test_generator_level_has_rooms(generated_level):
    """Generated level must contain at least two rooms."""
    assert len(generated_level.rooms) >= 2, (
        f"Expected at least 2 rooms, got {len(generated_level.rooms)}"
    )
