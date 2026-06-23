"""Play-mode Verb · Noun · Adverb action panel (Phase 50 Slice 7).

The pure-logic core of the VNA Card panel: it holds the option sets the Slice
1–3 providers (:mod:`dungeon_daddy.rpg.action_options`) offer for the current
room/actor, tracks the player's Verb/Noun/Adverb selections, and builds a
validated :class:`ActionCard` on submit. Because the adverb pool depends on the
*chosen noun's* ``target_type`` (plus world flags and the actor's playbook),
selecting a noun recomputes the adverb list.

Dropdown widgets present plain strings, so this panel also maps each slot's
human-readable label back to the slug/id the engine needs. The Arcade
``UIDropdown`` widget build is deferred to the ui-test harness (Slice 8); this
module stays Arcade-free so it is unit-testable without a display context.
"""
from __future__ import annotations

from typing import Callable, Collection, Iterable, Mapping

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
    noun_sources_for_verb,
    validate_card,
)
from dungeon_daddy.rpg.models import ActorAbility

# Vertical band reserved at the top of the panel for the acting-actor header,
# above the Verb/Noun/Adverb rows (shared by setup_widget and draw).
_HEADER_H = 22


class VnaActionPanel:
    def __init__(self) -> None:
        self._verbs: list[VerbOption] = []
        self._nouns: list[NounOption] = []
        self._adverbs: list[AdverbOption] = []
        self._verb: str | None = None
        self._noun_id: str | None = None
        self._adverb: str | None = None
        self._playbook_slug: str | None = None
        self._actor_name: str | None = None
        self._world_flags: list[str] = []
        self._library: object | None = None
        self._on_submit: Callable[[ActionCard], None] | None = None
        self._last_error: CardError | None = None
        # Arcade widget state (populated by setup_widget; see Slice 8 wiring).
        self._all_widgets: list = []
        self._widget_params: tuple | None = None

    # ------------------------------------------------------------------
    # Context / option population
    # ------------------------------------------------------------------

    def set_context(
        self,
        *,
        actor_abilities: Iterable[ActorAbility],
        room_context: Mapping,
        actor: Mapping,
        playbook_slug: str,
        world_flags: Collection[str],
        library: object | None = None,
    ) -> None:
        """Populate the offered Verb/Noun/Adverb sets from the providers.

        Defaults each slot to its first option; the adverb list is computed
        for the default noun's ``target_type``.
        """
        self._verbs = available_verbs(actor_abilities)
        self._nouns = available_nouns(room_context, actor)
        self._actor_name = actor.get("display_name")
        self._playbook_slug = playbook_slug
        self._world_flags = list(world_flags)
        self._library = library
        self._verb = self._verbs[0].verb if self._verbs else None
        self._reset_noun_for_verb()

    def select_verb(self, verb: str) -> None:
        """Select a verb and refilter the Noun slot to what that verb can target."""
        self._verb = verb
        self._reset_noun_for_verb()

    def _visible_nouns(self) -> list[NounOption]:
        """The nouns the current verb may target (all of them for skill verbs)."""
        if self._verb is None:
            return list(self._nouns)
        allowed = noun_sources_for_verb(self._verb)
        if allowed is None:
            return list(self._nouns)
        return [n for n in self._nouns if n.source in allowed]

    def _reset_noun_for_verb(self) -> None:
        """Default the Noun (and its dependent Adverb list) to the verb's first option."""
        visible = self._visible_nouns()
        self._noun_id = visible[0].noun_id if visible else None
        self._refresh_adverbs()

    def select_noun(self, noun_id: str) -> None:
        """Select a noun and recompute the adverb list for its ``target_type``."""
        self._noun_id = noun_id
        self._refresh_adverbs()

    def select_adverb(self, adverb: str) -> None:
        self._adverb = adverb

    def acting_actor_name(self) -> str | None:
        """Display name of the actor whose action this Card builds."""
        return self._actor_name

    def build_card(self) -> ActionCard | None:
        """Assemble an :class:`ActionCard` from the current selections.

        Returns ``None`` when any slot is unset (e.g. before ``set_context``).
        """
        if self._verb is None or self._noun_id is None or self._adverb is None:
            return None
        return ActionCard(verb=self._verb, noun_id=self._noun_id, adverb=self._adverb)

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    def set_submit_callback(self, fn: Callable[[ActionCard], None]) -> None:
        self._on_submit = fn

    def submit(self) -> None:
        """Validate the current Card against the offered options, then dispatch.

        On a valid Card the ``on_submit`` callback receives it and
        ``_last_error`` is cleared; an out-of-bounds slot stores the
        :class:`CardError` and the callback does not fire (engine-bounded,
        mirroring proposal validation).
        """
        card = self.build_card()
        if card is None:
            return
        error = validate_card(card, self._card_options())
        if error is not None:
            self._last_error = error
            return
        self._last_error = None
        if self._on_submit is not None:
            self._on_submit(card)

    def _card_options(self) -> CardOptions:
        return CardOptions(verbs=self._verbs, nouns=self._nouns, adverbs=self._adverbs)

    # ------------------------------------------------------------------
    # Dropdown adapter — UIDropdown options are plain strings, so map each
    # slot's label back to the slug/id the engine needs. (Slice 8 widget build.)
    # ------------------------------------------------------------------

    def verb_labels(self) -> list[str]:
        return [v.label for v in self._verbs]

    def noun_labels(self) -> list[str]:
        return [n.label for n in self._visible_nouns()]

    def adverb_labels(self) -> list[str]:
        return [a.label for a in self._adverbs]

    def select_verb_by_label(self, label: str) -> None:
        for v in self._verbs:
            if v.label == label:
                self.select_verb(v.verb)
                return

    def select_noun_by_label(self, label: str) -> None:
        for n in self._visible_nouns():
            if n.label == label:
                self.select_noun(n.noun_id)
                return

    def select_adverb_by_label(self, label: str) -> None:
        for a in self._adverbs:
            if a.label == label:
                self.select_adverb(a.adverb)
                return

    def selected_verb_label(self) -> str | None:
        return next((v.label for v in self._verbs if v.verb == self._verb), None)

    def selected_noun_label(self) -> str | None:
        return next((n.label for n in self._visible_nouns() if n.noun_id == self._noun_id), None)

    def selected_adverb_label(self) -> str | None:
        return next((a.label for a in self._adverbs if a.adverb == self._adverb), None)

    def noun_label_for(self, noun_id: str) -> str | None:
        """Human-readable label for an offered noun id (for narration/messages)."""
        return next((n.label for n in self._nouns if n.noun_id == noun_id), None)

    def _selected_noun(self) -> NounOption | None:
        return next((n for n in self._nouns if n.noun_id == self._noun_id), None)

    def _refresh_adverbs(self) -> None:
        noun = self._selected_noun()
        if noun is None or self._playbook_slug is None:
            self._adverbs = []
            self._adverb = None
            return
        self._adverbs = available_adverbs(
            self._playbook_slug,
            target_type=noun.target_type,
            world_flags=self._world_flags,
            library=self._library,
        )
        self._adverb = self._adverbs[0].adverb if self._adverbs else None

    # ------------------------------------------------------------------
    # Arcade widget build (display required; exercised via the ui-test harness)
    # ------------------------------------------------------------------

    def setup_widget(
        self, manager: object | None, x: float, y: float, w: float, h: float
    ) -> None:
        """Build the three V·N·A dropdowns plus a SUBMIT button.

        Dropdown options are plain label strings; ``on_change`` maps each back to
        its slug/id via the ``select_*_by_label`` adapter. Changing the Noun
        recomputes the adverb pool, so the panel rebuilds itself to refresh the
        Adverb dropdown's options.
        """
        if manager is None:
            return
        import arcade.gui
        from dungeon_daddy.ui.theme import (
            BG_2, BG_3, BG_HI, FONT_UI, INK_1, INK_4, LINE, LINE_HI, PAD_MD, TEAL,
        )

        self._widget_params = (manager, x, y, w, h)
        self.teardown_widget(manager)

        field_w = int(w - PAD_MD * 2)
        field_h = 30
        row_gap = 18 + field_h  # label row + dropdown
        cur_y = y + h - PAD_MD - _HEADER_H - field_h  # leave room for actor header

        def _dropdown(options: list[str], default: str | None) -> object:
            nonlocal cur_y
            dd = arcade.gui.UIDropdown(
                x=int(x + PAD_MD), y=int(cur_y),
                width=field_w, height=field_h,
                default=default, options=options or [None],
            )
            manager.add(dd)  # type: ignore[union-attr]
            self._all_widgets.append(dd)
            cur_y -= row_gap
            return dd

        verb_dd = _dropdown(self.verb_labels(), self.selected_verb_label())
        noun_dd = _dropdown(self.noun_labels(), self.selected_noun_label())
        adverb_dd = _dropdown(self.adverb_labels(), self.selected_adverb_label())

        @verb_dd.event("on_change")
        def _on_verb(event) -> None:
            if event.new_value is not None:
                self.select_verb_by_label(event.new_value)
                # Noun options are verb-dependent — rebuild so the Noun and
                # Adverb dropdowns reflect the new verb's targets.
                if self._widget_params:
                    self.setup_widget(*self._widget_params)

        @noun_dd.event("on_change")
        def _on_noun(event) -> None:
            if event.new_value is not None:
                self.select_noun_by_label(event.new_value)
                # Adverb options changed — rebuild so the dropdown reflects them.
                if self._widget_params:
                    self.setup_widget(*self._widget_params)

        @adverb_dd.event("on_change")
        def _on_adverb(event) -> None:
            if event.new_value is not None:
                self.select_adverb_by_label(event.new_value)

        submit_h = 28
        submit_btn = arcade.gui.UIFlatButton(
            x=int(x + PAD_MD), y=int(cur_y - submit_h),
            width=field_w, height=submit_h,
            text="SUBMIT",
            style={
                "normal": arcade.gui.UIFlatButton.UIStyle(
                    font_size=8, font_name=FONT_UI,
                    font_color=(*TEAL, 255), bg=(*BG_2, 255),
                    border=(*LINE, 255), border_width=1,
                ),
                "hover": arcade.gui.UIFlatButton.UIStyle(
                    font_size=8, font_name=FONT_UI,
                    font_color=(*INK_1, 255), bg=(*BG_3, 255),
                    border=(*LINE_HI, 255), border_width=1,
                ),
                "press": arcade.gui.UIFlatButton.UIStyle(
                    font_size=8, font_name=FONT_UI,
                    font_color=(*TEAL, 255), bg=(*BG_HI, 255),
                    border=(*TEAL, 255), border_width=1,
                ),
                "disabled": arcade.gui.UIFlatButton.UIStyle(
                    font_size=8, font_name=FONT_UI,
                    font_color=(*INK_4, 255), bg=(*BG_2, 255),
                    border=(*LINE, 255), border_width=1,
                ),
            },
        )

        @submit_btn.event
        def on_click(event) -> None:
            self.submit()

        manager.add(submit_btn)  # type: ignore[union-attr]
        self._all_widgets.append(submit_btn)

    def teardown_widget(self, manager: object | None) -> None:
        if manager is None:
            return
        for widget in self._all_widgets:
            try:
                manager.remove(widget)  # type: ignore[union-attr]
            except Exception:
                pass
        self._all_widgets.clear()

    def draw(self, x: float, y: float, w: float, h: float) -> None:
        import arcade
        from dungeon_daddy.ui.theme import (
            BG_1, FONT_UI, INK_4, PAD_MD, TEAL, TEXT_SM,
        )

        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_1)
        # Acting-actor header — names whose action this Card builds.
        header = f"ACTING AS: {self._actor_name}" if self._actor_name else "ACTING AS: —"
        arcade.draw_text(
            header, x + PAD_MD, y + h - PAD_MD,
            TEAL, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top", bold=True,
        )
        field_h = 30
        row_gap = 18 + field_h
        cur_y = y + h - PAD_MD - _HEADER_H
        for label in ("Verb", "Noun", "Adverb"):
            arcade.draw_text(
                label, x + PAD_MD, cur_y,
                INK_4, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
            )
            cur_y -= row_gap
