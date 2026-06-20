from dungeon_daddy.rpg.action_options import VerbOption, available_verbs
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
