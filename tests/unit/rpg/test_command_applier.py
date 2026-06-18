from __future__ import annotations

from dungeon_daddy.rpg.command import ConsumeItem, ConsumeKitCharge, EquipItem, GiveItem, TakeItem, UnequipItem
from dungeon_daddy.rpg.command_applier import apply_command
from dungeon_daddy.rpg.command_validator import CommandValidationResult
from dungeon_daddy.rpg.models import Item

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


def _gear(owner: str = ACTOR_A) -> "Item":
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
