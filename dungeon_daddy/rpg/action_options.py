"""Action option providers for the Phase 50 Hybrid Action Model (Verb · Noun · Adverb).

The verb provider surfaces the choices the player may pick for the **Verb** slot of an
action Card: the 9 universal verbs (always available) plus any class verbs the actor has
earned via abilities flagged ``surfaces_as_verb``. The list reads the actor's *live*
``ActorAbility`` set, so Phase 52 advancement grows it with no rewiring here.

The noun provider surfaces the **Noun** slot: the concrete targets in the actor's current
room (objects, loose items, NPCs, monsters, exits), the actor's carried items, plus the
synthetic ``self`` and ``room`` targets. It reads the enriched ``current_room`` context
block and is forgiving of absent source keys.

The adverb provider surfaces the **Adverb** slot: the universal adverb pool (base adverbs
plus world-flag-gated ones, restricted to engine-resolvable ``HOW_MODIFIER_FLAGS`` keys)
plus the actor playbook's signature adverbs filtered by the noun's ``target_type``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Collection, Iterable, Mapping

from pydantic import BaseModel

from dungeon_daddy.rpg.models import ActorAbility
from dungeon_daddy.rpg.move_party import HOW_MODIFIER_FLAGS
from dungeon_daddy.rpg.playbook import PlaybookLibrary, _UNIVERSAL_VERBS


# Canonical verb slugs. ``move`` is one of the 9 universal skill verbs but is
# also an engine mutation; the interaction verbs below are *not* skill verbs —
# they map straight to a ``PlayerCommand`` (see ``rpg/action_resolution.py``).
VERB_MOVE = "move"
VERB_PICK_UP = "pick-up"
VERB_EQUIP = "equip"
VERB_ACTIVATE = "activate"

# Interaction verbs surfaced in the Verb slot alongside the universal verbs.
_INTERACTION_VERBS: dict[str, str] = {
    VERB_PICK_UP: "Pick Up",
    VERB_EQUIP: "Equip",
    VERB_ACTIVATE: "Activate",
}


@dataclass(frozen=True)
class VerbOption:
    verb: str
    label: str
    kind: str  # "universal" | "interaction" | "class"


@dataclass(frozen=True)
class NounOption:
    noun_id: str  # the full engine id the command layer needs (object_id/item_id/...)
    label: str
    target_type: str  # one of _VALID_TARGET_TYPES (npc/object/item/room/self/monster)
    slug: str | None = None  # human-readable identity for display (objects/items only)


@dataclass(frozen=True)
class AdverbOption:
    adverb: str
    label: str
    kind: str  # "universal" | "signature"


class ActionCard(BaseModel):
    """The player's structured action declaration: a Verb · Noun · Adverb grammar.

    The input-dual of an ``LLMReactionProposal`` — the player declares an action
    through bounded, engine-offered choices that :func:`validate_card` checks
    against the sets the providers offered for the current room/actor.
    """

    verb: str
    noun_id: str
    adverb: str


@dataclass(frozen=True)
class CardOptions:
    """The engine-offered sets a Card is validated against (Slices 1–3 output)."""

    verbs: list[VerbOption] = field(default_factory=list)
    nouns: list[NounOption] = field(default_factory=list)
    adverbs: list[AdverbOption] = field(default_factory=list)


@dataclass(frozen=True)
class CardError:
    """Why a Card was rejected: which slot was out of bounds and a reason string."""

    field: str  # "verb" | "noun" | "adverb"
    reason: str


def validate_card(card: ActionCard, options: CardOptions) -> CardError | None:
    """Reject a Card whose verb/noun/adverb is not in the offered sets.

    Engine-bounded, mirroring proposal validation: a Card may only name a
    choice the providers actually surfaced for the current room/actor. Returns
    the first :class:`CardError` found, or ``None`` when the Card is in bounds.
    """
    if card.verb not in {v.verb for v in options.verbs}:
        return CardError(field="verb", reason=f"Verb not offered: {card.verb}")
    if card.noun_id not in {n.noun_id for n in options.nouns}:
        return CardError(field="noun", reason=f"Noun not offered: {card.noun_id}")
    if card.adverb not in {a.adverb for a in options.adverbs}:
        return CardError(field="adverb", reason=f"Adverb not offered: {card.adverb}")
    return None


# Universal adverb surfacing (carries forward the Phase 48 ``ui/how_chips``
# logic that Slice 8 retired). Base adverbs are always offered; the rest surface
# only when the named world-context flag is present. Restricted at call time to
# keys the engine's ``HOW_MODIFIER_FLAGS`` table can actually resolve.
_BASE_ADVERBS: tuple[str, ...] = ("cautiously", "quickly", "boldly")
_CONDITIONAL_ADVERBS: dict[str, str] = {
    "stealthily": "can_sense",
    "deliberately": "one_way",
    "reverently": "ritual_connector",
    "recklessly": "armed_trap",
}

_DEFAULT_LIBRARY: PlaybookLibrary | None = None


def _default_library() -> PlaybookLibrary:
    global _DEFAULT_LIBRARY
    if _DEFAULT_LIBRARY is None:
        _DEFAULT_LIBRARY = PlaybookLibrary()
    return _DEFAULT_LIBRARY


def available_verbs(actor_abilities: Iterable[ActorAbility]) -> list[VerbOption]:
    options = [
        VerbOption(verb=verb, label=verb.capitalize(), kind="universal")
        for verb in sorted(_UNIVERSAL_VERBS)
    ]
    options.extend(
        VerbOption(verb=verb, label=label, kind="interaction")
        for verb, label in _INTERACTION_VERBS.items()
    )
    options.extend(
        VerbOption(verb=ability.ability_slug, label=ability.display_name, kind="class")
        for ability in actor_abilities
        if ability.surfaces_as_verb
    )
    return options


def available_adverbs(
    playbook_slug: str,
    *,
    target_type: str,
    world_flags: Collection[str],
    library: PlaybookLibrary | None = None,
) -> list[AdverbOption]:
    """Surface the choices for the **Adverb** slot of an action Card.

    The universal pool mirrors the Phase 48 ``how_chips`` surfacing logic: the
    base adverbs (``cautiously``/``quickly``/``boldly``) plus the conditional
    ones that ``world_flags`` enables — restricted to keys the engine's
    ``HOW_MODIFIER_FLAGS`` table can resolve. Signature adverbs from the
    playbook are appended when they apply to ``target_type``.
    """
    flags = set(world_flags)
    universal = list(_BASE_ADVERBS)
    universal.extend(
        adverb
        for adverb, gate in _CONDITIONAL_ADVERBS.items()
        if gate in flags
    )
    options = [
        AdverbOption(adverb=adverb, label=adverb.capitalize(), kind="universal")
        for adverb in universal
        if adverb in HOW_MODIFIER_FLAGS
    ]

    playbook = (library or _default_library()).get(playbook_slug)
    surfaced = {opt.adverb for opt in options}
    for sig in playbook.signature_adverbs:
        if target_type in sig.target_types and sig.slug not in surfaced:
            options.append(
                AdverbOption(
                    adverb=sig.slug,
                    label=sig.slug.replace("-", " ").title(),
                    kind="signature",
                )
            )
            surfaced.add(sig.slug)
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

    For objects and items the ``noun_id`` is the full engine id (``object_id`` /
    ``item_id``) the command layer needs, with the human-readable ``slug`` kept on
    the option for display; the remaining sources already key on full ids.
    """
    options: list[NounOption] = []
    for obj in room_context.get("objects", []):
        options.append(
            NounOption(
                noun_id=obj["object_id"],
                label=obj["display_name"],
                target_type="object",
                slug=obj["slug"],
            )
        )
    for item in room_context.get("loose_items", []):
        options.append(
            NounOption(
                noun_id=item["item_id"],
                label=item["display_name"],
                target_type="item",
                slug=item["slug"],
            )
        )
    for item in actor.get("carried_items", []):
        options.append(
            NounOption(
                noun_id=item["item_id"],
                label=item["display_name"],
                target_type="item",
                slug=item["slug"],
            )
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
