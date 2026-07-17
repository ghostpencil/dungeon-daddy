"""Eval tests for the `lookup_world` narrator tool (Phase 51.8 Slice B5, spec §12).

Two behaviors, live: an *out-of-scene* lore question triggers a lookup and lands
the fact in the narration; an *in-room* question does not look anything up.

This is the only test that drives `lookup_world` through a real tool-calling
provider — every other test in the suite fake-drives `complete_round`, so B2's
`OpenAIProvider` translation (`LLMToolDef` → OpenAI function format, and
`message.tool_calls` back to `LLMToolCall`) is otherwise unexercised.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
from dungeon_daddy.llm.lookup_tool import LookupRecord, build_lookup_executor
from dungeon_daddy.llm.openai_provider import OpenAIProvider
from dungeon_daddy.llm.provider import LLMMessage, LLMToolCall
from dungeon_daddy.memory.lookup import LookupService
from dungeon_daddy.memory.repository import MemoryRepository
from tests.evals.fixtures.dungeon_fixtures import TOMB_DUNGEON, VAULT_LEVEL, VAULT_ROOM

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[2] / "dungeon_daddy" / "data" / "migrations"
)

CAMPAIGN_ID = "campaign:eval-tomb"

# (executor, records) — the tool the agent calls, and the L6 provenance it records.
_Lookup = tuple[Callable[[LLMToolCall], str], list[LookupRecord]]

# Out-of-scene lore: nothing in VAULT_ROOM / VAULT_LEVEL / TOMB_DUNGEON mentions
# Karn Vale, so the narrator can only learn it by calling `lookup_world`. The
# bellwright's name is the probe — it appears in no prompt the model receives,
# so a response containing it must have come through the tool result.
LORE_TITLE = "The Sunken Bell of Karn Vale"
LORE_SUMMARY = (
    "The great bell of Karn Vale was cast by the bellwright Vessa Orn from "
    "shards left over from the King's crown. It tolls of its own accord "
    "whenever the Forgotten King stirs in his tomb."
)
LORE_PROBE = "vessa"


@pytest.fixture
def lookup(tmp_path: Path) -> Iterator[_Lookup]:
    """A live `lookup_world` executor over a campaign holding one lore memory."""
    repo = MemoryRepository(db_path=tmp_path / "eval.duckdb")
    repo.initialize_schema(MIGRATIONS_DIR)
    repo.save_memory_entry(
        "mem-bell",
        CAMPAIGN_ID,
        "lore",
        LORE_TITLE,
        LORE_SUMMARY,
        status="approved",  # search_entities' memory branch is approved-only
        importance=6,
    )
    for tag in ("theme:history", "thread:obsidian-crown"):
        repo.add_memory_tag("mem-bell", tag)

    records: list[LookupRecord] = []
    # No context bundle in this eval, so nothing overlaps → no L7 redirect.
    executor = build_lookup_executor(
        LookupService(repo, CAMPAIGN_ID), set(), on_lookup=records.append
    )
    yield executor, records
    repo.close()


@pytest.mark.eval
def test_out_of_scene_question_triggers_lookup_and_lands_the_fact(
    provider: OpenAIProvider,
    lookup: _Lookup,
) -> None:
    executor, records = lookup
    agent = DungeonMasterAgent(provider=provider)
    response = agent.respond(
        history=[
            LLMMessage(
                role="user",
                content=(
                    "One of us recalls a rumor about the Sunken Bell of Karn Vale. "
                    "What do the records of this place say about it?"
                ),
            )
        ],
        room=VAULT_ROOM,
        level=VAULT_LEVEL,
        dungeon=TOMB_DUNGEON,
        room_memory="",
        lookup=executor,
    )
    assert records, (
        "Out-of-scene question did not trigger a lookup_world call.\n"
        f"Response: {response!r}"
    )
    assert any(r.hit_count for r in records), (
        f"lookup_world was called but found nothing: {records}"
    )
    assert LORE_PROBE in response.lower(), (
        f"Looked-up fact did not land in the narration (probe {LORE_PROBE!r}).\n"
        f"Lookups: {records}\n"
        f"Response: {response!r}"
    )


@pytest.mark.eval
def test_in_room_question_does_not_trigger_a_lookup(
    provider: OpenAIProvider,
    lookup: _Lookup,
) -> None:
    executor, records = lookup
    agent = DungeonMasterAgent(provider=provider)
    response = agent.respond(
        history=[
            LLMMessage(
                role="user",
                content="We look around the chamber. What does the dust in here tell us?",
            )
        ],
        room=VAULT_ROOM,  # its note already covers the dust — answerable in-scene
        level=VAULT_LEVEL,
        dungeon=TOMB_DUNGEON,
        room_memory="",
        lookup=executor,
    )
    assert records == [], (
        "In-room question should be answered from context, not looked up.\n"
        f"Lookups: {records}\n"
        f"Response: {response!r}"
    )
    assert response.strip(), "Expected narration for an in-room question."
