"""Provisional Play-mode exit-list panel (Phase 48 Slice 10).

Throwaway UI: a thin panel that displays the navigation state from the
room-context bundle (``rpg/room_context.build_room_context``) — visible exits,
locked exits with their reason, the passive hidden-exit hint, and a contextual
``how?`` chip row (``ui/how_chips.build_how_chips``). Clicking a chip selects the
adverb; clicking a visible exit issues a move via the registered callback. Phase
50's Card primitive replaces it; the engine and the ``how?``->flag contract are
the durable parts.
"""
from __future__ import annotations

from collections.abc import Callable

from dungeon_daddy.ui.how_chips import HowChipData

_LINE_H = 18.0
_ROW_GAP = 4.0
_CHIP_H = 20.0
_CHIP_GAP = 6.0
_CHIP_CHAR_PX = 7.0
_CHIP_PAD = 12.0
_PAD = 12.0  # mirrors theme.PAD_MD


def _in_rect(rect: tuple[float, float, float, float], px: float, py: float) -> bool:
    x, y, w, h = rect
    return x <= px < x + w and y <= py < y + h


class ExitListPanel:
    def __init__(self) -> None:
        self._visible_exits: list[dict] = []
        self._locked_exits: list[dict] = []
        self._hidden_exit_hint: int = 0
        self._how_chips: list[HowChipData] = []
        self._selected_how: str | None = None
        self._on_move: Callable[[str, str], None] | None = None
        self._current_room_name: str | None = None
        self._current_room_id: str | None = None
        self._x = self._y = self._w = self._h = 0.0

    # -- data -----------------------------------------------------------------

    def set_current_room(self, name: str | None, room_id: str | None) -> None:
        """Identify the room the party is in, shown at the top of the panel."""
        self._current_room_name = name
        self._current_room_id = room_id

    def set_from_context(self, bundle: dict) -> None:
        self._visible_exits = list(bundle.get("visible_exits", []))
        self._locked_exits = list(bundle.get("locked_exits", []))
        self._hidden_exit_hint = int(bundle.get("hidden_exit_hint", 0))

    def set_how_chips(self, chips: list[HowChipData]) -> None:
        self._how_chips = list(chips)
        valid = {c.how for c in self._how_chips}
        if self._selected_how not in valid:
            self._selected_how = self._how_chips[0].how if self._how_chips else None

    def set_move_callback(self, fn: Callable[[str, str], None]) -> None:
        self._on_move = fn

    @property
    def selected_how(self) -> str | None:
        return self._selected_how

    # -- geometry -------------------------------------------------------------

    def setup(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h

    def _layout(self) -> dict:
        """Shared layout used by both draw() and handle_click().

        Returns clickable rects (arcade coords; (x, y) = bottom-left) for the
        visible exits and how-chips, plus display rects for locked exits, the
        hidden hint, and section headers.
        """
        left = self._x + _PAD
        row_w = self._w - 2 * _PAD
        top = self._y + self._h - _PAD

        def take_row(height: float) -> tuple[float, float, float, float]:
            nonlocal top
            bottom = top - height
            rect = (left, bottom, row_w, height)
            top = bottom - _ROW_GAP
            return rect

        headers: list[tuple[str, tuple[float, float, float, float]]] = []
        room: list[tuple[str, str, tuple[float, float, float, float]]] = []
        exits: list[tuple[str, str, str, tuple[float, float, float, float]]] = []
        locked: list[tuple[str, tuple[float, float, float, float]]] = []
        hint: tuple[str, tuple[float, float, float, float]] | None = None
        chips: list[tuple[str, str, tuple[float, float, float, float]]] = []

        if self._current_room_name:
            room.append(("name", self._current_room_name, take_row(_LINE_H)))
            if self._current_room_id:
                room.append(("id", self._current_room_id, take_row(_LINE_H)))

        headers.append(("EXITS", take_row(_LINE_H)))

        for ex in self._visible_exits:
            label = f"-> {ex['label']}  ({ex['status']})"
            exits.append((ex["exit_id"], label, ex["status"], take_row(_LINE_H)))

        for ex in self._locked_exits:
            missing = ex.get("missing_condition")
            suffix = f" — {missing}" if missing else ""
            text = f"-> {ex['label']}  ({ex['reason']}{suffix})"
            locked.append((text, take_row(_LINE_H)))

        if self._hidden_exit_hint:
            n = self._hidden_exit_hint
            plural = "s" if n != 1 else ""
            hint = (f"-> ???  ({n} hidden exit{plural} detected)", take_row(_LINE_H))

        if self._how_chips:
            headers.append(("HOW?", take_row(_LINE_H)))
            chip_top = top
            cx = left
            for chip in self._how_chips:
                cw = len(chip.label) * _CHIP_CHAR_PX + _CHIP_PAD
                if cx + cw > left + row_w:
                    chip_top -= _CHIP_H + _CHIP_GAP
                    cx = left
                chips.append((chip.how, chip.label, (cx, chip_top - _CHIP_H, cw, _CHIP_H)))
                cx += cw + _CHIP_GAP
            top = chip_top - _CHIP_H - _CHIP_GAP

        return {"room": room, "headers": headers, "exits": exits, "locked": locked, "hint": hint, "chips": chips}

    # -- interaction ----------------------------------------------------------

    def handle_click(self, px: float, py: float) -> bool:
        layout = self._layout()
        for how, _label, rect in layout["chips"]:
            if _in_rect(rect, px, py):
                self._selected_how = how
                return True
        for exit_id, _label, _status, rect in layout["exits"]:
            if _in_rect(rect, px, py):
                if self._on_move is not None and self._selected_how is not None:
                    self._on_move(exit_id, self._selected_how)
                return True
        return False

    # -- render ---------------------------------------------------------------

    def draw(self) -> None:
        import arcade
        from dungeon_daddy.ui.theme import (
            BG_1, BG_2, BG_HI, INK_1, INK_2, INK_3, INK_4, TEAL, LINE,
            FONT_UI, TEXT_SM, TEXT_BASE,
        )

        x, y, w, h = self._x, self._y, self._w, self._h
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_1)

        layout = self._layout()

        def _text(s: str, rect, color, size=TEXT_SM) -> None:
            rx, ry, _rw, rh = rect
            arcade.draw_text(
                s, rx, ry + rh, color,
                font_size=size, font_name=FONT_UI, anchor_y="top",
            )

        for kind, text, rect in layout["room"]:
            if kind == "name":
                _text(text, rect, INK_1, TEXT_BASE)
            else:
                _text(text, rect, INK_4)
        for label, rect in layout["headers"]:
            _text(label, rect, INK_3, TEXT_BASE)
        for _eid, label, _status, rect in layout["exits"]:
            _text(label, rect, INK_2)
        for label, rect in layout["locked"]:
            _text(label, rect, INK_4)
        if layout["hint"] is not None:
            text, rect = layout["hint"]
            _text(text, rect, INK_3)

        for how, label, rect in layout["chips"]:
            cx, cy, cw, ch = rect
            selected = how == self._selected_how
            arcade.draw_rect_filled(arcade.XYWH(cx + cw / 2, cy + ch / 2, cw, ch),
                                    BG_HI if selected else BG_2)
            arcade.draw_rect_outline(arcade.XYWH(cx + cw / 2, cy + ch / 2, cw, ch),
                                     TEAL if selected else LINE, 1)
            arcade.draw_text(
                label, cx + cw / 2, cy + ch / 2,
                TEAL if selected else INK_3,
                font_size=TEXT_SM, font_name=FONT_UI,
                anchor_x="center", anchor_y="center",
            )
