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
VERB_GIVE = "give"
VERB_USE = "use"
VERB_COMBINE = "combine"
VERB_LOOK = "look"

# Interaction verbs surfaced in the Verb slot alongside the universal verbs.
_INTERACTION_VERBS: dict[str, str] = {
    VERB_PICK_UP: "Pick Up",
    VERB_EQUIP: "Equip",
    VERB_ACTIVATE: "Activate",
    VERB_LOOK: "Look",
    VERB_GIVE: "Give",
    VERB_USE: "Use",
    VERB_COMBINE: "Combine",
}

# Verbs that require a second noun (Target). Absent from this set = intransitive.
TRANSITIVE_VERBS: frozenset[str] = frozenset({VERB_GIVE, VERB_USE, VERB_COMBINE})


def is_transitive(verb: str) -> bool:
    """True when ``verb`` requires a Target noun."""
    return verb in TRANSITIVE_VERBS

# Noun ``source`` tags — finer than ``target_type`` (which can't tell an exit
# from the synthetic room, or a loose item from a carried one). Used to filter
# the Noun slot by the chosen Verb.
SOURCE_OBJECT = "object"
SOURCE_LOOSE_ITEM = "loose_item"
SOURCE_CARRIED_ITEM = "carried_item"
SOURCE_NPC = "npc"
SOURCE_MONSTER = "monster"
SOURCE_EXIT = "exit"
SOURCE_LOCKED_EXIT = "locked_exit"
SOURCE_SELF = "self"
SOURCE_ROOM = "room"
SOURCE_PARTY = "party"

# Exit statuses that block movement and should appear as Use targets.
_LOCKED_EXIT_STATUSES: frozenset[str] = frozenset({"locked", "blocked", "one_way"})

# Which noun sources each verb may target for the primary noun slot. Absent
# verbs (skill verbs) are unrestricted. Transitive verbs (give/use/combine)
# use a carried item as the primary noun; the Target slot holds the recipient.
_VERB_NOUN_SOURCES: dict[str, set[str]] = {
    VERB_MOVE: {SOURCE_EXIT, SOURCE_LOCKED_EXIT},
    VERB_PICK_UP: {SOURCE_LOOSE_ITEM},
    VERB_EQUIP: {SOURCE_CARRIED_ITEM},
    VERB_ACTIVATE: {SOURCE_OBJECT},
    VERB_GIVE: {SOURCE_CARRIED_ITEM},
    VERB_USE: {SOURCE_CARRIED_ITEM},
    VERB_COMBINE: {SOURCE_CARRIED_ITEM},
}

# Which noun sources are valid as the Target (second noun) for each transitive verb.
_VERB_TARGET_SOURCES: dict[str, set[str]] = {
    VERB_GIVE: {SOURCE_NPC, SOURCE_PARTY},
    VERB_COMBINE: {SOURCE_CARRIED_ITEM},
    VERB_USE: {SOURCE_OBJECT, SOURCE_MONSTER, SOURCE_NPC, SOURCE_SELF, SOURCE_PARTY, SOURCE_LOCKED_EXIT},
}


def noun_sources_for_verb(verb: str) -> set[str] | None:
    """The noun ``source`` tags ``verb`` may target, or ``None`` for unrestricted.

    Mutation verbs map to one source each; skill verbs (not in the table) return
    ``None`` and may target any noun.
    """
    return _VERB_NOUN_SOURCES.get(verb)


def target_sources_for_verb(verb: str) -> set[str] | None:
    """Source filter for the Target slot, or ``None`` if verb is intransitive."""
    return _VERB_TARGET_SOURCES.get(verb)


def verbs_for_noun(
    noun: "NounOption", all_verbs: Iterable["VerbOption"]
) -> list["VerbOption"]:
    """The verbs from ``all_verbs`` that may target ``noun`` — inverse of
    :func:`noun_sources_for_verb`.

    A verb applies when it is unrestricted (skill verbs, for which
    ``noun_sources_for_verb`` returns ``None``) or when ``noun.source`` is among
    the sources the verb accepts for its primary Noun slot. Input order is
    preserved. Used to populate the suggested-verbs chip row for the selected
    noun; verbs *not* returned are rendered disabled by the widget layer.
    """
    applicable: list[VerbOption] = []
    for verb in all_verbs:
        sources = noun_sources_for_verb(verb.verb)
        if sources is None or noun.source in sources:
            applicable.append(verb)
    return applicable


# Deterministic (no-roll) verbs: these resolve straight to a ``PlayerCommand``
# (or pure observation) rather than an action roll. ``use`` is conditional —
# use-on-self is a deterministic Consume, use-on-creature is a roll — so it is
# handled separately in :func:`action_preview`, not listed here.
_DETERMINISTIC_VERBS: frozenset[str] = frozenset(
    {VERB_MOVE, VERB_PICK_UP, VERB_EQUIP, VERB_ACTIVATE, VERB_GIVE, VERB_COMBINE, VERB_LOOK}
)

# Canonical memory types a deterministic verb could create, per the
# creation-trigger rules in MEMORY_SYSTEM_SPEC.md (move → a new room/`location`;
# activate/use/combine → `dungeon_state`; give → forms/damages a bond
# (`relationship`); look → a discovered clue (`event`)). Inventory shuffles
# (pick-up/equip) trigger no memory. Contested rolls use ``_CONTESTED_MEMORY_TAGS``.
_DETERMINISTIC_MEMORY_TAGS: dict[str, list[str]] = {
    VERB_MOVE: ["location"],
    VERB_ACTIVATE: ["dungeon_state"],
    VERB_USE: ["dungeon_state"],
    VERB_COMBINE: ["dungeon_state"],
    VERB_GIVE: ["relationship"],
    VERB_LOOK: ["event"],
    VERB_PICK_UP: [],
    VERB_EQUIP: [],
}

# Any action roll resolves a major action (`event`) and risks fallout on a
# failed/partial outcome (`fallout`).
_CONTESTED_MEMORY_TAGS: list[str] = ["event", "fallout"]

# Actor status that means a creature is a live threat (see Actor.status).
_LIVE_ACTOR_STATUS = "active"


@dataclass(frozen=True)
class ActionPreview:
    """A deterministic, engine-derived preview of an action Card (no LLM call).

    ``likely_roll`` is the action rating the verb resolves against (the verb
    name for skill verbs), or ``None`` for a deterministic action that shows
    "No roll — automatic". ``requires_roll`` drives the adaptive button
    (``ROLL`` vs ``DO``/``MOVE``/``LOOK``). ``risk`` is a templated line built
    from threats *present in the room* (``None`` when the room is calm).
    ``memory_tags`` are the canonical memory types this action could create.
    """

    likely_roll: str | None
    requires_roll: bool
    risk: str | None
    memory_tags: list[str] = field(default_factory=list)


def action_preview(
    card: "ActionCard", room_context: Mapping, actor: Mapping
) -> ActionPreview:
    """Build the deterministic Preview box for an action Card (spec §4.5).

    Pure and unit-testable — it reads only already-loaded state and **never**
    calls the LLM. ``requires_roll`` is true for skill/class verbs and for
    use-on-a-creature (use-on-self is a deterministic Consume). ``risk`` names
    the live threats in ``room_context`` (active creatures, disturbed objects).
    """
    verb = card.verb
    if verb == VERB_USE:
        requires_roll = card.target_id != actor.get("actor_id")
    else:
        requires_roll = verb not in _DETERMINISTIC_VERBS

    likely_roll = verb if requires_roll else None
    if requires_roll:
        memory_tags = list(_CONTESTED_MEMORY_TAGS)
    else:
        memory_tags = list(_DETERMINISTIC_MEMORY_TAGS.get(verb, []))

    return ActionPreview(
        likely_roll=likely_roll,
        requires_roll=requires_roll,
        risk=_templated_risk(room_context),
        memory_tags=memory_tags,
    )


def _templated_risk(room_context: Mapping) -> str | None:
    """Template a risk line from threats present in the room, or ``None``.

    Active creatures may stir; disturbed objects are named hazards. Forgiving of
    absent keys, matching :func:`available_nouns`.
    """
    threats: list[str] = []
    for monster in room_context.get("monsters", []):
        if monster.get("status", _LIVE_ACTOR_STATUS) == _LIVE_ACTOR_STATUS:
            threats.append(f"{monster['display_name']} may stir")
    for obj in room_context.get("objects", []):
        if obj.get("current_state") == "disturbed":
            threats.append(f"{obj['display_name']} is disturbed")
    return "; ".join(threats) if threats else None


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
    source: str = ""  # noun origin for verb filtering (see _NOUN_SOURCES)


@dataclass(frozen=True)
class AdverbOption:
    adverb: str
    label: str
    kind: str  # "universal" | "signature"


class ActionCard(BaseModel):
    """The player's structured action declaration: a Verb · Noun · [Target] · Adverb grammar.

    The input-dual of an ``LLMReactionProposal`` — the player declares an action
    through bounded, engine-offered choices that :func:`validate_card` checks
    against the sets the providers offered for the current room/actor.
    ``target_id`` is present only for transitive verbs (give, use, combine).
    """

    verb: str
    noun_id: str
    adverb: str
    target_id: str | None = None


@dataclass(frozen=True)
class CardOptions:
    """The engine-offered sets a Card is validated against (Slices 1–3 output)."""

    verbs: list[VerbOption] = field(default_factory=list)
    nouns: list[NounOption] = field(default_factory=list)
    adverbs: list[AdverbOption] = field(default_factory=list)
    targets: list[NounOption] = field(default_factory=list)


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
    if is_transitive(card.verb):
        if card.target_id is None:
            return CardError(field="target", reason=f"Transitive verb requires a Target: {card.verb}")
        if card.target_id not in {n.noun_id for n in options.targets}:
            return CardError(field="target", reason=f"Target not offered: {card.target_id}")
    elif card.target_id is not None:
        return CardError(field="target", reason=f"Intransitive verb may not have a Target: {card.verb}")
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
                source=SOURCE_OBJECT,
            )
        )
    for item in room_context.get("loose_items", []):
        options.append(
            NounOption(
                noun_id=item["item_id"],
                label=item["display_name"],
                target_type="item",
                slug=item["slug"],
                source=SOURCE_LOOSE_ITEM,
            )
        )
    for item in actor.get("carried_items", []):
        options.append(
            NounOption(
                noun_id=item["item_id"],
                label=item["display_name"],
                target_type="item",
                slug=item["slug"],
                source=SOURCE_CARRIED_ITEM,
            )
        )
    for npc in room_context.get("npcs", []):
        options.append(
            NounOption(
                noun_id=npc["actor_id"], label=npc["display_name"],
                target_type="npc", source=SOURCE_NPC,
            )
        )
    acting_id = actor.get("actor_id")
    for pc in room_context.get("party", []):
        if pc["actor_id"] != acting_id:
            options.append(
                NounOption(
                    noun_id=pc["actor_id"], label=pc["display_name"],
                    target_type="npc", source=SOURCE_PARTY,
                )
            )
    for monster in room_context.get("monsters", []):
        options.append(
            NounOption(
                noun_id=monster["actor_id"], label=monster["display_name"],
                target_type="monster", source=SOURCE_MONSTER,
            )
        )
    for ext in room_context.get("exits", []):
        is_locked = (
            ext.get("status") in _LOCKED_EXIT_STATUSES
            or bool(ext.get("requires_item_slug"))
        )
        options.append(
            NounOption(
                noun_id=ext["exit_id"], label=ext["label"],
                target_type="room",
                source=SOURCE_LOCKED_EXIT if is_locked else SOURCE_EXIT,
            )
        )
    options.append(
        NounOption(
            noun_id=actor["actor_id"], label=actor["display_name"],
            target_type="self", source=SOURCE_SELF,
        )
    )
    room_id = room_context.get("room_id")
    if room_id is not None:
        options.append(
            NounOption(
                noun_id=room_id, label="This room",
                target_type="room", source=SOURCE_ROOM,
            )
        )
    return options
