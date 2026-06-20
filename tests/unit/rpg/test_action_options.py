from dungeon_daddy.rpg.action_options import (
    ActionCard,
    AdverbOption,
    CardError,
    CardOptions,
    NounOption,
    VerbOption,
    available_adverbs,
    available_nouns,
    available_verbs,
    validate_card,
)
from dungeon_daddy.rpg.models import ActorAbility

_UNIVERSAL = {
    "fight",
    "move",
    "tinker",
    "study",
    "focus",
    "sway",
    "sense",
    "channel",
    "endure",
}


def _ability(slug, *, surfaces_as_verb, display_name=None):
    return ActorAbility(
        actor_id="a1",
        ability_slug=slug,
        display_name=display_name or slug.replace("-", " ").title(),
        description="",
        source="playbook_start",
        surfaces_as_verb=surfaces_as_verb,
    )


def test_available_verbs_includes_all_universal_verbs_with_no_abilities():
    verbs = available_verbs([])
    universal = {v.verb for v in verbs if v.kind == "universal"}
    assert universal == _UNIVERSAL


def test_available_verbs_includes_interaction_verbs():
    verbs = available_verbs([])
    interaction = {v.verb: v for v in verbs if v.kind == "interaction"}
    assert set(interaction) == {"pick-up", "equip", "activate"}
    assert interaction["pick-up"].label == "Pick Up"


def test_available_verbs_appends_class_verb_for_surfacing_ability():
    verbs = available_verbs([_ability("vanish", surfaces_as_verb=True, display_name="Vanish")])
    vanish = [v for v in verbs if v.verb == "vanish"]
    assert vanish == [VerbOption(verb="vanish", label="Vanish", kind="class")]


def test_available_verbs_excludes_non_surfacing_ability():
    verbs = available_verbs([_ability("iron-will", surfaces_as_verb=False)])
    assert all(v.verb != "iron-will" for v in verbs)


# --------------------------------------------------------------------------
# Noun provider (Slice 2)
# --------------------------------------------------------------------------

_ACTOR = {"actor_id": "actor:c1:mara", "display_name": "Mara"}


def _nouns(room_context, actor=_ACTOR):
    return available_nouns(room_context, actor)


def test_room_object_becomes_object_noun():
    nouns = _nouns({"objects": [
        {"object_id": "obj:c1:iron-chest", "slug": "iron-chest", "display_name": "Iron Chest"}
    ]})
    assert NounOption(
        noun_id="obj:c1:iron-chest", slug="iron-chest", label="Iron Chest", target_type="object"
    ) in nouns


def test_loose_item_becomes_item_noun():
    nouns = _nouns({"loose_items": [
        {"item_id": "item:c1:gold-coin", "slug": "gold-coin", "display_name": "Gold Coin"}
    ]})
    assert NounOption(
        noun_id="item:c1:gold-coin", slug="gold-coin", label="Gold Coin", target_type="item"
    ) in nouns


def test_carried_item_becomes_item_noun():
    actor = {**_ACTOR, "carried_items": [
        {"item_id": "item:c1:dagger", "slug": "dagger", "display_name": "Dagger"}
    ]}
    nouns = _nouns({}, actor)
    assert NounOption(
        noun_id="item:c1:dagger", slug="dagger", label="Dagger", target_type="item"
    ) in nouns


def test_npc_becomes_npc_noun():
    nouns = _nouns({"npcs": [{"actor_id": "actor:c1:warden", "display_name": "The Warden"}]})
    assert NounOption(noun_id="actor:c1:warden", label="The Warden", target_type="npc") in nouns


def test_monster_becomes_monster_noun():
    nouns = _nouns({"monsters": [{"actor_id": "actor:c1:ghoul", "display_name": "Pale Ghoul"}]})
    assert NounOption(noun_id="actor:c1:ghoul", label="Pale Ghoul", target_type="monster") in nouns


def test_exit_becomes_room_noun():
    nouns = _nouns({"exits": [{"exit_id": "exit:c1:north", "label": "North Door"}]})
    assert NounOption(noun_id="exit:c1:north", label="North Door", target_type="room") in nouns


def test_synthetic_self_and_room_always_present():
    nouns = _nouns({"room_id": "room:level-01:antechamber"})
    assert NounOption(noun_id="actor:c1:mara", label="Mara", target_type="self") in nouns
    assert NounOption(
        noun_id="room:level-01:antechamber", label="This room", target_type="room"
    ) in nouns


def test_self_present_even_without_room_context():
    nouns = _nouns({})
    assert any(n.target_type == "self" for n in nouns)
    assert all(n.target_type != "room" for n in nouns)


def test_empty_context_yields_only_self():
    nouns = _nouns({})
    assert nouns == [NounOption(noun_id="actor:c1:mara", label="Mara", target_type="self")]


# --------------------------------------------------------------------------
# Adverb provider (Slice 3)
# --------------------------------------------------------------------------

# "fighter" playbook signature adverbs (data/playbooks.json):
#   recklessly -> [monster, object], brutally -> [monster],
#   with-discipline -> [monster, npc]
_BASE_UNIVERSAL_ADVERBS = {"cautiously", "quickly", "boldly"}


def test_universal_base_adverbs_always_present():
    advs = available_adverbs("fighter", target_type="object", world_flags=set())
    universal = {a.adverb for a in advs if a.kind == "universal"}
    assert _BASE_UNIVERSAL_ADVERBS <= universal
    assert all(a.kind == "universal" for a in advs if a.adverb in _BASE_UNIVERSAL_ADVERBS)


def test_conditional_universal_adverb_absent_without_world_flag():
    advs = available_adverbs("fighter", target_type="object", world_flags=set())
    assert all(a.adverb != "stealthily" for a in advs)


def test_conditional_universal_adverb_surfaces_with_world_flag():
    advs = available_adverbs("fighter", target_type="object", world_flags={"can_sense"})
    assert AdverbOption(adverb="stealthily", label="Stealthily", kind="universal") in advs


def test_signature_adverb_surfaces_for_matching_target_type():
    # fighter's "brutally" targets [monster]
    advs = available_adverbs("fighter", target_type="monster", world_flags=set())
    assert AdverbOption(adverb="brutally", label="Brutally", kind="signature") in advs


def test_signature_adverb_absent_for_non_matching_target_type():
    # fighter's "brutally" targets [monster] only — not object
    advs = available_adverbs("fighter", target_type="object", world_flags=set())
    assert all(a.adverb != "brutally" for a in advs)


def test_multiword_signature_adverb_label_is_title_cased():
    # fighter's "with-discipline" targets [monster, npc]
    advs = available_adverbs("fighter", target_type="npc", world_flags=set())
    assert AdverbOption(
        adverb="with-discipline", label="With Discipline", kind="signature"
    ) in advs


def test_adverb_surfaced_both_universally_and_as_signature_is_not_duplicated():
    # fighter's "recklessly" is a signature adverb (monster/object) AND a
    # universal adverb gated by the armed-trap world flag — surface it once.
    advs = available_adverbs(
        "fighter", target_type="monster", world_flags={"armed_trap"}
    )
    recklessly = [a for a in advs if a.adverb == "recklessly"]
    assert recklessly == [
        AdverbOption(adverb="recklessly", label="Recklessly", kind="universal")
    ]


# --------------------------------------------------------------------------
# Card model + validation (Slice 4)
# --------------------------------------------------------------------------

_OPTIONS = CardOptions(
    verbs=[
        VerbOption(verb="fight", label="Fight", kind="universal"),
        VerbOption(verb="vanish", label="Vanish", kind="class"),
    ],
    nouns=[
        NounOption(noun_id="actor:c1:ghoul", label="Pale Ghoul", target_type="monster"),
    ],
    adverbs=[
        AdverbOption(adverb="boldly", label="Boldly", kind="universal"),
    ],
)


def test_action_card_constructs_with_verb_noun_adverb():
    card = ActionCard(verb="fight", noun_id="actor:c1:ghoul", adverb="boldly")
    assert (card.verb, card.noun_id, card.adverb) == ("fight", "actor:c1:ghoul", "boldly")


def test_validate_card_accepts_card_within_offered_sets():
    card = ActionCard(verb="fight", noun_id="actor:c1:ghoul", adverb="boldly")
    assert validate_card(card, _OPTIONS) is None


def test_validate_card_rejects_verb_not_offered():
    card = ActionCard(verb="teleport", noun_id="actor:c1:ghoul", adverb="boldly")
    err = validate_card(card, _OPTIONS)
    assert isinstance(err, CardError) and err.field == "verb"


def test_validate_card_rejects_noun_not_offered():
    card = ActionCard(verb="fight", noun_id="actor:c1:nobody", adverb="boldly")
    err = validate_card(card, _OPTIONS)
    assert isinstance(err, CardError) and err.field == "noun"


def test_validate_card_rejects_adverb_not_offered():
    card = ActionCard(verb="fight", noun_id="actor:c1:ghoul", adverb="sneakily")
    err = validate_card(card, _OPTIONS)
    assert isinstance(err, CardError) and err.field == "adverb"
