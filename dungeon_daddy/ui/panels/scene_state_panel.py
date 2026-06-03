"""Scene state panel — displays scene context in Play Mode."""
from __future__ import annotations

from dungeon_daddy.rpg.models import ActionResolution, ActorState, ClockState


class SceneStatePanel:
    def __init__(self) -> None:
        self._scene_title: str | None = None
        self._location_slug: str | None = None
        self._clocks: list[ClockState] = []
        self._actors: list[ActorState] = []
        self._recent_resolutions: list[ActionResolution] = []
        self._risk: str = "moderate"
        self._effect: str = "standard"
        self._x = self._y = self._w = self._h = 0.0

    def set_scene(self, title: str | None, location_slug: str | None) -> None:
        self._scene_title = title
        self._location_slug = location_slug

    def set_clocks(self, clocks: list[ClockState]) -> None:
        self._clocks = list(clocks)

    def set_actors(self, actors: list[ActorState]) -> None:
        self._actors = list(actors)

    def set_recent_resolutions(self, resolutions: list[ActionResolution]) -> None:
        self._recent_resolutions = list(resolutions)

    def set_risk(self, risk: str) -> None:
        self._risk = risk

    def set_effect(self, effect: str) -> None:
        self._effect = effect

    def setup(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h

    def draw(self) -> None:
        import arcade
        from dungeon_daddy.ui.theme import BG_1, INK_3, FONT_UI, TEXT_SM, PAD_MD

        x, y, w, h = self._x, self._y, self._w, self._h
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_1)

        if self._scene_title is None:
            arcade.draw_text(
                "No scene active", x + PAD_MD, y + h / 2,
                INK_3, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
            return

        arcade.draw_text(
            f"{self._scene_title}  [{self._location_slug}]",
            x + PAD_MD, y + h - PAD_MD,
            INK_3, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
        )
