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
from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.action_options import (
    ActionCard,
    CardOptions,
    available_adverbs,
    available_nouns,
    available_verbs,
    validate_card,
)
from dungeon_daddy.rpg.action_resolution import resolve_card, resolve_card_roll
from dungeon_daddy.rpg.command import ActivateObject, MoveParty, PickUpItem
from dungeon_daddy.rpg.command_applier import apply_command
from dungeon_daddy.rpg.command_validator import validate_command
from dungeon_daddy.rpg.models import Item, ObjectTransition, RoomExit, RoomObject
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


def _room_context(repo: MemoryRepository) -> dict:
    """The real ``current_room`` block — proves the noun_id carries the full id."""
    return ContextBundleBuilder(
        campaign_id=CAMPAIGN_ID,
        scene_id=None,
        mode="run_scene",
        focus_actor_ids=[],
        token_budget=500,
        current_room_id=ROOM_A,
    ).build(repo).current_room


def test_pickup_card_flows_through_grammar_into_engine(repo: MemoryRepository) -> None:
    repo.save_actor(
        ACTOR["actor_id"], CAMPAIGN_ID, "pc", "mara", "Mara", "active", room_id=ROOM_A
    )
    repo.save_item(Item(
        item_id="item:c1:gold-coin",
        campaign_id=CAMPAIGN_ID,
        slug="gold-coin",
        display_name="Gold Coin",
        item_type="dungeon_item",
        description="A shiny coin.",
        room_id=ROOM_A,
        status="active",
    ))

    options = CardOptions(
        verbs=available_verbs([]),
        nouns=available_nouns(_room_context(repo), ACTOR),
        adverbs=available_adverbs("fighter", target_type="item", world_flags=set()),
    )

    # The noun the provider surfaced carries the full item_id, not the slug.
    card = ActionCard(verb="pick-up", noun_id="item:c1:gold-coin", adverb="cautiously")
    assert validate_card(card, options) is None

    cmd = resolve_card(card, actor_id=ACTOR["actor_id"])
    assert cmd == PickUpItem(item_id="item:c1:gold-coin", actor_id=ACTOR["actor_id"])

    vresult = validate_command(cmd, repo, CAMPAIGN_ID, party_room_id=ROOM_A)
    assert vresult.accepted is True
    apply_command(cmd, vresult, repo, CAMPAIGN_ID)

    picked = next(i for i in repo.get_items(CAMPAIGN_ID) if i["item_id"] == "item:c1:gold-coin")
    assert picked["owner_actor_id"] == ACTOR["actor_id"]
    assert picked["room_id"] is None


def test_activate_card_flows_through_grammar_into_engine(repo: MemoryRepository) -> None:
    repo.save_actor(
        ACTOR["actor_id"], CAMPAIGN_ID, "pc", "mara", "Mara", "active", room_id=ROOM_A
    )
    repo.save_room_object(RoomObject(
        object_id="obj:c1:iron-chest",
        campaign_id=CAMPAIGN_ID,
        room_id=ROOM_A,
        level_id="level:1",
        slug="iron-chest",
        display_name="Iron Chest",
        archetype="container",
        description="A heavy iron chest.",
        current_state="sealed",
        transitions=[
            ObjectTransition(
                transition_id="tr:c1:iron-chest:0",
                object_id="obj:c1:iron-chest",
                from_state="sealed",
                to_state="opened",
                trigger="open",
            )
        ],
    ))

    options = CardOptions(
        verbs=available_verbs([]),
        nouns=available_nouns(_room_context(repo), ACTOR),
        adverbs=available_adverbs("fighter", target_type="object", world_flags=set()),
    )

    # The noun the provider surfaced carries the full object_id, not the slug.
    card = ActionCard(verb="activate", noun_id="obj:c1:iron-chest", adverb="cautiously")
    assert validate_card(card, options) is None

    cmd = resolve_card(card, actor_id=ACTOR["actor_id"], trigger="open")
    assert cmd == ActivateObject(
        object_id="obj:c1:iron-chest", actor_id=ACTOR["actor_id"], trigger="open"
    )

    vresult = validate_command(cmd, repo, CAMPAIGN_ID, party_room_id=ROOM_A)
    assert vresult.accepted is True
    apply_command(cmd, vresult, repo, CAMPAIGN_ID)

    obj = repo.get_room_object("obj:c1:iron-chest")
    assert obj["current_state"] == "opened"


def test_fight_card_flows_through_grammar_into_action_roll(repo: MemoryRepository) -> None:
    """A non-mutation Card drives the real providers, then resolves as an action roll."""
    repo.save_actor(
        ACTOR["actor_id"], CAMPAIGN_ID, "pc", "mara", "Mara", "active", room_id=ROOM_A
    )
    repo.save_actor_action_rating(ACTOR["actor_id"], "fight", 2)
    repo.save_actor(
        "actor:c1:ghoul", CAMPAIGN_ID, "monster", "ghoul", "Ghoul", "active", room_id=ROOM_A
    )

    options = CardOptions(
        verbs=available_verbs([]),
        nouns=available_nouns(_room_context(repo), ACTOR),
        adverbs=available_adverbs("fighter", target_type="monster", world_flags=set()),
    )

    card = ActionCard(verb="fight", noun_id="actor:c1:ghoul", adverb="boldly")
    assert validate_card(card, options) is None
    # The roll path: a non-mutation verb produces no PlayerCommand.
    assert resolve_card(card, actor_id=ACTOR["actor_id"]) is None

    actor = {
        "actor_id": ACTOR["actor_id"],
        "actions": {
            r["action_key"]: r["rating"]
            for r in repo.get_actor_action_ratings(ACTOR["actor_id"])
        },
    }
    roll = resolve_card_roll(
        card, campaign_id=CAMPAIGN_ID, actor=actor, fixed=[6, 2]
    )

    # rating 2 -> 2 dice; "boldly" carries only world-side-effect flags.
    assert roll.resolution.dice_rolled == [6, 2]
    assert roll.resolution.outcome == "full"
    assert roll.resolution.actor_id == ACTOR["actor_id"]
    assert roll.side_effect_flags == {"occupants_aware", "advance_npc_reaction"}
