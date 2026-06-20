"""Slice 5 — resolve a validated ``ActionCard`` into an engine ``PlayerCommand``.

The second half of the Phase 50 grammar: once a Card's Verb·Noun·Adverb has
passed :func:`validate_card`, a *mutation* verb is translated into the matching
``PlayerCommand`` (``rpg/command.py``) the engine already knows how to validate
and apply. The adverb rides through as ``how`` on the one command that has a
``how`` slot (``MoveParty``); the other commands carry no adverb axis.

Non-mutation verbs (``fight``/``study``/``sway``/…) return ``None`` — those
resolve via the action-roll path in Slice 6.
"""
from __future__ import annotations

from dungeon_daddy.rpg.action_options import (
    VERB_ACTIVATE,
    VERB_EQUIP,
    VERB_MOVE,
    VERB_PICK_UP,
)
from dungeon_daddy.rpg.command import (
    ActivateObject,
    EquipItem,
    MoveParty,
    PickUpItem,
    PlayerCommand,
)


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
