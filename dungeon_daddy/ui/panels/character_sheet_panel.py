"""Character sheet panel — displays actor state in Play Mode."""
from __future__ import annotations

from dungeon_daddy.rpg.models import ActorState, FalloutRecord


class CharacterSheetPanel:
    def __init__(self) -> None:
        self._actor: ActorState | None = None
        self._fallout: list[FalloutRecord] = []
        self._momentum: int = 0
        self._x = self._y = self._w = self._h = 0.0

    def set_actor(self, actor: ActorState | None) -> None:
        self._actor = actor

    def set_fallout(self, entries: list[FalloutRecord]) -> None:
        self._fallout = list(entries)

    def set_momentum(self, value: int) -> None:
        self._momentum = value

    def setup(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h

    def draw(self) -> None:
        import arcade
        from dungeon_daddy.ui.theme import BG_1, INK_3, FONT_UI, TEXT_SM, PAD_MD

        x, y, w, h = self._x, self._y, self._w, self._h
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_1)

        if self._actor is None:
            arcade.draw_text(
                "No actor selected", x + PAD_MD, y + h / 2,
                INK_3, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
            return

        cur_y = y + h - PAD_MD
        arcade.draw_text(
            f"{self._actor.display_name}  [{self._actor.actor_type}]",
            x + PAD_MD, cur_y, INK_3,
            font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
        )
