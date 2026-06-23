import pytest

from dungeon_daddy.rpg.action_options import ActionCard
from dungeon_daddy.rpg.action_resolution import resolve_card, resolve_card_roll
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


# --- Slice 6: Card -> action roll resolution -------------------------------

ROLL_ACTOR = {"actor_id": "actor:c1:mara", "actions": {"fight": 2}}


def test_roll_card_sizes_pool_from_actor_rating():
    # rating 2 -> a 2-die pool; fixed dice make the outcome deterministic.
    card = ActionCard(verb="fight", noun_id="actor:c1:ghoul", adverb="boldly")
    roll = resolve_card_roll(
        card, campaign_id="campaign:test", actor=ROLL_ACTOR, fixed=[6, 3]
    )
    assert roll.resolution.dice_rolled == [6, 3]
    assert roll.resolution.outcome == "full"


def test_roll_card_passes_adverb_side_effect_flags_through():
    # "boldly" carries only world-side-effect flags (no dice delta).
    card = ActionCard(verb="fight", noun_id="actor:c1:ghoul", adverb="boldly")
    roll = resolve_card_roll(
        card, campaign_id="campaign:test", actor=ROLL_ACTOR, fixed=[6, 1]
    )
    assert roll.side_effect_flags == {"occupants_aware", "advance_npc_reaction"}


def test_roll_card_applies_adverb_dice_delta_to_pool(monkeypatch):
    # No shipping adverb carries a dice delta yet; verify the dice:+N convention:
    # a +1 flag grows the pool and is stripped from the side-effect flags.
    from dungeon_daddy.rpg.move_party import HOW_MODIFIER_FLAGS

    monkeypatch.setitem(HOW_MODIFIER_FLAGS, "boldly", {"dice:+1", "occupants_aware"})
    card = ActionCard(verb="fight", noun_id="actor:c1:ghoul", adverb="boldly")
    roll = resolve_card_roll(
        card, campaign_id="campaign:test", actor=ROLL_ACTOR, fixed=[1, 1, 1]
    )
    assert roll.resolution.dice_rolled == [1, 1, 1]  # rating 2 + delta 1 = 3 dice
    assert roll.side_effect_flags == {"occupants_aware"}


def test_roll_card_adds_momentum_to_pool():
    card = ActionCard(verb="fight", noun_id="actor:c1:ghoul", adverb="boldly")
    roll = resolve_card_roll(
        card,
        campaign_id="campaign:test",
        actor=ROLL_ACTOR,
        momentum_spend=1,
        fixed=[1, 1, 1],
    )
    assert roll.resolution.dice_rolled == [1, 1, 1]  # rating 2 + momentum 1 = 3 dice


def test_roll_card_rejects_mutation_verb():
    card = ActionCard(verb="move", noun_id="exit:c1:north", adverb="cautiously")
    with pytest.raises(ValueError):
        resolve_card_roll(card, campaign_id="campaign:test", actor=ROLL_ACTOR)
