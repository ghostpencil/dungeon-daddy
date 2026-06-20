"""Action option providers for the Phase 50 Hybrid Action Model (Verb · Noun · Adverb).

The verb provider surfaces the choices the player may pick for the **Verb** slot of an
action Card: the 9 universal verbs (always available) plus any class verbs the actor has
earned via abilities flagged ``surfaces_as_verb``. The list reads the actor's *live*
``ActorAbility`` set, so Phase 52 advancement grows it with no rewiring here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from dungeon_daddy.rpg.models import ActorAbility
from dungeon_daddy.rpg.playbook import _UNIVERSAL_VERBS


@dataclass(frozen=True)
class VerbOption:
    verb: str
    label: str
    kind: str  # "universal" | "class"


def available_verbs(actor_abilities: Iterable[ActorAbility]) -> list[VerbOption]:
    options = [
        VerbOption(verb=verb, label=verb.capitalize(), kind="universal")
        for verb in sorted(_UNIVERSAL_VERBS)
    ]
    options.extend(
        VerbOption(verb=ability.ability_slug, label=ability.display_name, kind="class")
        for ability in actor_abilities
        if ability.surfaces_as_verb
    )
    return options
