from __future__ import annotations

from dungeon_daddy.rpg.command import ActivateObject, ConsumeItem, ConsumeKitCharge, EquipItem, GiveItem, TakeItem, UnequipItem
from dungeon_daddy.rpg.command_validator import validate_command
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


class TestConsumeKitChargeValidation:
    def test_rejects_unknown_item_id(self, repo) -> None:
        result = validate_command(_command(), repo, CAMPAIGN)
        assert not result.accepted
        assert len(result.rejection_events) == 1
        assert result.rejection_events[0].event_type == "command.rejected"

    def test_rejects_non_kit_item(self, repo) -> None:
        dungeon_item = Item(
            item_id=KIT_ID,
            campaign_id=CAMPAIGN,
            slug="lockpick-kit",
            display_name="Lockpick Kit",
            item_type="dungeon_item",
            description="A set of lockpicks.",
        )
        repo.save_item(dungeon_item)
        result = validate_command(_command(), repo, CAMPAIGN)
        assert not result.accepted
        assert result.rejection_reason is not None
        assert "not a class_kit" in result.rejection_reason

    def test_rejects_inactive_kit(self, repo) -> None:
        repo.save_item(_kit())
        repo.update_item_status(KIT_ID, "consumed")
        result = validate_command(_command(), repo, CAMPAIGN)
        assert not result.accepted
        assert result.rejection_reason is not None
        assert "not active" in result.rejection_reason

    def test_rejects_depleted_kit(self, repo) -> None:
        repo.save_item(_kit(charges_current=0))
        result = validate_command(_command(), repo, CAMPAIGN)
        assert not result.accepted
        assert result.rejection_reason is not None
        assert "No charges" in result.rejection_reason

    def test_accepts_valid_kit_charge(self, repo) -> None:
        repo.save_item(_kit(charges_current=2))
        result = validate_command(_command(), repo, CAMPAIGN)
        assert result.accepted
        assert result.rejection_reason is None
        assert result.rejection_events == []


def _dungeon_item(item_id: str = ITEM_ID, status: str = "active") -> Item:
    return Item(
        item_id=item_id,
        campaign_id=CAMPAIGN,
        slug=item_id.split(":")[-1],
        display_name="Healing Potion",
        item_type="dungeon_item",
        description="Restores vitality.",
        owner_actor_id=ACTOR_A,
        status=status,  # type: ignore[arg-type]
    )


def _save_pc(repo, actor_id: str = ACTOR_B) -> None:
    repo.save_actor(actor_id, CAMPAIGN, "pc", actor_id.split(":")[-1], "Rogue")


def _save_npc(repo, actor_id: str = ACTOR_B) -> None:
    repo.save_actor(actor_id, CAMPAIGN, "npc", actor_id.split(":")[-1], "Rogue NPC")


class TestConsumeItemValidation:
    def test_rejects_unknown_item(self, repo) -> None:
        result = validate_command(ConsumeItem(item_id=ITEM_ID, reason="drink"), repo, CAMPAIGN)
        assert not result.accepted
        assert result.rejection_events[0].event_type == "command.rejected"

    def test_rejects_inactive_item(self, repo) -> None:
        repo.save_item(_dungeon_item(status="consumed"))
        result = validate_command(ConsumeItem(item_id=ITEM_ID, reason="drink"), repo, CAMPAIGN)
        assert not result.accepted
        assert "not active" in (result.rejection_reason or "")

    def test_accepts_active_item(self, repo) -> None:
        repo.save_item(_dungeon_item())
        result = validate_command(ConsumeItem(item_id=ITEM_ID, reason="drink"), repo, CAMPAIGN)
        assert result.accepted


class TestGiveItemValidation:
    def test_rejects_unknown_item(self, repo) -> None:
        result = validate_command(GiveItem(item_id=ITEM_ID, to_actor_id=ACTOR_B), repo, CAMPAIGN)
        assert not result.accepted
        assert result.rejection_events[0].event_type == "command.rejected"

    def test_rejects_unknown_target_actor(self, repo) -> None:
        repo.save_item(_dungeon_item())
        result = validate_command(GiveItem(item_id=ITEM_ID, to_actor_id=ACTOR_B), repo, CAMPAIGN)
        assert not result.accepted
        assert "Unknown target actor" in (result.rejection_reason or "")

    def test_rejects_non_pc_target(self, repo) -> None:
        repo.save_item(_dungeon_item())
        _save_npc(repo)
        result = validate_command(GiveItem(item_id=ITEM_ID, to_actor_id=ACTOR_B), repo, CAMPAIGN)
        assert not result.accepted
        assert "not a player character" in (result.rejection_reason or "")

    def test_rejects_when_target_at_dungeon_item_cap(self, repo) -> None:
        repo.save_item(_dungeon_item())
        _save_pc(repo)
        for i in range(10):
            repo.save_item(_dungeon_item(item_id=f"item:test:item-{i}"))
            repo.update_item_owner(f"item:test:item-{i}", ACTOR_B)
        result = validate_command(GiveItem(item_id=ITEM_ID, to_actor_id=ACTOR_B), repo, CAMPAIGN)
        assert not result.accepted
        assert "cap" in (result.rejection_reason or "")

    def test_accepts_valid_give(self, repo) -> None:
        repo.save_item(_dungeon_item())
        _save_pc(repo)
        result = validate_command(GiveItem(item_id=ITEM_ID, to_actor_id=ACTOR_B), repo, CAMPAIGN)
        assert result.accepted


class TestTakeItemValidation:
    def test_rejects_unknown_item(self, repo) -> None:
        result = validate_command(TakeItem(item_id=ITEM_ID), repo, CAMPAIGN)
        assert not result.accepted
        assert result.rejection_events[0].event_type == "command.rejected"

    def test_rejects_unowned_item(self, repo) -> None:
        unowned = Item(
            item_id=ITEM_ID,
            campaign_id=CAMPAIGN,
            slug="potion",
            display_name="Potion",
            item_type="dungeon_item",
            description="A potion.",
            owner_actor_id=None,
        )
        repo.save_item(unowned)
        result = validate_command(TakeItem(item_id=ITEM_ID), repo, CAMPAIGN)
        assert not result.accepted
        assert "no owner" in (result.rejection_reason or "")

    def test_accepts_owned_item(self, repo) -> None:
        repo.save_item(_dungeon_item())
        result = validate_command(TakeItem(item_id=ITEM_ID), repo, CAMPAIGN)
        assert result.accepted


def _gear(item_id: str = GEAR_ID, status: str = "active", owner: str | None = ACTOR_A) -> Item:
    return Item(
        item_id=item_id,
        campaign_id=CAMPAIGN,
        slug=item_id.split(":")[-1],
        display_name="Iron Sword",
        item_type="equipped_gear",
        description="A sturdy iron sword.",
        owner_actor_id=owner,
        status=status,  # type: ignore[arg-type]
    )


class TestEquipItemValidation:
    def test_rejects_unknown_item(self, repo) -> None:
        result = validate_command(EquipItem(item_id=GEAR_ID), repo, CAMPAIGN)
        assert not result.accepted
        assert result.rejection_events[0].event_type == "command.rejected"

    def test_rejects_non_equipped_gear_type(self, repo) -> None:
        repo.save_item(_dungeon_item())
        result = validate_command(EquipItem(item_id=ITEM_ID), repo, CAMPAIGN)
        assert not result.accepted
        assert "not equipped_gear" in (result.rejection_reason or "")

    def test_rejects_inactive_gear(self, repo) -> None:
        repo.save_item(_gear(status="lost"))
        result = validate_command(EquipItem(item_id=GEAR_ID), repo, CAMPAIGN)
        assert not result.accepted
        assert "not active" in (result.rejection_reason or "")

    def test_rejects_unowned_gear(self, repo) -> None:
        repo.save_item(_gear(owner=None))
        result = validate_command(EquipItem(item_id=GEAR_ID), repo, CAMPAIGN)
        assert not result.accepted
        assert "no owner" in (result.rejection_reason or "")

    def test_accepts_valid_equipped_gear(self, repo) -> None:
        repo.save_item(_gear())
        result = validate_command(EquipItem(item_id=GEAR_ID), repo, CAMPAIGN)
        assert result.accepted
        assert result.rejection_events == []


class TestUnequipItemValidation:
    def test_rejects_unknown_item(self, repo) -> None:
        result = validate_command(UnequipItem(item_id=GEAR_ID), repo, CAMPAIGN)
        assert not result.accepted
        assert result.rejection_events[0].event_type == "command.rejected"

    def test_rejects_non_equipped_gear_type(self, repo) -> None:
        repo.save_item(_dungeon_item())
        result = validate_command(UnequipItem(item_id=ITEM_ID), repo, CAMPAIGN)
        assert not result.accepted
        assert "not equipped_gear" in (result.rejection_reason or "")

    def test_rejects_inactive_gear(self, repo) -> None:
        repo.save_item(_gear(status="lost"))
        result = validate_command(UnequipItem(item_id=GEAR_ID), repo, CAMPAIGN)
        assert not result.accepted
        assert "not active" in (result.rejection_reason or "")

    def test_rejects_unowned_gear(self, repo) -> None:
        repo.save_item(_gear(owner=None))
        result = validate_command(UnequipItem(item_id=GEAR_ID), repo, CAMPAIGN)
        assert not result.accepted
        assert "no owner" in (result.rejection_reason or "")

    def test_accepts_valid_equipped_gear(self, repo) -> None:
        repo.save_item(_gear())
        result = validate_command(UnequipItem(item_id=GEAR_ID), repo, CAMPAIGN)
        assert result.accepted
        assert result.rejection_events == []


OBJECT_ID = "obj:test:iron-chest"
ROOM_ID = "room:test:vault"


def _object(
    current_state: str = "locked",
    transitions: list[ObjectTransition] | None = None,
) -> RoomObject:
    if transitions is None:
        transitions = [
            ObjectTransition(
                transition_id="tr:test:unlock",
                object_id=OBJECT_ID,
                from_state="locked",
                to_state="unlocked",
                trigger="unlock",
            )
        ]
    return RoomObject(
        object_id=OBJECT_ID,
        campaign_id=CAMPAIGN,
        room_id=ROOM_ID,
        level_id="level:test:1",
        slug="iron-chest",
        display_name="Iron Chest",
        archetype="container",
        description="A heavy iron chest.",
        current_state=current_state,
        transitions=transitions,
    )


def _activate(trigger: str = "unlock") -> ActivateObject:
    return ActivateObject(object_id=OBJECT_ID, actor_id=ACTOR_A, trigger=trigger)


class TestActivateObjectValidation:
    def test_rejects_unknown_object(self, repo) -> None:
        result = validate_command(_activate(), repo, CAMPAIGN)
        assert not result.accepted
        assert len(result.rejection_events) == 1
        assert result.rejection_events[0].event_type == "command.rejected"

    def test_rejects_unmatched_trigger(self, repo) -> None:
        repo.save_room_object(_object())
        result = validate_command(_activate(trigger="force"), repo, CAMPAIGN)
        assert not result.accepted
        assert "No transition" in (result.rejection_reason or "")

    def test_rejects_trigger_valid_for_other_state(self, repo) -> None:
        # 'unlock' exists but only from 'locked'; object is already 'unlocked'
        repo.save_room_object(_object(current_state="unlocked"))
        result = validate_command(_activate(trigger="unlock"), repo, CAMPAIGN)
        assert not result.accepted
        assert "No transition" in (result.rejection_reason or "")

    def test_rejects_missing_required_item(self, repo) -> None:
        repo.save_room_object(
            _object(
                transitions=[
                    ObjectTransition(
                        transition_id="tr:test:unlock",
                        object_id=OBJECT_ID,
                        from_state="locked",
                        to_state="unlocked",
                        trigger="unlock",
                        requires_item_slug="brass-key",
                    )
                ]
            )
        )
        result = validate_command(_activate(), repo, CAMPAIGN)
        assert not result.accepted
        assert "brass-key" in (result.rejection_reason or "")

    def test_rejects_required_item_present_but_inactive(self, repo) -> None:
        repo.save_room_object(
            _object(
                transitions=[
                    ObjectTransition(
                        transition_id="tr:test:unlock",
                        object_id=OBJECT_ID,
                        from_state="locked",
                        to_state="unlocked",
                        trigger="unlock",
                        requires_item_slug="brass-key",
                    )
                ]
            )
        )
        key = Item(
            item_id="item:test:brass-key",
            campaign_id=CAMPAIGN,
            slug="brass-key",
            display_name="Brass Key",
            item_type="dungeon_item",
            description="An ornate brass key.",
            owner_actor_id=ACTOR_A,
            status="lost",
        )
        repo.save_item(key)
        result = validate_command(_activate(), repo, CAMPAIGN)
        assert not result.accepted
        assert "brass-key" in (result.rejection_reason or "")

    def test_accepts_valid_transition_without_required_item(self, repo) -> None:
        repo.save_room_object(_object())
        result = validate_command(_activate(), repo, CAMPAIGN)
        assert result.accepted
        assert result.rejection_reason is None
        assert result.rejection_events == []

    def test_accepts_valid_transition_with_required_item(self, repo) -> None:
        repo.save_room_object(
            _object(
                transitions=[
                    ObjectTransition(
                        transition_id="tr:test:unlock",
                        object_id=OBJECT_ID,
                        from_state="locked",
                        to_state="unlocked",
                        trigger="unlock",
                        requires_item_slug="brass-key",
                    )
                ]
            )
        )
        key = Item(
            item_id="item:test:brass-key",
            campaign_id=CAMPAIGN,
            slug="brass-key",
            display_name="Brass Key",
            item_type="dungeon_item",
            description="An ornate brass key.",
            owner_actor_id=ACTOR_A,
            status="active",
        )
        repo.save_item(key)
        result = validate_command(_activate(), repo, CAMPAIGN)
        assert result.accepted
        assert result.rejection_events == []
