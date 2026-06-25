"""In-chat Action Builder (Phase 50.6 Slice 4).

Relocates the Verb·Noun·Adverb action surface out of the right RPG side panel
and into the left chat column, directly below the actor mini-card. It **reuses
:class:`VnaActionPanel`'s Arcade-free logic core verbatim** — every option list,
selection, and the ``submit`` path come from the panel — and adds only a
presentational layer: a wrapped command sentence whose slots are custom-drawn
chips that open a popup selection list on click (per Phase 50 feedback the slots
must support fast selection from a large vocabulary, not a cycle picker).

This module stays unit-testable: drawing is mocked in tests and exercised for
real via the ui-test harness. The slot/popup hit-testing follows the same
rect-list pattern as :mod:`chat_panel`.
"""
from __future__ import annotations

from dungeon_daddy.rpg.action_options import VERB_LOOK, VERB_MOVE, verbs_for_noun
from dungeon_daddy.ui.panels.vna_action_panel import VnaActionPanel

# Slot kinds, in the order they appear in the command sentence. ``target`` is
# present only for transitive verbs (Phase 50.5 ``Verb · Noun · [Target] · Adverb``).
_KIND_VERB = "verb"
_KIND_NOUN = "noun"
_KIND_TARGET = "target"
_KIND_ADVERB = "adverb"

# Connector word drawn before the Target slot, per transitive verb family
# (Phase 50.5 grammar): "use X on the Y", "give X to Y".
_TARGET_CONNECTORS = {"use": "on the", "give": "to"}
_DEFAULT_TARGET_CONNECTOR = "with"

# Connector word drawn before the Noun slot. Most verbs read "<verb> the <noun>";
# a few read better with a preposition (e.g. "look at the symbols").
_NOUN_CONNECTORS = {"look": "at the"}
_DEFAULT_NOUN_CONNECTOR = "the"

# Placeholder text drawn (dim, INK_4) in a slot that has no current selection, so
# an empty slot reads as a fill-in-the-blank prompt rather than a value (CP-3).
_SLOT_PLACEHOLDERS = {
    _KIND_VERB: "verb",
    _KIND_NOUN: "noun",
    _KIND_TARGET: "target",
    _KIND_ADVERB: "how",
}


class InChatActionBuilder:
    def __init__(self, panel: VnaActionPanel) -> None:
        self._panel = panel
        # The slot currently showing its popup list, or ``None`` when closed.
        self._open_slot: str | None = None
        # Hit rects populated by draw(): slots, the open popup's rows, the button,
        # and the suggested-verb chips (carry a label + enabled flag).
        self._slot_rects: list[tuple[float, float, float, float, str]] = []
        self._popup_row_rects: list[tuple[float, float, float, float, str]] = []
        self._button_rect: tuple[float, float, float, float] | None = None
        self._suggested_rects: list[
            tuple[float, float, float, float, str, bool]
        ] = []

    # ------------------------------------------------------------------
    # Command sentence model (drawn + hit-tested)
    # ------------------------------------------------------------------

    def slots(self) -> list[tuple[str, str | None]]:
        """Ordered ``(kind, label)`` slots reflecting the panel's selection.

        The Target slot is included only when the chosen verb is transitive and
        offers at least one target.
        """
        result: list[tuple[str, str | None]] = [
            (_KIND_VERB, self._panel.selected_verb_label()),
            (_KIND_NOUN, self._panel.selected_noun_label()),
        ]
        if self._panel.target_labels():
            result.append((_KIND_TARGET, self._panel.selected_target_label()))
        result.append((_KIND_ADVERB, self._panel.selected_adverb_label()))
        return result

    def slot_is_unset(self, kind: str) -> bool:
        """True when ``kind`` has no current selection.

        An unset slot is drawn as a dim ``INK_4`` placeholder (its role word) so
        it reads as "needs a choice" rather than as a value (CP-3).
        """
        if kind == _KIND_VERB:
            return self._panel.selected_verb_label() is None
        if kind == _KIND_NOUN:
            return self._panel.selected_noun_label() is None
        if kind == _KIND_TARGET:
            return self._panel.selected_target_label() is None
        if kind == _KIND_ADVERB:
            return self._panel.selected_adverb_label() is None
        return False

    # ------------------------------------------------------------------
    # Interaction — slot chips open a popup list (custom combobox)
    # ------------------------------------------------------------------

    def popup_labels(self) -> list[str]:
        """Selectable labels for the currently-open slot (empty when closed)."""
        return self._labels_for(self._open_slot)

    def _labels_for(self, kind: str | None) -> list[str]:
        if kind == _KIND_VERB:
            return self._panel.verb_labels()
        if kind == _KIND_NOUN:
            return self._panel.noun_labels()
        if kind == _KIND_TARGET:
            return self._panel.target_labels()
        if kind == _KIND_ADVERB:
            return self._panel.adverb_labels()
        return []

    # ------------------------------------------------------------------
    # Suggested-verbs row — quick-pick chips filtered by the selected noun
    # ------------------------------------------------------------------

    # Max suggested chips drawn (the ~5 "by relevance" cap is applied in draw();
    # the model below returns the full ranked list so disabled tags stay testable).
    _SUGGESTED_CAP = 5

    def suggested_verbs(self) -> list[tuple[str, bool]]:
        """Relevance-ranked ``(label, enabled)`` verb chips for the selected noun.

        Verbs that may target the current noun (:func:`verbs_for_noun`) are
        enabled and ranked first; the remaining offered verbs are tagged disabled
        so the widget can grey them as hints. Clicking an enabled chip sets the
        Verb slot (same effect as the verb popup); ``draw`` shows the first
        :attr:`_SUGGESTED_CAP`.
        """
        verbs = self._panel.verb_options()
        noun = self._panel.selected_noun_option()
        if noun is None:
            return [(v.label, True) for v in verbs]
        applicable = verbs_for_noun(noun, verbs)
        enabled = {v.verb for v in applicable}
        disabled = [v for v in verbs if v.verb not in enabled]
        return (
            [(v.label, True) for v in applicable]
            + [(v.label, False) for v in disabled]
        )

    def _suggested_is_active(self, label: str) -> bool:
        """True when a suggested chip matches the current verb selection.

        The active chip is drawn *filled* (vs the outlined slots and other
        suggestions) to show which verb is current and to distinguish the
        quick-pick row from the verb dropdown slot (CP-4, spec §8 "selected =
        filled").
        """
        return label == self._panel.selected_verb_label()

    def _select(self, kind: str, label: str) -> None:
        if kind == _KIND_VERB:
            self._panel.select_verb_by_label(label)
        elif kind == _KIND_NOUN:
            self._panel.select_noun_by_label(label)
        elif kind == _KIND_TARGET:
            self._panel.select_target_by_label(label)
        elif kind == _KIND_ADVERB:
            self._panel.select_adverb_by_label(label)

    def on_mouse_press(self, x: float, y: float) -> bool:
        """Route a click. Returns ``True`` when the builder consumed it.

        An open popup takes priority (it is drawn on top): a click on one of its
        rows selects that option and closes the popup.
        """
        if self._open_slot is not None:
            for left, bottom, w, h, label in self._popup_row_rects:
                if left <= x < left + w and bottom <= y < bottom + h:
                    self._select(self._open_slot, label)
                    self._open_slot = None
                    return True
            # A click anywhere else while a popup is open dismisses it.
            self._open_slot = None
            return True
        for left, bottom, w, h, label, enabled in self._suggested_rects:
            if left <= x < left + w and bottom <= y < bottom + h:
                # Enabled chip sets the Verb slot; a disabled chip is a no-op
                # but still consumes the click (it sits inside the band).
                if enabled:
                    self._panel.select_verb_by_label(label)
                return True
        for left, bottom, w, h, kind in self._slot_rects:
            if left <= x < left + w and bottom <= y < bottom + h:
                self._open_slot = kind
                return True
        if self._button_rect is not None:
            left, bottom, w, h = self._button_rect
            if left <= x < left + w and bottom <= y < bottom + h:
                self._panel.submit()
                return True
        return False

    # Deterministic verbs that read calmer than a generic "DO" (spec §4.6).
    _DETERMINISTIC_BUTTON_LABELS = {VERB_MOVE: "MOVE", VERB_LOOK: "LOOK"}

    def button_label(self) -> str:
        """Adaptive action-button label (spec §4.6).

        ``ROLL`` when the action is contested/uncertain (or no preview yet);
        otherwise the deterministic ``MOVE`` / ``LOOK`` for those verbs, else
        ``DO``. Derived from the deterministic :meth:`VnaActionPanel.preview`.
        """
        preview = self._panel.preview()
        if preview is None or preview.requires_roll:
            return "ROLL"
        card = self._panel.build_card()
        verb = card.verb if card is not None else None
        return self._DETERMINISTIC_BUTTON_LABELS.get(verb, "DO")

    def preview_lines(self) -> list[str]:
        """Display lines for the deterministic Preview inset (spec §4.5).

        Empty when no Card can be built. The first line is the likely roll (or
        "No roll — automatic"); a Risk line follows only when the room holds a
        live threat; a Memory line lists the canonical memory types the action
        could create.
        """
        preview = self._panel.preview()
        if preview is None:
            return []
        lines: list[str] = []
        if preview.likely_roll:
            lines.append(f"Likely roll: {preview.likely_roll.upper()}")
        else:
            lines.append("No roll — automatic")
        if preview.risk:
            lines.append(f"Risk: {preview.risk}")
        if preview.memory_tags:
            lines.append("Memory: " + ", ".join(preview.memory_tags))
        return lines

    @staticmethod
    def _wrap_units(
        widths: list[float],
        avail: float,
        gap: float,
        glued: list[bool],
    ) -> list[int]:
        """Greedy line assignment for the command sentence (CP-1).

        ``glued[i] is True`` keeps unit ``i`` on the same line as unit ``i-1`` —
        used to bind a noun/target connector to the slot it precedes so a wrap
        never orphans the connector. Units are grouped by their glue chains and
        each *group* is placed greedily; a group that would overflow ``avail``
        starts a new line as a unit. Returns the 0-based line index per unit.
        """
        groups: list[list[int]] = []
        for i in range(len(widths)):
            if i > 0 and glued[i]:
                groups[-1].append(i)
            else:
                groups.append([i])
        lines = [0] * len(widths)
        line = 0
        cur_x = 0.0
        for group in groups:
            group_w = sum(widths[i] for i in group) + gap * (len(group) - 1)
            if cur_x > 0 and cur_x + group_w > avail:
                line += 1
                cur_x = 0.0
            for i in group:
                lines[i] = line
            cur_x += group_w + gap
        return lines

    def _target_connector(self) -> str:
        verb_label = (self._panel.selected_verb_label() or "").lower()
        return _TARGET_CONNECTORS.get(verb_label, _DEFAULT_TARGET_CONNECTOR)

    def _noun_connector(self) -> str:
        verb_label = (self._panel.selected_verb_label() or "").lower()
        return _NOUN_CONNECTORS.get(verb_label, _DEFAULT_NOUN_CONNECTOR)

    # ------------------------------------------------------------------
    # Arcade draw layer (display required; exercised via the ui-test harness)
    # ------------------------------------------------------------------

    # Rough per-character advance for width estimation (FONT_MONO @ TEXT_SM).
    _CHAR_W = 7.0
    _LINE_H = 26.0
    _CHIP_H = 20.0
    _ROW_H = 18.0  # popup row height

    def draw(self, x: float, y: float, w: float, h: float) -> None:
        """Render the wrapped command sentence + slot chips + action button.

        Records hit rects (``_slot_rects``/``_button_rect``/``_popup_row_rects``)
        consumed by :meth:`on_mouse_press`. The open popup is drawn last so it
        overlays the sentence.
        """
        import arcade
        from dungeon_daddy.ui.theme import (
            BG_1, BG_2, BG_3, EMBER, FONT_MONO, FONT_UI, INK_2, INK_3, INK_4,
            LINE, LINE_HI, PAD_MD, PAD_SM, RADIUS_SM, TEAL, TEXT_SM,
            VIOLET, draw_kicker, draw_rounded_rect,
        )

        self._slot_rects = []
        self._popup_row_rects = []
        self._button_rect = None
        self._suggested_rects = []

        # Panel background. No "COMMAND SENTENCE" kicker — a decorative frame will
        # highlight this region later; the label read too technical and cost rows.
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_2)
        arcade.draw_line(x, y + h, x + w, y + h, LINE, 1)

        left = x + PAD_MD
        right = x + w - PAD_MD
        top_y = y + h - 16  # baseline (chip centre) of the first sentence row
        gap = 6.0

        # Per-slot tint encodes slot role (spec §8: verb VIOLET, noun/target TEAL,
        # adverb INK_2). All slots share identical chip chrome (BG_3 fill, 1px
        # border, ▾ caret) so they read as the same kind of editable control; the
        # tint is the only differentiator. The adverb uses INK_2 (not the dimmer
        # INK_3) so it does not read as static text next to the INK_3 connectors.
        _SLOT_TINT = {
            _KIND_VERB: VIOLET,
            _KIND_NOUN: TEAL,
            _KIND_TARGET: TEAL,
            _KIND_ADVERB: INK_2,
        }

        def _text_w(s: str) -> float:
            return len(s) * self._CHAR_W

        # Build the command sentence as ordered draw units so wrapping can be
        # clause-aware: "<Actor> will [VERB] the [NOUN] (conn [TARGET]) [ADVERB]".
        # Each unit is (utype, payload, width, glued); a noun/target slot is glued
        # to the connector that precedes it so a wrap never orphans the connector.
        units: list[tuple[str, object, float, bool]] = []
        actor = self._panel.acting_actor_name() or "—"
        # The actor name is content (INK_2); "will" is a glue word and shares the
        # quiet INK_3 weight of the other connectors so the sentence reads evenly
        # (CP-5). "will" is glued to the name so it never wraps away from it.
        units.append(("text", (actor, INK_2), _text_w(actor), False))
        units.append(("text", ("will", INK_3), _text_w("will"), True))
        for kind, label in self.slots():
            if kind == _KIND_NOUN:
                conn = self._noun_connector()
                units.append(("text", (conn, INK_3), _text_w(conn), False))
            elif kind == _KIND_TARGET:
                conn = self._target_connector()
                units.append(("text", (conn, INK_3), _text_w(conn), False))
            if label is None:
                # Empty slot → dim placeholder prompt instead of a value (CP-3).
                text = _SLOT_PLACEHOLDERS.get(kind, "…")
                tint = INK_4
            else:
                text = label.upper() if kind == _KIND_VERB else label
                tint = _SLOT_TINT.get(kind, INK_3)
            chip_w = _text_w(text) + PAD_SM * 2 + 14  # +14 for the ▾ affordance
            glued = kind in (_KIND_NOUN, _KIND_TARGET)
            units.append(("slot", (kind, text, tint, chip_w), chip_w, glued))

        lines = self._wrap_units(
            [u[2] for u in units], right - left, gap, [u[3] for u in units]
        )

        cur_line = 0
        cur_x = left
        for (utype, payload, width, _glued), line in zip(units, lines):
            if line != cur_line:
                cur_line = line
                cur_x = left
            cy = top_y - line * self._LINE_H
            if utype == "text":
                s, color = payload  # type: ignore[misc]
                arcade.draw_text(
                    s, cur_x, cy, color,
                    font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
                )
            else:
                kind, text, tint, chip_w = payload  # type: ignore[misc]
                draw_rounded_rect(
                    cur_x + chip_w / 2, cy, chip_w, self._CHIP_H, RADIUS_SM,
                    BG_3, border_color=tint, border_width=1,
                )
                arcade.draw_text(
                    f"{text} ▾", cur_x + chip_w / 2, cy, tint,
                    font_size=TEXT_SM, font_name=FONT_MONO,
                    anchor_x="center", anchor_y="center",
                )
                self._slot_rects.append(
                    (cur_x, cy - self._CHIP_H / 2, chip_w, self._CHIP_H, kind)
                )
            cur_x += width + gap

        # Action button — bottom-right of the band. Styling is adaptive: a
        # contested ROLL gets TEAL emphasis; a deterministic DO/MOVE/LOOK reads
        # calmer (LINE border, INK_2 text). Drawn first so the preview inset and
        # suggested row can stack above it.
        label = self.button_label()
        is_roll = label == "ROLL"
        btn_w, btn_h = 64.0, 24.0
        btn_x = right - btn_w
        btn_y = y + PAD_SM
        btn_tint = TEAL if is_roll else LINE
        btn_text = TEAL if is_roll else INK_2
        draw_rounded_rect(
            btn_x + btn_w / 2, btn_y + btn_h / 2, btn_w, btn_h, RADIUS_SM,
            BG_1 if is_roll else BG_3, border_color=btn_tint, border_width=1,
        )
        arcade.draw_text(
            label, btn_x + btn_w / 2, btn_y + btn_h / 2, btn_text,
            font_size=TEXT_SM, font_name=FONT_MONO,
            anchor_x="center", anchor_y="center", bold=True,
        )
        self._button_rect = (btn_x, btn_y, btn_w, btn_h)

        # Deterministic PREVIEW inset — likely roll / templated risk / memory
        # tags (spec §4.5). Stacks just above the button row.
        pv_lines = self.preview_lines()
        pv_line_h = 15.0
        pv_bot = btn_y + btn_h + 6
        pv_h = 12 + len(pv_lines) * pv_line_h + PAD_SM
        if pv_lines:
            draw_rounded_rect(
                left + (right - left) / 2, pv_bot + pv_h / 2, right - left, pv_h,
                RADIUS_SM, BG_1, border_color=LINE, border_width=1,
            )
            draw_kicker("PREVIEW", left + 6, pv_bot + pv_h - 6)
            line_y = pv_bot + pv_h - 22
            for pv_line in pv_lines:
                color = EMBER if pv_line.startswith("Risk:") else INK_3
                arcade.draw_text(
                    pv_line, left + 6, line_y, color,
                    font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="center",
                )
                line_y -= pv_line_h

        # Suggested-verbs quick-pick row — applicable verbs tinted VIOLET, the
        # rest greyed (INK_4). Capped for width; sits above the preview inset.
        sug_y = pv_bot + pv_h + 16
        arcade.draw_text(
            "Suggested:", left, sug_y, INK_3,
            font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
        )
        sug_x = left + _text_w("Suggested:") + 8
        for s_label, enabled in self.suggested_verbs()[: self._SUGGESTED_CAP]:
            text = s_label.upper()
            chip_w = _text_w(text) + PAD_SM * 2
            if sug_x + chip_w > right:
                break
            tint = VIOLET if enabled else INK_4
            # Active = the chip for the current verb → filled (spec §8); other
            # chips stay outlined so the row reads distinct from the verb slot.
            active = enabled and self._suggested_is_active(s_label)
            fill = tint if active else BG_3
            text_color = BG_1 if active else tint
            draw_rounded_rect(
                sug_x + chip_w / 2, sug_y, chip_w, self._CHIP_H, RADIUS_SM,
                fill, border_color=tint, border_width=1,
            )
            arcade.draw_text(
                text, sug_x + chip_w / 2, sug_y, text_color,
                font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="center", anchor_y="center",
            )
            self._suggested_rects.append(
                (sug_x, sug_y - self._CHIP_H / 2, chip_w, self._CHIP_H, s_label, enabled)
            )
            sug_x += chip_w + 6

        # Open popup — drawn last, stacked upward from its slot so it never
        # spills off the bottom of the column.
        if self._open_slot is not None:
            anchor = next(
                (r for r in self._slot_rects if r[4] == self._open_slot), None
            )
            if anchor is not None:
                ax, abot, aw, _ah, _kind = anchor
                labels = self.popup_labels()
                pop_w = max(aw, 120.0)
                row_h = self._ROW_H
                base = abot + self._CHIP_H + 2  # just above the slot chip
                for i, label in enumerate(labels):
                    row_bot = base + i * row_h
                    row_cy = row_bot + row_h / 2
                    draw_rounded_rect(
                        ax + pop_w / 2, row_cy, pop_w, row_h, RADIUS_SM,
                        BG_1, border_color=LINE_HI, border_width=1,
                    )
                    arcade.draw_text(
                        label, ax + PAD_SM, row_cy, INK_2,
                        font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="center",
                    )
                    self._popup_row_rects.append(
                        (ax, row_bot, pop_w, row_h, label)
                    )
