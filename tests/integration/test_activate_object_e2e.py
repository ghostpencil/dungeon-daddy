from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.command import ActivateObject, PickUpItem
from dungeon_daddy.rpg.command_applier import apply_command
from dungeon_daddy.rpg.command_validator import validate_command
from dungeon_daddy.rpg.models import Item, ObjectTransition, RoomObject

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent / "dungeon_daddy" / "data" / "migrations"
)

CAMPAIGN = "campaign:test"
ACTOR_ID = "actor:test:fighter"
OBJECT_ID = "obj:test:chest"
ROOM_ID = "room:test:vault"
LEVEL_ID = "level:test:dungeon"
KEY_ID = "item:test:brass-key"
COIN_ID = "item:test:ancient-coin"
CLOCK_ID = "clock:test:treasure"


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(db_path=tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


def _chest(requires_key: bool = True) -> RoomObject:
    return RoomObject(
        object_id=OBJECT_ID,
        campaign_id=CAMPAIGN,
        room_id=ROOM_ID,
        level_id=LEVEL_ID,
        slug="chest",
        display_name="Iron Chest",
        archetype="container",
        description="A heavy iron chest.",
        current_state="locked",
        transitions=[
            ObjectTransition(
                transition_id="tr:test:open-chest",
                object_id=OBJECT_ID,
                from_state="locked",
                to_state="opened",
                trigger="open",
                requires_item_slug="brass-key" if requires_key else None,
                spawns_item_slug="ancient-coin",
                advances_clock_slug="treasure",
            )
        ],
    )


def _key(owner: str | None = ACTOR_ID) -> Item:
    return Item(
        item_id=KEY_ID,
        campaign_id=CAMPAIGN,
        slug="brass-key",
        display_name="Brass Key",
        item_type="dungeon_item",
        description="An ornate brass key.",
        owner_actor_id=owner,
        status="active",
    )


def _coin() -> Item:
    return Item(
        item_id=COIN_ID,
        campaign_id=CAMPAIGN,
        slug="ancient-coin",
        display_name="Ancient Coin",
        item_type="dungeon_item",
        description="A worn ancient coin.",
        status="inert",
        owner_actor_id=None,
        room_id=None,
    )


def _seed_base(repo: MemoryRepository, *, with_key: bool = True) -> None:
    repo.save_actor(ACTOR_ID, CAMPAIGN, "pc", "fighter", "Fighter")
    if with_key:
        repo.save_item(_key())
    repo.save_room_object(_chest(requires_key=True))
    repo.save_item(_coin())
    repo.save_clock(CLOCK_ID, CAMPAIGN, "Treasure Clock", segments=4, filled=1)


def test_full_pipeline_success(repo: MemoryRepository) -> None:
    _seed_base(repo, with_key=True)
    cmd = ActivateObject(object_id=OBJECT_ID, actor_id=ACTOR_ID, trigger="open")

    validation = validate_command(cmd, repo, CAMPAIGN)
    assert validation.accepted, validation.rejection_reason

    result = apply_command(cmd, validation, repo, CAMPAIGN)

    event_types = {e.event_type for e in result.events}
    assert "object.transitioned" in event_types
    assert "item.spawned" in event_types
    assert "clock.advanced" in event_types

    obj = repo.get_room_object(OBJECT_ID)
    assert obj["current_state"] == "opened"

    loose = repo.get_items_by_room(CAMPAIGN, ROOM_ID)
    assert any(i["slug"] == "ancient-coin" and i["status"] == "active" for i in loose)

    clocks = repo.get_clocks(CAMPAIGN)
    assert clocks[0]["filled"] == 2


def test_rejected_command_is_noop(repo: MemoryRepository) -> None:
    _seed_base(repo, with_key=False)  # actor has no key
    cmd = ActivateObject(object_id=OBJECT_ID, actor_id=ACTOR_ID, trigger="open")

    validation = validate_command(cmd, repo, CAMPAIGN)
    assert not validation.accepted
    assert "brass-key" in (validation.rejection_reason or "")

    result = apply_command(cmd, validation, repo, CAMPAIGN)
    assert result.events == []

    obj = repo.get_room_object(OBJECT_ID)
    assert obj["current_state"] == "locked"

    loose = repo.get_items_by_room(CAMPAIGN, ROOM_ID)
    assert loose == []

    clocks = repo.get_clocks(CAMPAIGN)
    assert clocks[0]["filled"] == 1


def test_chained_activate_then_pickup(repo: MemoryRepository) -> None:
    _seed_base(repo, with_key=True)
    activate_cmd = ActivateObject(object_id=OBJECT_ID, actor_id=ACTOR_ID, trigger="open")

    v1 = validate_command(activate_cmd, repo, CAMPAIGN)
    assert v1.accepted
    apply_command(activate_cmd, v1, repo, CAMPAIGN)

    # ancient-coin is now active and loose in the vault
    pickup_cmd = PickUpItem(item_id=COIN_ID, actor_id=ACTOR_ID)
    v2 = validate_command(pickup_cmd, repo, CAMPAIGN)
    assert v2.accepted, v2.rejection_reason

    result = apply_command(pickup_cmd, v2, repo, CAMPAIGN)
    assert any(e.event_type == "item.picked_up" for e in result.events)

    items_by_actor = repo.get_items_by_actor(ACTOR_ID)
    coin = next((i for i in items_by_actor if i["item_id"] == COIN_ID), None)
    assert coin is not None
    assert coin["owner_actor_id"] == ACTOR_ID
    assert coin["room_id"] is None
