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

from dungeon_daddy.rpg.action_options import DIALOGUE_VERBS, VERB_LOOK, VERB_MOVE
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
        # Hit rects populated by draw(): slots, the open popup's rows, the button.
        self._slot_rects: list[tuple[float, float, float, float, str]] = []
        self._popup_row_rects: list[tuple[float, float, float, float, str]] = []
        # Clickable suggested-approach chips for the selected obstacle (Slice 3).
        self._suggestion_rects: list[tuple[float, float, float, float, str]] = []
        self._button_rect: tuple[float, float, float, float] | None = None
        # Collapsible band (Slice 11): collapsed shows only the header/toggle row.
        # ``_user_toggled`` latches once the user clicks the toggle so that
        # auto-collapse (driven by window height) stops overriding their choice.
        self._collapsed = False
        self._user_toggled = False
        self._toggle_rect: tuple[float, float, float, float] | None = None

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

    # ------------------------------------------------------------------
    # Obstacle approaches (Slice 3) — suggested actions for the selected obstacle
    # ------------------------------------------------------------------

    def suggested_approach_labels(self) -> list[str]:
        """Display labels of the selected obstacle's suggested approach verbs.

        The obstacle's class-flavored approaches (from the room context) filtered
        to the verbs actually **offered** to the acting actor, so every suggestion
        is actionable — universal approaches (fight, tinker, …) always show; a
        class approach the actor lacks does not. Empty when the selected noun is
        not an obstacle. Order follows the obstacle's approach order.
        """
        approach_verbs = self._panel.selected_noun_approach_verbs()
        offered = {v.verb: v.label for v in self._panel.verb_options()}
        return [offered[verb] for verb in approach_verbs if verb in offered]

    def _select_suggested_approach(self, label: str) -> None:
        """Select a suggested approach verb while keeping the obstacle noun.

        ``select_verb`` re-defaults the Noun slot, so the currently-selected
        obstacle is re-selected afterwards — the player's intent is "solve *this*
        obstacle with that approach".
        """
        noun = self._panel.selected_noun_option()
        self._panel.select_verb_by_label(label)
        if noun is not None:
            self._panel.select_noun(noun.noun_id)

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
    # Collapsible band (Slice 11)
    # ------------------------------------------------------------------

    def is_collapsed(self) -> bool:
        """Whether the band is collapsed to its header/toggle row only."""
        return self._collapsed

    def toggle_collapsed(self) -> None:
        """Flip the collapsed state in response to a user click on the toggle.

        Latches ``_user_toggled`` so subsequent :meth:`apply_auto_collapse`
        calls (driven by window height) no longer override the user's choice.
        """
        self._collapsed = not self._collapsed
        self._user_toggled = True

    def apply_auto_collapse(self, should_collapse: bool) -> None:
        """Auto-collapse on short windows, unless the user has toggled manually.

        The host panel calls this each layout with ``window height < threshold``;
        once the user clicks the ▾/▴ toggle their preference wins.
        """
        if not self._user_toggled:
            self._collapsed = should_collapse

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
        rows selects that option and closes the popup. The collapse toggle in the
        header row is hit-tested before the slots/button.
        """
        if self._toggle_rect is not None:
            left, bottom, w, h = self._toggle_rect
            if left <= x < left + w and bottom <= y < bottom + h:
                self.toggle_collapsed()
                self._open_slot = None
                return True
        if self._open_slot is not None:
            for left, bottom, w, h, label in self._popup_row_rects:
                if left <= x < left + w and bottom <= y < bottom + h:
                    self._select(self._open_slot, label)
                    self._open_slot = None
                    return True
            # A click anywhere else while a popup is open dismisses it.
            self._open_slot = None
            return True
        for left, bottom, w, h, kind in self._slot_rects:
            if left <= x < left + w and bottom <= y < bottom + h:
                self._open_slot = kind
                return True
        for left, bottom, w, h, label in self._suggestion_rects:
            if left <= x < left + w and bottom <= y < bottom + h:
                self._select_suggested_approach(label)
                return True
        if self._button_rect is not None:
            left, bottom, w, h = self._button_rect
            if left <= x < left + w and bottom <= y < bottom + h:
                self._panel.submit()
                return True
        return False

    # Deterministic verbs that read calmer than a generic "DO" (spec §4.6).
    _DETERMINISTIC_BUTTON_LABELS = {VERB_MOVE: "MOVE", VERB_LOOK: "LOOK"}

    def is_dialogue_action(self) -> bool:
        """True when the current selection opens dialogue (Slice 10, §6).

        A ``sway``/talk-family verb aimed at a *speakable* creature initiates a
        conversation (which swaps the bottom input to the SAY box) rather than
        resolving a contested roll. Surfaced in the builder as a ``TALK`` button;
        the conversation itself is a Phase 51 extension point.
        """
        verb = self._panel.selected_verb_label()
        if verb is None or verb.lower() not in DIALOGUE_VERBS:
            return False
        return self._panel.selected_noun_is_speakable()

    def button_label(self) -> str:
        """Adaptive action-button label (spec §4.6, §6).

        ``TALK`` when the action opens dialogue (a sway/talk verb on a speakable
        target); ``ROLL`` when the action is contested/uncertain (or no preview
        yet); otherwise the deterministic ``MOVE`` / ``LOOK`` for those verbs,
        else ``DO``. Derived from the deterministic :meth:`VnaActionPanel.preview`.
        """
        if self.is_dialogue_action():
            return "TALK"
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
    _UNIT_GAP = 6.0  # horizontal gap between sentence units
    _BTN_H = 24.0  # action button height
    _HEADER_H = 26.0  # top header/toggle bar height (also the collapsed height)
    _SENTENCE_TOP_OFF = 16.0  # first-row baseline below the band top
    _PV_LINE_H = 15.0  # preview inset line height
    _PV_GAP = 6.0  # gap between the button row and the preview inset
    _SUGGEST_ROW_H = 20.0  # suggested-approach chip row height
    # Constant gap kept between the wrapped sentence's lowest chip and the top of
    # the preview inset; the band sizes to honour it (Slice 11 dynamic height).
    _SENTENCE_PREVIEW_GAP = 16.0

    def _text_w(self, s: str) -> float:
        return len(s) * self._CHAR_W

    def _sentence_units(self) -> list[tuple[str, object, float, bool]]:
        """Ordered draw units for the command sentence with wrap geometry.

        Each unit is ``(utype, payload, width, glued)`` where ``utype`` is
        ``"text"`` or ``"slot"``. Shared by :meth:`draw` and
        :meth:`sentence_line_count` so the measured line count always matches
        what is rendered. Builds "<Actor> will [VERB] (conn) [NOUN] (conn
        [TARGET]) [ADVERB]"; a noun/target slot is glued to the connector that
        precedes it so a wrap never orphans the connector.
        """
        from dungeon_daddy.ui.theme import INK_2, INK_3, INK_4, PAD_SM, TEAL, VIOLET

        # Per-slot tint encodes slot role (spec §8: verb VIOLET, noun/target TEAL,
        # adverb INK_2). The adverb uses INK_2 (not the dimmer INK_3) so it does
        # not read as static text next to the INK_3 connectors.
        slot_tint = {
            _KIND_VERB: VIOLET,
            _KIND_NOUN: TEAL,
            _KIND_TARGET: TEAL,
            _KIND_ADVERB: INK_2,
        }
        units: list[tuple[str, object, float, bool]] = []
        actor = self._panel.acting_actor_name() or "—"
        # The actor name is content (INK_2); "will" is a glue word sharing the
        # quiet INK_3 weight of the other connectors (CP-5) and glued to the name.
        units.append(("text", (actor, INK_2), self._text_w(actor), False))
        units.append(("text", ("will", INK_3), self._text_w("will"), True))
        for kind, label in self.slots():
            if kind == _KIND_NOUN:
                conn = self._noun_connector()
                units.append(("text", (conn, INK_3), self._text_w(conn), False))
            elif kind == _KIND_TARGET:
                conn = self._target_connector()
                units.append(("text", (conn, INK_3), self._text_w(conn), False))
            if label is None:
                # Empty slot → dim placeholder prompt instead of a value (CP-3).
                text = _SLOT_PLACEHOLDERS.get(kind, "…")
                tint = INK_4
            else:
                text = label.upper() if kind == _KIND_VERB else label
                tint = slot_tint.get(kind, INK_3)
            chip_w = self._text_w(text) + PAD_SM * 2 + 14  # +14 for the ▾ caret
            glued = kind in (_KIND_NOUN, _KIND_TARGET)
            units.append(("slot", (kind, text, tint, chip_w), chip_w, glued))
        return units

    def sentence_line_count(self, w: float) -> int:
        """Number of wrapped rows the command sentence occupies at band width ``w``.

        Mirrors :meth:`draw`'s wrap so the band can be sized to the sentence
        (Slice 11). ``w`` is the band width; the usable text column is
        ``w − 2·PAD_MD``.
        """
        from dungeon_daddy.ui.theme import PAD_MD

        units = self._sentence_units()
        if not units:
            return 1
        avail = w - 2 * PAD_MD
        lines = self._wrap_units(
            [u[2] for u in units], avail, self._UNIT_GAP, [u[3] for u in units]
        )
        return max(lines) + 1

    def content_height(self, w: float) -> float:
        """Band height that keeps the sentence↔preview gap constant (Slice 11).

        The sentence is top-anchored and the button/preview are bottom-anchored
        (see :meth:`draw`), so sizing the band to the wrapped line count + the
        preview-line count keeps a constant gap between them — killing both the
        airy-when-short gap and the collision-when-long overlap of the old fixed
        180px band (spec §9 Slice 11 requirement). When collapsed only the
        header/toggle row is shown.
        """
        from dungeon_daddy.ui.theme import PAD_SM

        if self._collapsed:
            return self._HEADER_H
        n = self.sentence_line_count(w)
        pv = self.preview_lines()
        pv_h = len(pv) * self._PV_LINE_H + 2 * PAD_SM if pv else 0.0
        sug_h = (
            self._SUGGEST_ROW_H + self._PV_GAP
            if self.suggested_approach_labels()
            else 0.0
        )
        bottom_block = PAD_SM + self._BTN_H + self._PV_GAP  # button row + gap
        return (
            self._HEADER_H
            + self._SENTENCE_PREVIEW_GAP
            + self._SENTENCE_TOP_OFF
            + self._CHIP_H / 2
            + bottom_block
            + (n - 1) * self._LINE_H
            + pv_h
            + sug_h
        )

    def draw(self, x: float, y: float, w: float, h: float) -> None:
        """Render the wrapped command sentence + slot chips + action button.

        Records hit rects (``_slot_rects``/``_button_rect``/``_popup_row_rects``)
        consumed by :meth:`on_mouse_press`. The open popup is drawn last so it
        overlays the sentence.
        """
        import arcade

        from dungeon_daddy.ui.theme import (
            BG_1,
            BG_2,
            BG_3,
            EMBER,
            FONT_MONO,
            FONT_UI,
            INK_2,
            INK_3,
            LINE,
            LINE_HI,
            PAD_MD,
            PAD_SM,
            RADIUS_SM,
            TEAL,
            TEXT_SM,
            VIOLET,
            draw_rounded_rect,
        )

        self._slot_rects = []
        self._popup_row_rects = []
        self._suggestion_rects = []
        self._button_rect = None
        self._toggle_rect = None

        # Panel background. No "COMMAND SENTENCE" kicker — a decorative frame will
        # highlight this region later; the label read too technical and cost rows.
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_2)
        arcade.draw_line(x, y + h, x + w, y + h, LINE, 1)

        left = x + PAD_MD
        right = x + w - PAD_MD

        # Header/toggle bar across the top of the band. The WHOLE bar is the
        # click target (a tiny corner caret was too hard to hit, especially when
        # collapsed at the bottom edge) — clicking anywhere on it collapses or
        # expands the band. When collapsed only this bar is drawn (Slice 11).
        header_bot = y + h - self._HEADER_H
        header_cy = header_bot + self._HEADER_H / 2
        arcade.draw_rect_filled(
            arcade.XYWH(x + w / 2, header_cy, w, self._HEADER_H), BG_3
        )
        arcade.draw_line(x, header_bot, x + w, header_bot, LINE, 1)
        arcade.draw_text(
            "ACTION", left, header_cy, INK_3,
            font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="center",
        )
        caret = "▾ show" if self._collapsed else "▴ hide"
        arcade.draw_text(
            caret, right, header_cy, INK_2,
            font_size=TEXT_SM, font_name=FONT_MONO,
            anchor_x="right", anchor_y="center",
        )
        self._toggle_rect = (x, header_bot, w, self._HEADER_H)
        if self._collapsed:
            return

        # Sentence chips sit below the header row.
        top_y = y + h - self._HEADER_H - self._SENTENCE_TOP_OFF
        gap = self._UNIT_GAP

        # Build the command sentence as ordered draw units so wrapping is
        # clause-aware (see _sentence_units). The same units feed
        # sentence_line_count so the measured band height matches the render.
        units = self._sentence_units()

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
        btn_w, btn_h = 64.0, self._BTN_H
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

        # Deterministic preview inset — likely roll / templated risk / memory
        # tags (spec §4.5), stacked just above the button row. No "PREVIEW"
        # kicker: the lines are self-describing and the kicker's accent bar poked
        # above the box. Lines are centred with symmetric top/bottom padding.
        pv_line_h = self._PV_LINE_H
        pv_bot = btn_y + btn_h + self._PV_GAP
        pv_lines = self.preview_lines()
        pv_h = len(pv_lines) * pv_line_h + 2 * PAD_SM if pv_lines else 0.0
        if pv_lines:
            draw_rounded_rect(
                left + (right - left) / 2, pv_bot + pv_h / 2, right - left, pv_h,
                RADIUS_SM, BG_1, border_color=LINE, border_width=1,
            )
            line_y = pv_bot + pv_h - PAD_SM - pv_line_h / 2
            for pv_line in pv_lines:
                color = EMBER if pv_line.startswith("Risk:") else INK_3
                arcade.draw_text(
                    pv_line, left + PAD_SM, line_y, color,
                    font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="center",
                )
                line_y -= pv_line_h

        # Suggested-approach chips — the selected obstacle's class-flavored
        # approaches (Slice 3), a clickable row above the preview inset. Clicking
        # a chip fills the Verb slot with that approach (keeping the obstacle
        # noun). A leading "TRY" caption reads as a hint, not a value.
        sug_labels = self.suggested_approach_labels()
        if sug_labels:
            sug_bot = pv_bot + pv_h + self._PV_GAP
            sug_cy = sug_bot + self._SUGGEST_ROW_H / 2
            cur_x = left
            arcade.draw_text(
                "TRY", cur_x, sug_cy, INK_3,
                font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="center",
            )
            cur_x += self._text_w("TRY") + self._UNIT_GAP
            for label in sug_labels:
                chip_w = self._text_w(label) + PAD_SM * 2
                draw_rounded_rect(
                    cur_x + chip_w / 2, sug_cy, chip_w, self._SUGGEST_ROW_H,
                    RADIUS_SM, BG_3, border_color=VIOLET, border_width=1,
                )
                arcade.draw_text(
                    label.upper(), cur_x + chip_w / 2, sug_cy, VIOLET,
                    font_size=TEXT_SM, font_name=FONT_MONO,
                    anchor_x="center", anchor_y="center",
                )
                self._suggestion_rects.append(
                    (cur_x, sug_cy - self._SUGGEST_ROW_H / 2, chip_w,
                     self._SUGGEST_ROW_H, label)
                )
                cur_x += chip_w + self._UNIT_GAP

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
