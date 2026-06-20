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
        panel.select_verb_by_label("Move")
        panel.select_noun_by_label("Iron Key")
        panel.select_adverb_by_label("Cautiously")
        assert panel.selected_verb_label() == "Move"
        assert panel.selected_noun_label() == "Iron Key"
        assert panel.selected_adverb_label() == "Cautiously"
