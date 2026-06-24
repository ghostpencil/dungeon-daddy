from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.command import ActivateObject, CombineItems, PickUpItem
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


HERB_ID = "item:test:dried-herb"
VIAL_ID = "item:test:empty-vial"
POTION_ID = "item:test:healing-potion"
COMBINE_ACTOR_ID = "actor:test:alchemist"


def _herb(owner: str | None = COMBINE_ACTOR_ID, combines_with: str | None = "empty-vial", result: str | None = "healing-potion") -> Item:
    return Item(
        item_id=HERB_ID,
        campaign_id=CAMPAIGN,
        slug="dried-herb",
        display_name="Dried Herb",
        item_type="dungeon_item",
        description="A bundle of dried herbs.",
        owner_actor_id=owner,
        status="active",
        combines_with_slug=combines_with,
        combination_result_slug=result,
    )


def _vial(owner: str | None = COMBINE_ACTOR_ID) -> Item:
    return Item(
        item_id=VIAL_ID,
        campaign_id=CAMPAIGN,
        slug="empty-vial",
        display_name="Empty Vial",
        item_type="dungeon_item",
        description="An empty glass vial.",
        owner_actor_id=owner,
        status="active",
    )


def _potion_inert() -> Item:
    return Item(
        item_id=POTION_ID,
        campaign_id=CAMPAIGN,
        slug="healing-potion",
        display_name="Healing Potion",
        item_type="dungeon_item",
        description="A glowing healing potion.",
        owner_actor_id=None,
        room_id=None,
        status="inert",
    )


def test_combine_items_success(repo: MemoryRepository) -> None:
    repo.save_actor(COMBINE_ACTOR_ID, CAMPAIGN, "pc", "alchemist", "Alchemist")
    repo.save_item(_herb())
    repo.save_item(_vial())
    repo.save_item(_potion_inert())

    cmd = CombineItems(item_a_id=HERB_ID, item_b_id=VIAL_ID, actor_id=COMBINE_ACTOR_ID)
    validation = validate_command(cmd, repo, CAMPAIGN)
    assert validation.accepted, validation.rejection_reason

    result = apply_command(cmd, validation, repo, CAMPAIGN)

    event_types = {e.event_type for e in result.events}
    assert "items.combined" in event_types
    assert "item.spawned" in event_types

    herb = next(i for i in repo.get_items(CAMPAIGN) if i["item_id"] == HERB_ID)
    vial = next(i for i in repo.get_items(CAMPAIGN) if i["item_id"] == VIAL_ID)
    assert herb["status"] == "consumed"
    assert vial["status"] == "consumed"

    potion = next(i for i in repo.get_items(CAMPAIGN) if i["item_id"] == POTION_ID)
    assert potion["status"] == "active"
    assert potion["owner_actor_id"] == COMBINE_ACTOR_ID


def test_combine_items_rejected_when_item_not_held(repo: MemoryRepository) -> None:
    repo.save_actor(COMBINE_ACTOR_ID, CAMPAIGN, "pc", "alchemist", "Alchemist")
    repo.save_item(_herb(owner=None))  # not held
    repo.save_item(_vial())

    cmd = CombineItems(item_a_id=HERB_ID, item_b_id=VIAL_ID, actor_id=COMBINE_ACTOR_ID)
    validation = validate_command(cmd, repo, CAMPAIGN)
    assert not validation.accepted

    result = apply_command(cmd, validation, repo, CAMPAIGN)
    assert result.events == []

    herb = next(i for i in repo.get_items(CAMPAIGN) if i["item_id"] == HERB_ID)
    assert herb["status"] == "active"


DRAUGHT_ID = "item:test:healing-draught"
USE_ACTOR_ID = "actor:test:hero"


def test_use_card_on_self_resolves_and_consumes_item_end_to_end(
    repo: MemoryRepository,
) -> None:
    """resolve_card(use, noun=item, target=actor) → ConsumeItem → validate → apply → consumed."""
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.action_resolution import resolve_card

    repo.save_actor(USE_ACTOR_ID, CAMPAIGN, "pc", "fighter", "Hero")
    draught = Item(
        item_id=DRAUGHT_ID,
        campaign_id=CAMPAIGN,
        slug="healing-draught",
        display_name="Healing Draught",
        item_type="dungeon_item",
        description="A small vial of healing liquid.",
        owner_actor_id=USE_ACTOR_ID,
        status="active",
    )
    repo.save_item(draught)

    card = ActionCard(
        verb="use", noun_id=DRAUGHT_ID, adverb="cautiously", target_id=USE_ACTOR_ID
    )
    cmd = resolve_card(card, actor_id=USE_ACTOR_ID)
    assert cmd is not None

    validation = validate_command(cmd, repo, CAMPAIGN)
    assert validation.accepted, validation.rejection_reason

    result = apply_command(cmd, validation, repo, CAMPAIGN)
    assert any(e.event_type == "item.consumed" for e in result.events)

    items = repo.get_items(CAMPAIGN)
    draught_row = next(i for i in items if i["item_id"] == DRAUGHT_ID)
    assert draught_row["status"] == "consumed"


def test_contested_transition_round_trips(repo: MemoryRepository) -> None:
    obj = RoomObject(
        object_id="obj:test:lever",
        campaign_id=CAMPAIGN,
        room_id=ROOM_ID,
        level_id=LEVEL_ID,
        slug="lever",
        display_name="Rusted Lever",
        archetype="mechanism",
        description="A lever that could trigger something deadly.",
        current_state="idle",
        transitions=[
            ObjectTransition(
                transition_id="tr:test:lever:pull",
                object_id="obj:test:lever",
                from_state="idle",
                to_state="triggered",
                trigger="pull",
                contested=True,
                action_verb="scrap",
            )
        ],
    )
    repo.save_room_object(obj)

    raw = repo.get_room_object("obj:test:lever")
    assert raw is not None
    reloaded = RoomObject.model_validate(raw)
    assert len(reloaded.transitions) == 1
    t = reloaded.transitions[0]
    assert t.contested is True
    assert t.action_verb == "scrap"
