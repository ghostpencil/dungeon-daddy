"""Fallout panel — displays active fallout entries in Play Mode."""
from __future__ import annotations

from dungeon_daddy.rpg.models import FalloutRecord


class FalloutPanel:
    def __init__(self) -> None:
        self._entries: list[FalloutRecord] = []
        self._x = self._y = self._w = self._h = 0.0

    def set_entries(self, entries: list[FalloutRecord]) -> None:
        self._entries = list(entries)

    def setup(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h

    def draw(self) -> None:
        import arcade
        from dungeon_daddy.ui.theme import BG_1, INK_3, FONT_UI, TEXT_SM, PAD_MD

        x, y, w, h = self._x, self._y, self._w, self._h
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_1)

        active = [e for e in self._entries if e.status == "active"]
        if not active:
            arcade.draw_text(
                "No active fallout", x + PAD_MD, y + h / 2,
                INK_3, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
            return

        cur_y = y + h - PAD_MD
        for entry in active:
            path_label = entry.markdown_path or "—"
            arcade.draw_text(
                f"[{entry.track_key}] {entry.title}  {entry.severity}  {entry.status}  {path_label}",
                x + PAD_MD, cur_y,
                INK_3, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
            )
            cur_y -= 20
