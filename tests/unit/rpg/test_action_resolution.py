from dungeon_daddy.rpg.action_options import ActionCard
from dungeon_daddy.rpg.action_resolution import resolve_card
from dungeon_daddy.rpg.command import (
    ActivateObject,
    EquipItem,
    MoveParty,
    PickUpItem,
)


def test_move_card_resolves_to_move_party_carrying_adverb_as_how():
    card = ActionCard(verb="move", noun_id="exit:c1:north", adverb="cautiously")
    cmd = resolve_card(card, actor_id="actor:c1:mara")
    assert cmd == MoveParty(exit_id="exit:c1:north", how="cautiously")


def test_pick_up_card_resolves_to_pick_up_item_with_actor():
    card = ActionCard(verb="pick-up", noun_id="gold-coin", adverb="quickly")
    cmd = resolve_card(card, actor_id="actor:c1:mara")
    assert cmd == PickUpItem(item_id="gold-coin", actor_id="actor:c1:mara")


def test_equip_card_resolves_to_equip_item():
    card = ActionCard(verb="equip", noun_id="dagger", adverb="boldly")
    cmd = resolve_card(card, actor_id="actor:c1:mara")
    assert cmd == EquipItem(item_id="dagger")


def test_activate_card_resolves_to_activate_object_with_actor_and_trigger():
    card = ActionCard(verb="activate", noun_id="iron-chest", adverb="cautiously")
    cmd = resolve_card(card, actor_id="actor:c1:mara", trigger="open")
    assert cmd == ActivateObject(
        object_id="iron-chest", actor_id="actor:c1:mara", trigger="open"
    )


def test_activate_card_without_trigger_raises():
    import pytest

    card = ActionCard(verb="activate", noun_id="iron-chest", adverb="cautiously")
    with pytest.raises(ValueError):
        resolve_card(card, actor_id="actor:c1:mara")


def test_non_mutation_verb_resolves_to_none():
    card = ActionCard(verb="fight", noun_id="actor:c1:ghoul", adverb="boldly")
    assert resolve_card(card, actor_id="actor:c1:mara") is None
