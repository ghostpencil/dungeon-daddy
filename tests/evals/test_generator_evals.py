"""Eval tests for DungeonGeneratorAgent output quality."""
from __future__ import annotations

import pytest

from dungeon_daddy.data.models import Dungeon, DungeonMeta, validate_dungeon
from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent
from dungeon_daddy.llm.telemetry import ObservingProvider
from tests.evals.fixtures.dungeon_fixtures import TOMB_BRIEF, TOMB_LEVEL_BRIEF

# design_view regenerates while ``_generation_retries < 3`` — i.e. the first
# attempt plus up to three error-fed retries. Mirror that budget here.
_MAX_RETRIES = 3


@pytest.fixture(scope="module")
def agent(provider: ObservingProvider) -> DungeonGeneratorAgent:
    return DungeonGeneratorAgent(provider=provider)


@pytest.fixture(scope="module")
def first_raw(agent: DungeonGeneratorAgent) -> str:
    """Single initial API call shared across all generator evals in this module."""
    return agent.generate_level(
        brief=TOMB_BRIEF,
        level_brief=TOMB_LEVEL_BRIEF,
        dungeon_so_far=None,  # type: ignore[arg-type]
    )


@pytest.fixture(scope="module")
def generated_level(agent: DungeonGeneratorAgent, first_raw: str):
    """The one-shot parsed Level from the shared initial call."""
    return agent.parse_level(first_raw)


def _tomb_meta() -> DungeonMeta:
    return DungeonMeta(
        title=TOMB_BRIEF.title,
        theme=TOMB_BRIEF.theme,
        setting=TOMB_BRIEF.setting,
        party=TOMB_BRIEF.party,
        quest=TOMB_BRIEF.quest,
    )


@pytest.mark.eval
def test_generator_level_is_parseable(generated_level):
    """Generator must return JSON that parses to a valid Level model."""
    assert generated_level.id is not None
    assert isinstance(generated_level.name, str)
    assert len(generated_level.name) > 0


@pytest.mark.eval
def test_generator_level_passes_validation(agent: DungeonGeneratorAgent, first_raw: str):
    """Generator must produce a valid level within production's retry budget.

    Production never relies on one-shot validity — ``design_view`` runs a
    validate→regenerate-with-errors loop (up to ``_MAX_RETRIES`` retries, feeding
    the validation/parse errors back to the model). This eval mirrors that loop,
    so a failure means the generator could not self-correct in the same budget
    production gives it — a real regression, not a single-sample coin flip.
    """
    meta = _tomb_meta()
    raw = first_raw
    errors: list[str] | None = None
    result = None
    for attempt in range(_MAX_RETRIES + 1):  # initial attempt + retries
        try:
            level = agent.parse_level(raw)
        except Exception as exc:  # parse failure also triggers a production retry
            errors = [str(exc)]
            result = None
        else:
            result = validate_dungeon(Dungeon(meta=meta, levels=[level]))
            if result.is_valid:
                break
            errors = result.errors
        if attempt < _MAX_RETRIES:
            raw = agent.generate_level(
                brief=TOMB_BRIEF,
                level_brief=TOMB_LEVEL_BRIEF,
                dungeon_so_far=None,  # type: ignore[arg-type]
                validation_errors=errors,
            )
    assert result is not None and result.is_valid, (
        f"Generator could not produce a valid level within {_MAX_RETRIES} retries. "
        f"Last errors: {errors}"
    )


@pytest.mark.eval
def test_generator_level_has_rooms(generated_level):
    """Generated level must contain at least two rooms."""
    assert len(generated_level.rooms) >= 2, (
        f"Expected at least 2 rooms, got {len(generated_level.rooms)}"
    )
