"""Memory inspector panel — search and browse memory entries in Play Mode."""
from __future__ import annotations

from dungeon_daddy.memory.models import MemoryEntry

_BOX_H = 26.0
_ROW_H = 20.0
_BTN_H = 22.0
_DETAIL_H_MIN = 40.0      # minimum detail pane height (no-selection hint)
_LINE_H_TITLE = 16        # TEXT_SM line height in pixels
_LINE_H_SUM   = 14        # TEXT_XS line height in pixels
_CHIP_CX_OFFSET = 38.0   # chip center is x2 - this value
_CHIP_W = 72.0            # chip draw_chip width (must fit "approved" / "rejected")
_CHAR_PX = 6.5            # approx Inter 10pt average character width in pixels
_CHAR_PX_XS = 5.8         # approx Inter 9pt average character width in pixels


def _word_wrap_lines(text: str, max_chars: int) -> list[str]:
    """Break text at word boundaries to fit within max_chars per line."""
    if not text:
        return []
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        wlen = len(word)
        if not current:
            current = [word]
            current_len = wlen
        elif current_len + 1 + wlen <= max_chars:
            current.append(word)
            current_len += 1 + wlen
        else:
            lines.append(" ".join(current))
            current = [word]
            current_len = wlen
    if current:
        lines.append(" ".join(current))
    return lines


class MemoryInspectorPanel:
    def __init__(self) -> None:
        self._entries: list[MemoryEntry] = []
        self._search_query: str = ""
        self._selected: MemoryEntry | None = None
        self._sync_warnings: set[str] = set()
        self._pending_commit: MemoryEntry | None = None
        self._x = self._y = self._w = self._h = 0.0
        self._widget: object | None = None  # arcade.gui.UIInputText when live
        self._entry_rects: list[tuple[float, float, float, float, MemoryEntry]] = []
        self._button_rects: dict[str, tuple[float, float, float, float]] = {}

    def set_entries(self, entries: list[MemoryEntry]) -> None:
        self._entries = list(entries)

    def set_search_query(self, query: str) -> None:
        self._search_query = query

    def get_results(self) -> list[MemoryEntry]:
        q = self._search_query.lower()
        if not q:
            return list(self._entries)
        return [
            e for e in self._entries
            if q in e.title.lower() or any(q in t.lower() for t in e.tags)
        ]

    def select_entry(self, entry: MemoryEntry | None) -> None:
        self._selected = entry

    def approve_selected(self) -> None:
        if self._selected is None:
            return
        updated = self._selected.model_copy(update={"status": "approved"})
        self._replace_entry(self._selected, updated)
        self._selected = updated
        self._pending_commit = updated

    def reject_selected(self) -> None:
        if self._selected is None:
            return
        updated = self._selected.model_copy(update={"status": "rejected"})
        self._replace_entry(self._selected, updated)
        self._selected = updated
        self._pending_commit = updated

    def edit_selected_summary(self, new_summary: str) -> None:
        if self._selected is None:
            return
        updated = self._selected.model_copy(update={"summary": new_summary})
        self._replace_entry(self._selected, updated)
        self._selected = updated
        self._pending_commit = updated

    def pop_pending_commit(self) -> MemoryEntry | None:
        entry = self._pending_commit
        self._pending_commit = None
        return entry

    def _replace_entry(self, old: MemoryEntry, new: MemoryEntry) -> None:
        self._entries = [new if e is old else e for e in self._entries]

    def set_sync_warnings(self, memory_ids: set[str]) -> None:
        self._sync_warnings = set(memory_ids)

    def has_sync_warning(self, memory_id: str) -> bool:
        return memory_id in self._sync_warnings

    def _compute_detail_h(self, w: float) -> float:
        """Return the pixel height needed to fully display the selected entry."""
        from dungeon_daddy.ui.theme import PAD_MD, PAD_SM
        if self._selected is None:
            return _DETAIL_H_MIN
        text_w = w - PAD_MD * 2
        title_chars = max(10, int(text_w / _CHAR_PX))
        sum_chars = max(10, int(text_w / _CHAR_PX_XS))
        title_lines = _word_wrap_lines(self._selected.title, title_chars)
        summary = (self._selected.summary or "").strip()
        sum_lines = _word_wrap_lines(summary, sum_chars) if summary else []
        h = PAD_SM + max(1, len(title_lines)) * _LINE_H_TITLE
        if sum_lines:
            h += 4 + len(sum_lines) * _LINE_H_SUM
        h += PAD_SM
        return max(_DETAIL_H_MIN, float(h))

    def _update_layout(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        results: list[MemoryEntry],
        detail_h: float = _DETAIL_H_MIN,
    ) -> None:
        from dungeon_daddy.ui.theme import PAD_MD
        list_top = y + h - PAD_MD - _BOX_H - PAD_MD
        list_bottom = y + PAD_MD * 3 + _BTN_H + detail_h

        rects: list[tuple[float, float, float, float, MemoryEntry]] = []
        for i, entry in enumerate(results):
            row_top = list_top - i * _ROW_H
            row_bottom = row_top - _ROW_H
            if row_bottom < list_bottom:
                break
            rects.append((x, row_bottom, x + w, row_top, entry))
        self._entry_rects = rects

        btn_y1 = y + PAD_MD
        btn_y2 = y + PAD_MD + _BTN_H
        mid_x = x + w / 2
        gap = PAD_MD / 2
        self._button_rects = {
            "approve": (x + PAD_MD, btn_y1, mid_x - gap, btn_y2),
            "reject": (mid_x + gap, btn_y1, x + w - PAD_MD, btn_y2),
        }

    def hit_entry(self, x: float, y: float) -> MemoryEntry | None:
        for x1, y1, x2, y2, entry in self._entry_rects:
            if x1 <= x <= x2 and y1 <= y <= y2:
                return entry
        return None

    def hit_button(self, x: float, y: float) -> str | None:
        if self._selected is None:
            return None
        for name, (bx1, by1, bx2, by2) in self._button_rects.items():
            if bx1 <= x <= bx2 and by1 <= y <= by2:
                return name
        return None

    def setup(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h

    def setup_widget(self, manager: object | None, x: float, y: float, w: float, h: float) -> None:
        """Create and register an interactive UIInputText for search."""
        if manager is None:
            return
        import arcade
        import arcade.gui

        from dungeon_daddy.ui.theme import FONT_MONO, INK_3, PAD_MD, TEXT_SM
        self.teardown_widget(manager)
        box_x = x + PAD_MD
        box_y = y + h - PAD_MD - _BOX_H
        box_w = w - PAD_MD * 2
        widget = arcade.gui.UIInputText(
            x=int(box_x), y=int(box_y),
            width=int(box_w), height=int(_BOX_H),
            text=self._search_query,
            font_name=(FONT_MONO,),
            font_size=TEXT_SM,
            text_color=(*INK_3, 255),
            multiline=False,
        )
        manager.add(widget)  # type: ignore[union-attr]
        self._widget = widget

    def teardown_widget(self, manager: object | None) -> None:
        """Remove the UIInputText from the manager."""
        if manager is None or self._widget is None:
            return
        try:
            manager.remove(self._widget)  # type: ignore[union-attr]
        except Exception:
            pass
        self._widget = None

    def draw(self) -> None:
        import arcade

        from dungeon_daddy.ui.theme import (
            BG_1,
            BG_2,
            BG_HI,
            FONT_MONO,
            FONT_UI,
            INK_1,
            INK_3,
            INK_4,
            LINE,
            PAD_MD,
            TEXT_SM,
            draw_chip,
        )

        x, y, w, h = self._x, self._y, self._w, self._h
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_1)

        # Sync search query from live widget if present
        box_x = x + PAD_MD
        box_y = y + h - PAD_MD - _BOX_H
        box_w = w - PAD_MD * 2
        box_cx, box_cy = box_x + box_w / 2, box_y + _BOX_H / 2
        if self._widget is not None:
            self._search_query = self._widget.text  # type: ignore[union-attr]
            if not self._search_query:
                arcade.draw_text(
                    "search tag / actor / location",
                    box_x + 4, box_cy,
                    INK_4, font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="center",
                )
        else:
            arcade.draw_rect_filled(arcade.XYWH(box_cx, box_cy, box_w, _BOX_H), BG_2)
            arcade.draw_rect_outline(arcade.XYWH(box_cx, box_cy, box_w, _BOX_H), LINE, 1)
            label = self._search_query if self._search_query else "search tag / actor / location"
            label_color = INK_3 if self._search_query else INK_4
            arcade.draw_text(
                label, box_x + 4, box_cy,
                label_color, font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="center",
            )

        detail_h = self._compute_detail_h(w)
        results = self.get_results()
        self._update_layout(x, y, w, h, results, detail_h=detail_h)

        list_top = y + h - PAD_MD - _BOX_H - PAD_MD
        if not results:
            arcade.draw_text(
                "No memories found", x + PAD_MD, list_top - _BOX_H / 2,
                INK_4, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
            self._draw_detail_pane(x, y, w, detail_h, arcade)
            self._draw_action_buttons(x, y, w, arcade)
            return

        _STATUS_COLOR = {
            "draft":    "ember",
            "approved": "teal",
            "rejected": "default",
            "archived": "default",
        }
        for x1, y1, x2, y2, entry in self._entry_rects:
            row_cy = (y1 + y2) / 2
            is_selected = self._selected is not None and entry.memory_id == self._selected.memory_id
            if is_selected:
                arcade.draw_rect_filled(arcade.XYWH((x1 + x2) / 2, row_cy, x2 - x1, y2 - y1), BG_HI)
            warning = " ⚠" if self.has_sync_warning(entry.memory_id) else ""
            title_color = INK_1 if is_selected else INK_3
            chip_left = x2 - _CHIP_CX_OFFSET - _CHIP_W / 2
            max_chars = max(10, int((chip_left - PAD_MD - (x1 + PAD_MD)) / _CHAR_PX))
            raw = entry.title
            title = raw if len(raw) <= max_chars else raw[: max_chars - 1] + "…"
            arcade.draw_text(
                f"{title}{warning}",
                x1 + PAD_MD, y2,
                title_color, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
            )
            chip_color = _STATUS_COLOR.get(entry.status, "default")
            draw_chip(entry.status, x2 - _CHIP_CX_OFFSET, row_cy, color=chip_color, width=int(_CHIP_W))

        self._draw_detail_pane(x, y, w, detail_h, arcade)
        self._draw_action_buttons(x, y, w, arcade)

    def _draw_detail_pane(self, x: float, y: float, w: float, detail_h: float, arcade) -> None:
        from dungeon_daddy.ui.theme import (
            BG_2,
            FONT_UI,
            INK_1,
            INK_3,
            INK_4,
            LINE,
            PAD_MD,
            PAD_SM,
            TEXT_SM,
            TEXT_XS,
        )
        pane_y1 = y + PAD_MD * 2 + _BTN_H
        pane_y2 = pane_y1 + detail_h
        cx = x + w / 2
        arcade.draw_rect_filled(arcade.XYWH(cx, pane_y1 + detail_h / 2, w, detail_h), BG_2)
        arcade.draw_line(x, pane_y2, x + w, pane_y2, LINE, 1)

        if self._selected is None:
            arcade.draw_text(
                "select an entry to review",
                cx, pane_y1 + detail_h / 2,
                INK_4, font_size=TEXT_SM, font_name=FONT_UI,
                anchor_x="center", anchor_y="center",
            )
            return

        text_x = x + PAD_MD
        text_w = w - PAD_MD * 2
        title_chars = max(10, int(text_w / _CHAR_PX))
        sum_chars = max(10, int(text_w / _CHAR_PX_XS))

        cur_y = pane_y2 - PAD_SM  # current baseline, decreasing downward

        title_lines = _word_wrap_lines(self._selected.title, title_chars)
        for line in title_lines:
            arcade.draw_text(line, text_x, cur_y, INK_1,
                             font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top")
            cur_y -= _LINE_H_TITLE

        summary = (self._selected.summary or "").strip()
        if summary:
            cur_y -= 4
            for line in _word_wrap_lines(summary, sum_chars):
                arcade.draw_text(line, text_x, cur_y, INK_3,
                                 font_size=TEXT_XS, font_name=FONT_UI, anchor_y="top")
                cur_y -= _LINE_H_SUM

    def _draw_action_buttons(self, x: float, y: float, w: float, arcade) -> None:
        from dungeon_daddy.ui.theme import (
            BG_2,
            EMBER,
            FONT_UI,
            INK_4,
            TEAL,
            TEAL_DIM,
            TEXT_SM,
        )
        has_sel = self._selected is not None
        ax1, ay1, ax2, ay2 = self._button_rects.get("approve", (0, 0, 0, 0))
        rx1, ry1, rx2, ry2 = self._button_rects.get("reject", (0, 0, 0, 0))
        acx, acy = (ax1 + ax2) / 2, (ay1 + ay2) / 2
        rcx, rcy = (rx1 + rx2) / 2, (ry1 + ry2) / 2
        aw, ah = ax2 - ax1, ay2 - ay1
        rw, rh = rx2 - rx1, ry2 - ry1

        approve_bg = (TEAL_DIM if has_sel else BG_2)
        approve_fg = TEAL if has_sel else INK_4
        reject_bg = ((72, 38, 20) if has_sel else BG_2)
        reject_fg = EMBER if has_sel else INK_4

        arcade.draw_rect_filled(arcade.XYWH(acx, acy, aw, ah), approve_bg)
        arcade.draw_rect_outline(arcade.XYWH(acx, acy, aw, ah), approve_fg, 1)
        arcade.draw_text("✓ APPROVE", acx, acy, approve_fg,
                         font_size=TEXT_SM, font_name=FONT_UI,
                         anchor_x="center", anchor_y="center")

        arcade.draw_rect_filled(arcade.XYWH(rcx, rcy, rw, rh), reject_bg)
        arcade.draw_rect_outline(arcade.XYWH(rcx, rcy, rw, rh), reject_fg, 1)
        arcade.draw_text("✗ REJECT", rcx, rcy, reject_fg,
                         font_size=TEXT_SM, font_name=FONT_UI,
                         anchor_x="center", anchor_y="center")
