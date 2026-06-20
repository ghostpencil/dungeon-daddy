"""Phase 50 Slice 5 — end-to-end: an ActionCard becomes a PlayerCommand the engine applies.

Exercises the full Verb·Noun·Adverb grammar against real code: the Slice 1–3
providers build the offered sets, ``validate_card`` accepts an in-bounds Card,
``resolve_card`` maps it to a ``MoveParty`` carrying the adverb as ``how``, and
``apply_move_party`` actually moves the party. Proves the resolved command is one
the engine accepts and applies — not just a shape match.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.action_options import (
    ActionCard,
    CardOptions,
    available_adverbs,
    available_nouns,
    available_verbs,
    validate_card,
)
from dungeon_daddy.rpg.action_resolution import resolve_card
from dungeon_daddy.rpg.command import MoveParty
from dungeon_daddy.rpg.models import RoomExit
from dungeon_daddy.rpg.move_party import apply_move_party

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent / "dungeon_daddy" / "data" / "migrations"
)

CAMPAIGN_ID = "campaign:test"
ROOM_A = "room:a"
ROOM_B = "room:b"
EXIT_ID = "exit:c1:north"
ACTOR = {"actor_id": "actor:c1:mara", "display_name": "Mara"}


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


def test_move_card_flows_through_grammar_into_engine(repo: MemoryRepository) -> None:
    repo.save_room_exit(
        RoomExit(
            exit_id=EXIT_ID,
            campaign_id=CAMPAIGN_ID,
            from_room_id=ROOM_A,
            to_room_id=ROOM_B,
            level_id="level:1",
            label="North Door",
            status="open",
        )
    )
    session = SessionState(dungeon_id="dungeon:test", current_room_id=ROOM_A)

    # The room context the providers read (mirrors _fetch_current_room's exit shape).
    room_context = {
        "room_id": ROOM_A,
        "exits": [{"exit_id": EXIT_ID, "label": "North Door"}],
    }
    options = CardOptions(
        verbs=available_verbs([]),
        nouns=available_nouns(room_context, ACTOR),
        adverbs=available_adverbs("fighter", target_type="room", world_flags=set()),
    )

    card = ActionCard(verb="move", noun_id=EXIT_ID, adverb="cautiously")
    assert validate_card(card, options) is None

    cmd = resolve_card(card, actor_id=ACTOR["actor_id"])
    assert cmd == MoveParty(exit_id=EXIT_ID, how="cautiously")

    new_session, result = apply_move_party(cmd, repo, CAMPAIGN_ID, session)

    assert result.accepted is True
    assert new_session.current_room_id == ROOM_B
    assert result.modifier_flags == {"suppress_entry_ticks", "trap_chance:-1"}
