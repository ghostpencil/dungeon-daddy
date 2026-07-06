from dungeon_daddy.rpg.command import (
    ActivateObject,
    ConsumeItem,
    ConsumeKitCharge,
    EquipItem,
    GiveItem,
    TakeItem,
    UnequipItem,
)


def test_consume_kit_charge_instantiates() -> None:
    cmd = ConsumeKitCharge(item_id="item:test:kit", reason="pick the lock")
    assert cmd.kind == "consume_kit_charge"
    assert cmd.item_id == "item:test:kit"
    assert cmd.reason == "pick the lock"


def test_consume_item_instantiates() -> None:
    cmd = ConsumeItem(item_id="item:test:potion", reason="heal wounds")
    assert cmd.kind == "consume_item"
    assert cmd.item_id == "item:test:potion"
    assert cmd.reason == "heal wounds"


def test_give_item_instantiates() -> None:
    cmd = GiveItem(item_id="item:test:torch", to_actor_id="actor:test:rogue")
    assert cmd.kind == "give_item"
    assert cmd.item_id == "item:test:torch"
    assert cmd.to_actor_id == "actor:test:rogue"


def test_take_item_instantiates() -> None:
    cmd = TakeItem(item_id="item:test:rope")
    assert cmd.kind == "take_item"
    assert cmd.item_id == "item:test:rope"


def test_equip_item_instantiates() -> None:
    cmd = EquipItem(item_id="item:test:sword")
    assert cmd.kind == "equip_item"
    assert cmd.item_id == "item:test:sword"


def test_unequip_item_instantiates() -> None:
    cmd = UnequipItem(item_id="item:test:sword")
    assert cmd.kind == "unequip_item"
    assert cmd.item_id == "item:test:sword"


def test_activate_object_instantiates() -> None:
    cmd = ActivateObject(object_id="obj:test:chest", actor_id="actor:test:rogue", trigger="unlock")
    assert cmd.kind == "activate_object"
    assert cmd.object_id == "obj:test:chest"
    assert cmd.actor_id == "actor:test:rogue"
    assert cmd.trigger == "unlock"
