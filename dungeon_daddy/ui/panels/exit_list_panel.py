"""Read-only Play-mode exit-list panel (Phase 48 Slice 10; Phase 50 Slice 8).

A thin, informational panel that displays the navigation state from the
room-context bundle (``rpg/room_context.build_room_context``) — visible exits,
locked exits with their reason, and the passive hidden-exit hint. Phase 50's
VNA Card panel (``ui/panels/vna_action_panel``) owns *acting* on exits (``verb =
move``); this panel is now display-only, so the provisional ``how?`` chip row
and click-to-move were retired with ``ui/how_chips``.
"""
from __future__ import annotations

_LINE_H = 18.0
_ROW_GAP = 4.0
_PAD = 12.0  # mirrors theme.PAD_MD


class ExitListPanel:
    def __init__(self) -> None:
        self._visible_exits: list[dict] = []
        self._locked_exits: list[dict] = []
        self._hidden_exit_hint: int = 0
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

    # -- geometry -------------------------------------------------------------

    def setup(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h

    def _layout(self) -> dict:
        """Shared layout used by both draw() and tests.

        Returns display rects (arcade coords; (x, y) = bottom-left) for the
        room header, the EXITS header, visible exits, locked exits, and the
        hidden-exit hint.
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

        return {"room": room, "headers": headers, "exits": exits, "locked": locked, "hint": hint}

    # -- render ---------------------------------------------------------------

    def draw(self) -> None:
        import arcade
        from dungeon_daddy.ui.theme import (
            BG_1, INK_1, INK_2, INK_3, INK_4,
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
