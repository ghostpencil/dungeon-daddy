"""Memory inspector panel — search and browse memory entries in Play Mode."""
from __future__ import annotations

from dungeon_daddy.memory.models import MemoryEntry

_BOX_H = 26.0


class MemoryInspectorPanel:
    def __init__(self) -> None:
        self._entries: list[MemoryEntry] = []
        self._search_query: str = ""
        self._selected: MemoryEntry | None = None
        self._sync_warnings: set[str] = set()
        self._x = self._y = self._w = self._h = 0.0
        self._widget: object | None = None  # arcade.gui.UIInputText when live

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

    def set_sync_warnings(self, memory_ids: set[str]) -> None:
        self._sync_warnings = set(memory_ids)

    def has_sync_warning(self, memory_id: str) -> bool:
        return memory_id in self._sync_warnings

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
            BG_1, BG_2, INK_3, INK_4, LINE, FONT_UI, FONT_MONO, TEXT_SM, PAD_MD,
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
            # Draw placeholder when the widget is empty
            if not self._search_query:
                arcade.draw_text(
                    "search tag / actor / location",
                    box_x + 4, box_cy,
                    INK_4, font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="center",
                )
        else:
            # Draw a non-interactive fallback box when widget is not wired
            arcade.draw_rect_filled(arcade.XYWH(box_cx, box_cy, box_w, _BOX_H), BG_2)
            arcade.draw_rect_outline(arcade.XYWH(box_cx, box_cy, box_w, _BOX_H), LINE, 1)
            label = self._search_query if self._search_query else "search tag / actor / location"
            label_color = INK_3 if self._search_query else INK_4
            arcade.draw_text(
                label, box_x + 4, box_cy,
                label_color, font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="center",
            )

        # Results list
        list_top = y + h - PAD_MD - _BOX_H - PAD_MD
        results = self.get_results()
        if not results:
            arcade.draw_text(
                "No memories found", x + PAD_MD, list_top - _BOX_H / 2,
                INK_4, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
            return

        cur_y = list_top
        for entry in results:
            warning = " ⚠" if self.has_sync_warning(entry.memory_id) else ""
            arcade.draw_text(
                f"{entry.title}{warning}", x + PAD_MD, cur_y,
                INK_3, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
            )
            cur_y -= 20
