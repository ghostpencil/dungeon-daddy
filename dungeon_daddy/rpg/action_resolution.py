"""Slice 5 — resolve a validated ``ActionCard`` into an engine ``PlayerCommand``.

The second half of the Phase 50 grammar: once a Card's Verb·Noun·Adverb has
passed :func:`validate_card`, a *mutation* verb is translated into the matching
``PlayerCommand`` (``rpg/command.py``) the engine already knows how to validate
and apply. The adverb rides through as ``how`` on the one command that has a
``how`` slot (``MoveParty``); the other commands carry no adverb axis.

Non-mutation verbs (``fight``/``study``/``sway``/…) return ``None`` here and
resolve via the action-roll path (:func:`resolve_card_roll`, Slice 6): the Card's
verb names the action rating, the adverb contributes a dice-pool delta plus
world-side-effect flags, and the existing roller (:func:`resolve_action`) is
called directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from dungeon_daddy.rpg.action_options import (
    VERB_ACTIVATE,
    VERB_EQUIP,
    VERB_MOVE,
    VERB_PICK_UP,
)
from dungeon_daddy.rpg.actions import resolve_action
from dungeon_daddy.rpg.command import (
    ActivateObject,
    EquipItem,
    MoveParty,
    PickUpItem,
    PlayerCommand,
)
from dungeon_daddy.rpg.models import ActionRequest, ActionResolution
from dungeon_daddy.rpg.move_party import HOW_MODIFIER_FLAGS


def resolve_card(
    card,
    *,
    actor_id: str,
    trigger: str | None = None,
) -> PlayerCommand | None:
    """Map a mutation-verb Card to its ``PlayerCommand``.

    ``actor_id`` is the acting actor (needed by pick-up/activate). ``trigger`` is
    the object transition to fire and is required for ``activate``. Returns
    ``None`` for non-mutation (action-roll) verbs, which Slice 6 resolves.
    """
    if card.verb == VERB_MOVE:
        return MoveParty(exit_id=card.noun_id, how=card.adverb)
    if card.verb == VERB_PICK_UP:
        return PickUpItem(item_id=card.noun_id, actor_id=actor_id)
    if card.verb == VERB_EQUIP:
        return EquipItem(item_id=card.noun_id)
    if card.verb == VERB_ACTIVATE:
        if trigger is None:
            raise ValueError("activate card requires a trigger")
        return ActivateObject(
            object_id=card.noun_id, actor_id=actor_id, trigger=trigger
        )
    return None


@dataclass(frozen=True)
class CardRoll:
    """The outcome of an action-roll Card.

    ``resolution`` is the full :class:`ActionResolution` from the roller (dice,
    outcome tier, stress cost). ``side_effect_flags`` are the adverb's
    world-side-effect flags — every ``HOW_MODIFIER_FLAGS`` entry that is *not* a
    ``dice:±N`` pool delta — for the LLM/world layer to apply to its narration.
    """

    resolution: ActionResolution
    side_effect_flags: frozenset[str]


def resolve_card_roll(
    card,
    *,
    campaign_id: str,
    actor: Mapping,
    momentum_spend: int = 0,
    push_yourself: bool = False,
    intent: str | None = None,
    fixed: list[int] | None = None,
) -> CardRoll:
    """Resolve a non-mutation Card as an action roll, calling the roller directly.

    The dice pool is the actor's rating for the Card's verb plus the adverb's
    ``dice:±N`` deltas (the roller adds ``momentum_spend`` and the push die). The
    remaining adverb flags are returned as world-side-effects. Raises
    ``ValueError`` for a mutation verb — those go through :func:`resolve_card`.
    """
    if card.verb in (VERB_MOVE, VERB_PICK_UP, VERB_EQUIP, VERB_ACTIVATE):
        raise ValueError(f"mutation verb is not an action roll: {card.verb}")

    rating = actor.get("actions", {}).get(card.verb, 0)
    dice_delta, side_effects = _split_adverb_flags(card.adverb)

    request = ActionRequest(
        campaign_id=campaign_id,
        actor_id=actor["actor_id"],
        action_key=card.verb,
        dice_pool=rating + dice_delta,
        momentum_spend=momentum_spend,
        push_yourself=push_yourself,
        intent=intent,
    )
    resolution = resolve_action(request, fixed=fixed)
    return CardRoll(resolution=resolution, side_effect_flags=frozenset(side_effects))


def _split_adverb_flags(adverb: str) -> tuple[int, set[str]]:
    """Split an adverb's flags into (summed ``dice:±N`` delta, side-effect flags)."""
    dice_delta = 0
    side_effects: set[str] = set()
    for flag in HOW_MODIFIER_FLAGS.get(adverb, set()):
        if flag.startswith("dice:"):
            dice_delta += int(flag.split(":", 1)[1])
        else:
            side_effects.add(flag)
    return dice_delta, side_effects
