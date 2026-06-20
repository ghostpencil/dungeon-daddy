from dungeon_daddy.rpg.action_options import (
    NounOption,
    VerbOption,
    available_nouns,
    available_verbs,
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
    assert {v.verb for v in verbs} == _UNIVERSAL
    assert all(v.kind == "universal" for v in verbs)


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
    nouns = _nouns({"objects": [{"slug": "iron-chest", "display_name": "Iron Chest"}]})
    assert NounOption(noun_id="iron-chest", label="Iron Chest", target_type="object") in nouns


def test_loose_item_becomes_item_noun():
    nouns = _nouns({"loose_items": [{"slug": "gold-coin", "display_name": "Gold Coin"}]})
    assert NounOption(noun_id="gold-coin", label="Gold Coin", target_type="item") in nouns


def test_carried_item_becomes_item_noun():
    actor = {**_ACTOR, "carried_items": [{"slug": "dagger", "display_name": "Dagger"}]}
    nouns = _nouns({}, actor)
    assert NounOption(noun_id="dagger", label="Dagger", target_type="item") in nouns


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
