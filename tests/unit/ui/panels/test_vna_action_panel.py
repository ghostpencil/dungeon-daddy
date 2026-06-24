from __future__ import annotations

from dungeon_daddy.rpg.models import ActorAbility


def _panel():
    from dungeon_daddy.ui.panels.vna_action_panel import VnaActionPanel
    return VnaActionPanel()


def _room_context(**kw) -> dict:
    ctx = {
        "room_id": "room-1",
        "objects": [],
        "loose_items": [],
        "npcs": [],
        "monsters": [],
        "exits": [],
    }
    ctx.update(kw)
    return ctx


def _actor(**kw) -> dict:
    a = {"actor_id": "actor-1", "display_name": "Elara", "carried_items": []}
    a.update(kw)
    return a


# ---------------------------------------------------------------------------
# Tracer bullet — set_context populates verbs and defaults the verb selection
# ---------------------------------------------------------------------------

class TestSetContextVerbs:
    def test_verbs_populated_from_provider(self):
        panel = _panel()
        panel.set_context(
            actor_abilities=[],
            room_context=_room_context(),
            actor=_actor(),
            playbook_slug="fighter",
            world_flags=[],
        )
        # 9 universal verbs are always offered.
        assert "fight" in {v.verb for v in panel._verbs}
        assert "move" in {v.verb for v in panel._verbs}

    def test_default_verb_is_first(self):
        panel = _panel()
        panel.set_context(
            actor_abilities=[],
            room_context=_room_context(),
            actor=_actor(),
            playbook_slug="fighter",
            world_flags=[],
        )
        assert panel._verb == panel._verbs[0].verb


# ---------------------------------------------------------------------------
# Noun population — providers feed the noun slot; synthetic self/room present
# ---------------------------------------------------------------------------

class TestSetContextNouns:
    def test_nouns_include_synthetic_self_and_room(self):
        panel = _panel()
        panel.set_context(
            actor_abilities=[],
            room_context=_room_context(),
            actor=_actor(),
            playbook_slug="fighter",
            world_flags=[],
        )
        target_types = {n.target_type for n in panel._nouns}
        assert "self" in target_types
        assert "room" in target_types

    def test_default_noun_is_first(self):
        panel = _panel()
        panel.set_context(
            actor_abilities=[],
            room_context=_room_context(
                monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}]
            ),
            actor=_actor(),
            playbook_slug="fighter",
            world_flags=[],
        )
        assert panel._noun_id == panel._nouns[0].noun_id
        assert panel._noun_id == "mon-1"


# ---------------------------------------------------------------------------
# Acting-actor header — the panel reports whose action the Card builds
# ---------------------------------------------------------------------------

class TestActingActorName:
    def test_set_context_captures_actor_display_name(self):
        panel = _panel()
        panel.set_context(
            actor_abilities=[],
            room_context=_room_context(),
            actor=_actor(display_name="Borin"),
            playbook_slug="fighter",
            world_flags=[],
        )
        assert panel.acting_actor_name() == "Borin"

    def test_acting_actor_name_none_before_context(self):
        panel = _panel()
        assert panel.acting_actor_name() is None


# ---------------------------------------------------------------------------
# Reactive adverbs — selecting a noun recomputes the adverb list by target_type
# ---------------------------------------------------------------------------

class TestSelectNounRecomputesAdverbs:
    def _monster_panel(self):
        panel = _panel()
        panel.set_context(
            actor_abilities=[],
            room_context=_room_context(
                monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}]
            ),
            actor=_actor(),
            playbook_slug="fighter",
            world_flags=[],
        )
        return panel

    def test_default_monster_noun_offers_signature_adverb(self):
        panel = self._monster_panel()
        # 'brutally' is a fighter signature adverb gated to target_type=monster.
        assert "brutally" in {a.adverb for a in panel._adverbs}

    def test_selecting_self_drops_monster_only_adverb(self):
        panel = self._monster_panel()
        panel.select_noun("actor-1")  # the synthetic self target
        adverbs = {a.adverb for a in panel._adverbs}
        assert "brutally" not in adverbs
        assert "cautiously" in adverbs  # universal base remains

    def test_select_noun_resets_adverb_selection(self):
        panel = self._monster_panel()
        panel.select_noun("actor-1")
        assert panel._adverb == panel._adverbs[0].adverb


# ---------------------------------------------------------------------------
# build_card — assembles an ActionCard from the current selections
# ---------------------------------------------------------------------------

class TestBuildCard:
    def test_build_card_uses_current_selections(self):
        from dungeon_daddy.rpg.action_options import ActionCard

        panel = _panel()
        panel.set_context(
            actor_abilities=[],
            room_context=_room_context(
                monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}]
            ),
            actor=_actor(),
            playbook_slug="fighter",
            world_flags=[],
        )
        panel.select_verb("fight")
        panel.select_noun("mon-1")
        panel.select_adverb("brutally")
        card = panel.build_card()
        assert isinstance(card, ActionCard)
        assert (card.verb, card.noun_id, card.adverb) == ("fight", "mon-1", "brutally")

    def test_build_card_none_without_context(self):
        panel = _panel()
        assert panel.build_card() is None


# ---------------------------------------------------------------------------
# submit — validates against offered options, then fires the callback
# ---------------------------------------------------------------------------

class TestSubmit:
    def _monster_panel(self):
        panel = _panel()
        panel.set_context(
            actor_abilities=[],
            room_context=_room_context(
                monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}]
            ),
            actor=_actor(),
            playbook_slug="fighter",
            world_flags=[],
        )
        return panel

    def test_valid_submit_fires_callback_with_card(self):
        panel = self._monster_panel()
        panel.select_verb("fight")
        panel.select_noun("mon-1")
        panel.select_adverb("brutally")
        seen = []
        panel.set_submit_callback(lambda card: seen.append(card))
        panel.submit()
        assert len(seen) == 1
        assert (seen[0].verb, seen[0].noun_id, seen[0].adverb) == ("fight", "mon-1", "brutally")
        assert panel._last_error is None

    def test_out_of_bounds_adverb_blocks_submit(self):
        from dungeon_daddy.rpg.action_options import CardError

        panel = self._monster_panel()
        panel.select_verb("fight")
        panel.select_noun("mon-1")
        panel.select_adverb("teleportingly")  # never offered
        seen = []
        panel.set_submit_callback(lambda card: seen.append(card))
        panel.submit()
        assert seen == []
        assert isinstance(panel._last_error, CardError)
        assert panel._last_error.field == "adverb"


# ---------------------------------------------------------------------------
# Dropdown adapter — plain-string labels mapped back to slugs/ids
# ---------------------------------------------------------------------------

class TestDropdownLabels:
    def _panel(self):
        panel = _panel()
        panel.set_context(
            actor_abilities=[],
            room_context=_room_context(
                loose_items=[
                    {"item_id": "itm-9", "display_name": "Iron Key", "slug": "iron-key"}
                ],
            ),
            actor=_actor(),
            playbook_slug="fighter",
            world_flags=[],
        )
        return panel

    def test_labels_match_option_order(self):
        panel = self._panel()
        assert panel.verb_labels() == [v.label for v in panel._verbs]
        assert panel.noun_labels() == [n.label for n in panel._nouns]
        assert panel.adverb_labels() == [a.label for a in panel._adverbs]

    def test_select_verb_by_label_maps_to_slug(self):
        panel = self._panel()
        panel.select_verb_by_label("Fight")
        assert panel._verb == "fight"

    def test_select_noun_by_label_maps_to_id_and_recomputes_adverbs(self):
        panel = self._panel()
        panel.select_noun_by_label("Iron Key")
        assert panel._noun_id == "itm-9"

    def test_select_adverb_by_label_maps_to_slug(self):
        panel = self._panel()
        # universal 'Cautiously' label -> 'cautiously' slug
        panel.select_adverb_by_label("Cautiously")
        assert panel._adverb == "cautiously"

    def test_selected_labels_reflect_current_selection(self):
        panel = self._panel()
        # 'Study' is a skill verb, so the Iron Key loose item stays targetable.
        panel.select_verb_by_label("Study")
        panel.select_noun_by_label("Iron Key")
        panel.select_adverb_by_label("Cautiously")
        assert panel.selected_verb_label() == "Study"
        assert panel.selected_noun_label() == "Iron Key"
        assert panel.selected_adverb_label() == "Cautiously"


# ---------------------------------------------------------------------------
# Verb-filtered nouns — the Noun slot only offers what the Verb can target
# ---------------------------------------------------------------------------

class TestNounsFilteredByVerb:
    def _panel(self):
        panel = _panel()
        panel.set_context(
            actor_abilities=[],
            room_context=_room_context(
                loose_items=[
                    {"item_id": "itm-9", "display_name": "Iron Key", "slug": "iron-key"}
                ],
                exits=[{"exit_id": "e-north", "label": "Door North"}],
                monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}],
            ),
            actor=_actor(),
            playbook_slug="fighter",
            world_flags=[],
        )
        return panel

    def test_move_offers_only_exits(self):
        panel = self._panel()
        panel.select_verb("move")
        assert panel.noun_labels() == ["Door North"]

    def test_pick_up_offers_only_loose_items(self):
        panel = self._panel()
        panel.select_verb("pick-up")
        assert panel.noun_labels() == ["Iron Key"]

    def test_skill_verb_offers_all_nouns(self):
        panel = self._panel()
        panel.select_verb("fight")
        labels = panel.noun_labels()
        assert "Gnoll" in labels and "Iron Key" in labels and "Door North" in labels

    def test_select_verb_resets_noun_to_first_visible(self):
        panel = self._panel()
        panel.select_verb("move")
        assert panel._noun_id == "e-north"

    def test_verb_with_no_targets_clears_noun(self):
        panel = self._panel()
        panel.select_verb("equip")  # no carried items in context
        assert panel.noun_labels() == []
        assert panel._noun_id is None


# ---------------------------------------------------------------------------
# Slice 9 — Target slot for transitive verbs (give / use / combine)
# ---------------------------------------------------------------------------

def _transitive_panel():
    """Panel with an NPC, object, monster, two carried items, party PC, and a locked exit."""
    panel = _panel()
    panel.set_context(
        actor_abilities=[],
        room_context=_room_context(
            npcs=[{"actor_id": "npc-guard", "display_name": "Guard"}],
            objects=[{"object_id": "obj-chest", "display_name": "Chest",
                      "slug": "chest", "description": "A heavy chest."}],
            monsters=[{"actor_id": "mon-ghoul", "display_name": "Ghoul"}],
            party=[{"actor_id": "pc-2", "display_name": "Borin"}],
            exits=[
                {"exit_id": "exit-gate", "label": "Iron Gate", "status": "locked"},
                {"exit_id": "exit-north", "label": "North Arch", "status": "open"},
            ],
        ),
        actor=_actor(
            actor_id="pc-1",
            display_name="Elara",
            carried_items=[
                {"item_id": "itm-key", "display_name": "Brass Key", "slug": "brass-key"},
                {"item_id": "itm-vial", "display_name": "Healing Vial", "slug": "healing-vial"},
            ],
        ),
        playbook_slug="fighter",
        world_flags=[],
    )
    return panel


class TestTargetSlot:
    def test_intransitive_verb_has_empty_targets(self):
        panel = _transitive_panel()
        panel.select_verb("fight")
        assert panel._targets == []

    def test_give_verb_restricts_noun_to_carried_items(self):
        panel = _transitive_panel()
        panel.select_verb("give")
        noun_ids = {n.noun_id for n in panel._visible_nouns()}
        assert "itm-key" in noun_ids
        assert "npc-guard" not in noun_ids  # NPC is a target, not a noun

    def test_give_verb_surfaces_npcs_as_targets(self):
        panel = _transitive_panel()
        panel.select_verb("give")
        target_ids = {n.noun_id for n in panel._targets}
        assert "npc-guard" in target_ids

    def test_give_verb_surfaces_party_pcs_as_targets(self):
        panel = _transitive_panel()
        panel.select_verb("give")
        target_ids = {n.noun_id for n in panel._targets}
        assert "pc-2" in target_ids

    def test_give_verb_excludes_acting_actor_from_targets(self):
        panel = _transitive_panel()
        panel.select_verb("give")
        target_ids = {n.noun_id for n in panel._targets}
        assert "pc-1" not in target_ids  # acting actor is SOURCE_SELF, not a give target

    def test_combine_verb_targets_exclude_selected_noun(self):
        panel = _transitive_panel()
        panel.select_verb("combine")
        panel.select_noun("itm-key")
        target_ids = {n.noun_id for n in panel._targets}
        assert "itm-vial" in target_ids
        assert "itm-key" not in target_ids  # can't combine with itself

    def test_use_verb_surfaces_object_and_monster_as_targets(self):
        panel = _transitive_panel()
        panel.select_verb("use")
        panel.select_noun("itm-vial")
        target_ids = {n.noun_id for n in panel._targets}
        assert "obj-chest" in target_ids
        assert "mon-ghoul" in target_ids

    def test_use_verb_surfaces_self_as_target(self):
        panel = _transitive_panel()
        panel.select_verb("use")
        panel.select_noun("itm-vial")
        target_ids = {n.noun_id for n in panel._targets}
        assert "pc-1" in target_ids  # self is a valid "use on self" target

    def test_use_verb_surfaces_party_members_as_targets(self):
        panel = _transitive_panel()
        panel.select_verb("use")
        panel.select_noun("itm-vial")
        target_ids = {n.noun_id for n in panel._targets}
        assert "pc-2" in target_ids  # other party PCs are valid use targets

    def test_build_card_includes_target_id_for_transitive_verb(self):
        from dungeon_daddy.rpg.action_options import ActionCard

        panel = _transitive_panel()
        panel.select_verb("give")
        panel.select_noun("itm-key")
        panel.select_target("npc-guard")
        panel.select_adverb("cautiously")
        card = panel.build_card()
        assert isinstance(card, ActionCard)
        assert card.target_id == "npc-guard"

    def test_submit_transitive_verb_fires_callback_with_target(self):
        panel = _transitive_panel()
        panel.select_verb("use")
        panel.select_noun("itm-vial")
        panel.select_target("pc-1")
        panel.select_adverb("cautiously")
        seen = []
        panel.set_submit_callback(lambda card: seen.append(card))
        panel.submit()
        assert len(seen) == 1
        assert seen[0].target_id == "pc-1"

    def test_submit_transitive_verb_no_target_stores_error(self):
        from dungeon_daddy.rpg.action_options import CardError

        panel = _transitive_panel()
        panel.select_verb("give")
        panel.select_noun("itm-key")
        # _target_id is None (no target selected)
        panel._target_id = None
        panel.select_adverb("cautiously")
        seen = []
        panel.set_submit_callback(lambda card: seen.append(card))
        panel.submit()
        assert seen == []
        assert isinstance(panel._last_error, CardError)
        assert panel._last_error.field == "target"

    def test_target_labels_and_select_by_label(self):
        panel = _transitive_panel()
        panel.select_verb("give")
        panel.select_noun("itm-key")
        labels = panel.target_labels()
        assert "Guard" in labels
        panel.select_target_by_label("Guard")
        assert panel._target_id == "npc-guard"

    def test_use_verb_surfaces_locked_exit_as_target(self):
        panel = _transitive_panel()
        panel.select_verb("use")
        panel.select_noun("itm-key")
        target_ids = {n.noun_id for n in panel._targets}
        assert "exit-gate" in target_ids  # locked exit appears as Use target

    def test_use_verb_excludes_open_exit_from_targets(self):
        panel = _transitive_panel()
        panel.select_verb("use")
        panel.select_noun("itm-key")
        target_ids = {n.noun_id for n in panel._targets}
        assert "exit-north" not in target_ids  # open exit without key requirement is NOT a use target
