"""Action option providers for the Phase 50 Hybrid Action Model (Verb · Noun · Adverb).

The verb provider surfaces the choices the player may pick for the **Verb** slot of an
action Card: the 9 universal verbs (always available) plus any class verbs the actor has
earned via abilities flagged ``surfaces_as_verb``. The list reads the actor's *live*
``ActorAbility`` set, so Phase 52 advancement grows it with no rewiring here.

The noun provider surfaces the **Noun** slot: the concrete targets in the actor's current
room (objects, loose items, NPCs, monsters, exits), the actor's carried items, plus the
synthetic ``self`` and ``room`` targets. It reads the enriched ``current_room`` context
block and is forgiving of absent source keys.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from dungeon_daddy.rpg.models import ActorAbility
from dungeon_daddy.rpg.playbook import _UNIVERSAL_VERBS


@dataclass(frozen=True)
class VerbOption:
    verb: str
    label: str
    kind: str  # "universal" | "class"


@dataclass(frozen=True)
class NounOption:
    noun_id: str
    label: str
    target_type: str  # one of _VALID_TARGET_TYPES (npc/object/item/room/self/monster)


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


def available_nouns(
    room_context: Mapping, actor: Mapping
) -> list[NounOption]:
    """Surface the targets the player may pick for the **Noun** slot of an action Card.

    Reads the enriched Phase 47/48 ``current_room`` context block (``objects``,
    ``loose_items``, ``npcs``, ``monsters``, ``exits``) plus the acting ``actor``'s
    carried items, and always adds the synthetic ``self`` (the actor) and — when the
    context names a room — ``room`` (the current room). The function is *forgiving*:
    any source key absent from ``room_context`` simply contributes nothing.
    """
    options: list[NounOption] = []
    for obj in room_context.get("objects", []):
        options.append(
            NounOption(noun_id=obj["slug"], label=obj["display_name"], target_type="object")
        )
    for item in room_context.get("loose_items", []):
        options.append(
            NounOption(noun_id=item["slug"], label=item["display_name"], target_type="item")
        )
    for item in actor.get("carried_items", []):
        options.append(
            NounOption(noun_id=item["slug"], label=item["display_name"], target_type="item")
        )
    for npc in room_context.get("npcs", []):
        options.append(
            NounOption(noun_id=npc["actor_id"], label=npc["display_name"], target_type="npc")
        )
    for monster in room_context.get("monsters", []):
        options.append(
            NounOption(
                noun_id=monster["actor_id"], label=monster["display_name"], target_type="monster"
            )
        )
    for ext in room_context.get("exits", []):
        options.append(
            NounOption(noun_id=ext["exit_id"], label=ext["label"], target_type="room")
        )
    options.append(
        NounOption(noun_id=actor["actor_id"], label=actor["display_name"], target_type="self")
    )
    room_id = room_context.get("room_id")
    if room_id is not None:
        options.append(NounOption(noun_id=room_id, label="This room", target_type="room"))
    return options
