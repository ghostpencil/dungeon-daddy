from __future__ import annotations

from dungeon_daddy.rpg.command import (
    ActivateObject,
    ConsumeItem,
    ConsumeKitCharge,
    DropItem,
    EquipItem,
    GiveItem,
    PickUpItem,
    TakeItem,
    UnequipItem,
)
from dungeon_daddy.rpg.command_applier import apply_command
from dungeon_daddy.rpg.command_validator import CommandValidationResult
from dungeon_daddy.rpg.models import Item, ObjectTransition, RoomObject

CAMPAIGN = "campaign:test"
KIT_ID = "item:test:lockpick-kit"
ITEM_ID = "item:test:potion"
GEAR_ID = "item:test:sword"
ACTOR_A = "actor:test:fighter"
ACTOR_B = "actor:test:rogue"


def _kit(charges_current: int = 2) -> Item:
    return Item(
        item_id=KIT_ID,
        campaign_id=CAMPAIGN,
        slug="lockpick-kit",
        display_name="Lockpick Kit",
        item_type="class_kit",
        description="A set of lockpicks.",
        charges_max=3,
        charges_current=charges_current,
    )


def _command() -> ConsumeKitCharge:
    return ConsumeKitCharge(item_id=KIT_ID, reason="pick the lock")


def _dungeon_item(item_id: str = ITEM_ID, owner: str = ACTOR_A) -> Item:
    return Item(
        item_id=item_id,
        campaign_id=CAMPAIGN,
        slug=item_id.split(":")[-1],
        display_name="Healing Potion",
        item_type="dungeon_item",
        description="Restores vitality.",
        owner_actor_id=owner,
    )


class TestConsumeKitChargeApplier:
    def test_decrements_charges_and_emits_event(self, repo) -> None:
        repo.save_item(_kit(charges_current=2))
        accepted = CommandValidationResult(accepted=True)
        result = apply_command(_command(), accepted, repo, CAMPAIGN)
        assert len(result.events) == 1
        assert result.events[0].event_type == "kit.charge_consumed"
        item = repo.get_items(CAMPAIGN)[0]
        assert item["charges_current"] == 1

    def test_noop_when_rejected(self, repo) -> None:
        repo.save_item(_kit(charges_current=2))
        rejected = CommandValidationResult(accepted=False, rejection_reason="No charges remaining")
        result = apply_command(_command(), rejected, repo, CAMPAIGN)
        assert result.events == []
        item = repo.get_items(CAMPAIGN)[0]
        assert item["charges_current"] == 2


class TestConsumeItemApplier:
    def test_marks_consumed_and_emits_event(self, repo) -> None:
        repo.save_item(_dungeon_item())
        accepted = CommandValidationResult(accepted=True)
        cmd = ConsumeItem(item_id=ITEM_ID, reason="drink potion")
        result = apply_command(cmd, accepted, repo, CAMPAIGN)
        assert len(result.events) == 1
        assert result.events[0].event_type == "item.consumed"
        item = repo.get_items(CAMPAIGN)[0]
        assert item["status"] == "consumed"

    def test_noop_when_rejected(self, repo) -> None:
        repo.save_item(_dungeon_item())
        rejected = CommandValidationResult(accepted=False, rejection_reason="not active")
        cmd = ConsumeItem(item_id=ITEM_ID, reason="drink")
        result = apply_command(cmd, rejected, repo, CAMPAIGN)
        assert result.events == []
        item = repo.get_items(CAMPAIGN)[0]
        assert item["status"] == "active"


class TestGiveItemApplier:
    def test_transfers_owner_and_emits_event(self, repo) -> None:
        repo.save_item(_dungeon_item(owner=ACTOR_A))
        accepted = CommandValidationResult(accepted=True)
        cmd = GiveItem(item_id=ITEM_ID, to_actor_id=ACTOR_B)
        result = apply_command(cmd, accepted, repo, CAMPAIGN)
        assert len(result.events) == 1
        assert result.events[0].event_type == "item.transferred"
        item = repo.get_items_by_actor(ACTOR_B)[0]
        assert item["owner_actor_id"] == ACTOR_B

    def test_noop_when_rejected(self, repo) -> None:
        repo.save_item(_dungeon_item(owner=ACTOR_A))
        rejected = CommandValidationResult(accepted=False, rejection_reason="Unknown target")
        cmd = GiveItem(item_id=ITEM_ID, to_actor_id=ACTOR_B)
        result = apply_command(cmd, rejected, repo, CAMPAIGN)
        assert result.events == []
        item = repo.get_items_by_actor(ACTOR_A)[0]
        assert item["owner_actor_id"] == ACTOR_A


class TestTakeItemApplier:
    def test_marks_lost_and_emits_event(self, repo) -> None:
        repo.save_item(_dungeon_item())
        accepted = CommandValidationResult(accepted=True)
        cmd = TakeItem(item_id=ITEM_ID)
        result = apply_command(cmd, accepted, repo, CAMPAIGN)
        assert len(result.events) == 1
        assert result.events[0].event_type == "item.removed"
        item = repo.get_items(CAMPAIGN)[0]
        assert item["status"] == "lost"

    def test_noop_when_rejected(self, repo) -> None:
        repo.save_item(_dungeon_item())
        rejected = CommandValidationResult(accepted=False, rejection_reason="no owner")
        cmd = TakeItem(item_id=ITEM_ID)
        result = apply_command(cmd, rejected, repo, CAMPAIGN)
        assert result.events == []
        item = repo.get_items(CAMPAIGN)[0]
        assert item["status"] == "active"


def _gear(owner: str = ACTOR_A) -> Item:
    from dungeon_daddy.rpg.models import Item
    return Item(
        item_id=GEAR_ID,
        campaign_id=CAMPAIGN,
        slug="sword",
        display_name="Iron Sword",
        item_type="equipped_gear",
        description="A sturdy iron sword.",
        owner_actor_id=owner,
    )


class TestEquipItemApplier:
    def test_sets_equipped_and_emits_event(self, repo) -> None:
        repo.save_item(_gear())
        accepted = CommandValidationResult(accepted=True)
        result = apply_command(EquipItem(item_id=GEAR_ID), accepted, repo, CAMPAIGN)
        assert len(result.events) == 1
        assert result.events[0].event_type == "item.equipped"
        item = repo.get_items(CAMPAIGN)[0]
        assert item["is_equipped"] is True

    def test_noop_when_rejected(self, repo) -> None:
        repo.save_item(_gear())
        rejected = CommandValidationResult(accepted=False, rejection_reason="not active")
        result = apply_command(EquipItem(item_id=GEAR_ID), rejected, repo, CAMPAIGN)
        assert result.events == []
        item = repo.get_items(CAMPAIGN)[0]
        assert item["is_equipped"] is False


OBJ_ID = "obj:test:chest"
ROOM_ID = "room:test:vault"
LEVEL_ID = "level:test:dungeon"


def _room_object(
    spawns_item_slug: str | None = None,
    advances_clock_slug: str | None = None,
) -> RoomObject:
    transition = ObjectTransition(
        transition_id="tr:test:open",
        object_id=OBJ_ID,
        from_state="sealed",
        to_state="opened",
        trigger="open",
        spawns_item_slug=spawns_item_slug,
        advances_clock_slug=advances_clock_slug,
    )
    return RoomObject(
        object_id=OBJ_ID,
        campaign_id=CAMPAIGN,
        room_id=ROOM_ID,
        level_id=LEVEL_ID,
        slug="chest",
        display_name="Iron Chest",
        archetype="container",
        description="A heavy iron chest.",
        current_state="sealed",
        transitions=[transition],
    )


def _inert_item(slug: str = "gem", room_id: str | None = None) -> Item:
    return Item(
        item_id=f"item:test:{slug}",
        campaign_id=CAMPAIGN,
        slug=slug,
        display_name=slug.title(),
        item_type="dungeon_item",
        description="A found item.",
        status="inert",
        room_id=room_id,
    )


class TestActivateObjectApplier:
    def test_transitions_state_and_emits_event(self, repo) -> None:
        repo.save_room_object(_room_object())
        accepted = CommandValidationResult(accepted=True)
        cmd = ActivateObject(object_id=OBJ_ID, actor_id=ACTOR_A, trigger="open")
        result = apply_command(cmd, accepted, repo, CAMPAIGN)
        assert any(e.event_type == "object.transitioned" for e in result.events)
        obj = repo.get_room_object(OBJ_ID)
        assert obj["current_state"] == "opened"

    def test_spawns_item_into_room(self, repo) -> None:
        repo.save_room_object(_room_object(spawns_item_slug="gem"))
        repo.save_item(_inert_item(slug="gem"))
        accepted = CommandValidationResult(accepted=True)
        cmd = ActivateObject(object_id=OBJ_ID, actor_id=ACTOR_A, trigger="open")
        result = apply_command(cmd, accepted, repo, CAMPAIGN)
        assert any(e.event_type == "item.spawned" for e in result.events)
        loose = repo.get_items_by_room(CAMPAIGN, ROOM_ID)
        assert len(loose) == 1
        assert loose[0]["slug"] == "gem"
        assert loose[0]["status"] == "active"

    def test_spawn_noop_when_slug_missing(self, repo) -> None:
        repo.save_room_object(_room_object(spawns_item_slug="missing"))
        accepted = CommandValidationResult(accepted=True)
        cmd = ActivateObject(object_id=OBJ_ID, actor_id=ACTOR_A, trigger="open")
        result = apply_command(cmd, accepted, repo, CAMPAIGN)
        assert not any(e.event_type == "item.spawned" for e in result.events)
        assert any(e.event_type == "object.transitioned" for e in result.events)

    def test_spawn_noop_when_already_placed(self, repo) -> None:
        repo.save_room_object(_room_object(spawns_item_slug="gem"))
        repo.save_item(_inert_item(slug="gem", room_id="room:test:other"))
        repo.update_item_room("item:test:gem", "room:test:other")
        accepted = CommandValidationResult(accepted=True)
        cmd = ActivateObject(object_id=OBJ_ID, actor_id=ACTOR_A, trigger="open")
        result = apply_command(cmd, accepted, repo, CAMPAIGN)
        assert not any(e.event_type == "item.spawned" for e in result.events)

    def test_advances_clock(self, repo) -> None:
        repo.save_room_object(_room_object(advances_clock_slug="doom"))
        repo.save_clock("clock:test:doom", CAMPAIGN, "Doom Clock", segments=4, filled=1)
        accepted = CommandValidationResult(accepted=True)
        cmd = ActivateObject(object_id=OBJ_ID, actor_id=ACTOR_A, trigger="open")
        result = apply_command(cmd, accepted, repo, CAMPAIGN)
        assert any(e.event_type == "clock.advanced" for e in result.events)
        clocks = repo.get_clocks(CAMPAIGN)
        assert clocks[0]["filled"] == 2

    def test_clock_noop_when_slug_missing(self, repo) -> None:
        repo.save_room_object(_room_object(advances_clock_slug="missing"))
        accepted = CommandValidationResult(accepted=True)
        cmd = ActivateObject(object_id=OBJ_ID, actor_id=ACTOR_A, trigger="open")
        result = apply_command(cmd, accepted, repo, CAMPAIGN)
        assert not any(e.event_type == "clock.advanced" for e in result.events)
        assert any(e.event_type == "object.transitioned" for e in result.events)

    def test_noop_when_rejected(self, repo) -> None:
        repo.save_room_object(_room_object())
        rejected = CommandValidationResult(accepted=False, rejection_reason="no transition")
        cmd = ActivateObject(object_id=OBJ_ID, actor_id=ACTOR_A, trigger="open")
        result = apply_command(cmd, rejected, repo, CAMPAIGN)
        assert result.events == []
        obj = repo.get_room_object(OBJ_ID)
        assert obj["current_state"] == "sealed"


class TestUnequipItemApplier:
    def test_clears_equipped_and_emits_event(self, repo) -> None:
        repo.save_item(_gear())
        repo.update_item_equipped(GEAR_ID, True)
        accepted = CommandValidationResult(accepted=True)
        result = apply_command(UnequipItem(item_id=GEAR_ID), accepted, repo, CAMPAIGN)
        assert len(result.events) == 1
        assert result.events[0].event_type == "item.unequipped"
        item = repo.get_items(CAMPAIGN)[0]
        assert item["is_equipped"] is False

    def test_noop_when_rejected(self, repo) -> None:
        repo.save_item(_gear())
        repo.update_item_equipped(GEAR_ID, True)
        rejected = CommandValidationResult(accepted=False, rejection_reason="not active")
        result = apply_command(UnequipItem(item_id=GEAR_ID), rejected, repo, CAMPAIGN)
        assert result.events == []
        item = repo.get_items(CAMPAIGN)[0]
        assert item["is_equipped"] is True


LOOSE_ID = "item:test:gem"
ROOM_A = "room:test:vault"


def _loose(item_id: str = LOOSE_ID, owner: str | None = None, room_id: str | None = ROOM_A) -> Item:
    from dungeon_daddy.rpg.models import Item
    return Item(
        item_id=item_id,
        campaign_id=CAMPAIGN,
        slug=item_id.split(":")[-1],
        display_name="Gem",
        item_type="dungeon_item",
        description="A sparkling gem.",
        owner_actor_id=owner,
        room_id=room_id,
    )


class TestPickUpItemApplier:
    def test_sets_owner_clears_room_emits_event(self, repo) -> None:
        repo.save_item(_loose())
        accepted = CommandValidationResult(accepted=True)
        result = apply_command(PickUpItem(item_id=LOOSE_ID, actor_id=ACTOR_A), accepted, repo, CAMPAIGN)
        assert len(result.events) == 1
        assert result.events[0].event_type == "item.picked_up"
        item = repo.get_items(CAMPAIGN)[0]
        assert item["owner_actor_id"] == ACTOR_A
        assert item["room_id"] is None

    def test_noop_when_rejected(self, repo) -> None:
        repo.save_item(_loose())
        rejected = CommandValidationResult(accepted=False, rejection_reason="at cap")
        result = apply_command(PickUpItem(item_id=LOOSE_ID, actor_id=ACTOR_A), rejected, repo, CAMPAIGN)
        assert result.events == []
        item = repo.get_items(CAMPAIGN)[0]
        assert item["owner_actor_id"] is None
        assert item["room_id"] == ROOM_A


class TestDropItemApplier:
    def test_clears_owner_sets_room_emits_event(self, repo) -> None:
        repo.save_item(_loose(owner=ACTOR_A, room_id=None))
        accepted = CommandValidationResult(accepted=True)
        result = apply_command(DropItem(item_id=LOOSE_ID, room_id=ROOM_A), accepted, repo, CAMPAIGN)
        assert len(result.events) == 1
        assert result.events[0].event_type == "item.dropped"
        item = repo.get_items(CAMPAIGN)[0]
        assert item["owner_actor_id"] is None
        assert item["room_id"] == ROOM_A

    def test_noop_when_rejected(self, repo) -> None:
        repo.save_item(_loose(owner=ACTOR_A, room_id=None))
        rejected = CommandValidationResult(accepted=False, rejection_reason="no owner")
        result = apply_command(DropItem(item_id=LOOSE_ID, room_id=ROOM_A), rejected, repo, CAMPAIGN)
        assert result.events == []
        item = repo.get_items(CAMPAIGN)[0]
        assert item["owner_actor_id"] == ACTOR_A
        assert item["room_id"] is None
