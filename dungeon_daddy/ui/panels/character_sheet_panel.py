"""Character sheet panel — displays actor state in Play Mode."""
from __future__ import annotations

from dungeon_daddy.rpg.models import ActorState, FalloutRecord

_ACTION_ORDER = [
    "fight", "move", "tinker", "study",
    "focus", "sway", "sense", "channel", "endure",
]
_PIP_W = 10
_PIP_H = 8
_PIP_GAP = 3


class CharacterSheetPanel:
    def __init__(self) -> None:
        self._actor: ActorState | None = None
        self._fallout: list[FalloutRecord] = []
        self._momentum: int = 0
        self._kits: list[dict] = []
        self._dungeon_items: list[dict] = []
        self._equipped: list[dict] = []
        self._x = self._y = self._w = self._h = 0.0

    def set_actor(self, actor: ActorState | None) -> None:
        self._actor = actor

    def set_fallout(self, entries: list[FalloutRecord]) -> None:
        self._fallout = list(entries)

    def set_momentum(self, value: int) -> None:
        self._momentum = value

    def set_inventory(
        self,
        kits: list[dict],
        dungeon_items: list[dict],
        equipped: list[dict],
    ) -> None:
        self._kits = list(kits)
        self._dungeon_items = list(dungeon_items)
        self._equipped = list(equipped)

    def setup(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h

    def draw(self) -> None:
        import arcade
        from dungeon_daddy.ui.theme import (
            BG_1, BG_2, BG_3,
            EMBER, INK_1, INK_2, INK_3, INK_4,
            TEAL, VIOLET,
            FONT_UI, TEXT_SM, TEXT_MD, PAD_MD, PAD_SM,
        )

        x, y, w, h = self._x, self._y, self._w, self._h
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_1)

        if self._actor is None:
            arcade.draw_text(
                "No actor selected", x + PAD_MD, y + h / 2,
                INK_3, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
            return

        cur_y = y + h - PAD_MD

        # --- Actor name + type ---
        arcade.draw_text(
            self._actor.display_name,
            x + PAD_MD, cur_y, INK_1,
            font_size=TEXT_MD, font_name=FONT_UI, bold=True, anchor_y="top",
        )
        cur_y -= TEXT_MD + PAD_SM
        arcade.draw_text(
            f"[{self._actor.actor_type}]",
            x + PAD_MD, cur_y, INK_3,
            font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
        )
        cur_y -= TEXT_SM + PAD_MD

        # --- Stress tracks ---
        if self._actor.stress:
            arcade.draw_text(
                "STRESS", x + PAD_MD, cur_y, TEAL,
                font_size=TEXT_SM, font_name=FONT_UI, bold=True, anchor_y="top",
            )
            cur_y -= TEXT_SM + PAD_SM

            for track in self._actor.stress.values():
                label = track.track_key.upper()
                filled = track.filled
                capacity = track.capacity
                at_max = filled >= capacity

                arcade.draw_text(
                    f"{label}  {filled}/{capacity}",
                    x + PAD_MD, cur_y, INK_2 if not at_max else EMBER,
                    font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
                )
                cur_y -= TEXT_SM + 2

                # pip row
                pip_x = x + PAD_MD
                pip_y = cur_y - _PIP_H
                for i in range(capacity):
                    if i < filled:
                        pip_color = EMBER if at_max else TEAL
                    else:
                        pip_color = BG_3
                    arcade.draw_rect_filled(
                        arcade.XYWH(pip_x + _PIP_W / 2, pip_y + _PIP_H / 2, _PIP_W, _PIP_H),
                        pip_color,
                    )
                    pip_x += _PIP_W + _PIP_GAP

                cur_y -= _PIP_H + PAD_SM

        cur_y -= PAD_SM

        # --- Action ratings ---
        if self._actor.actions:
            arcade.draw_text(
                "ACTIONS", x + PAD_MD, cur_y, VIOLET,
                font_size=TEXT_SM, font_name=FONT_UI, bold=True, anchor_y="top",
            )
            cur_y -= TEXT_SM + PAD_SM

            col_w = (w - PAD_MD * 2) / 3
            col = 0
            row_x = x + PAD_MD
            row_y = cur_y

            for key in _ACTION_ORDER:
                rating = self._actor.actions.get(key, 0)
                color = INK_2 if rating > 0 else INK_4
                label = f"{key.upper()[:3]}  {rating}"
                ax = row_x + col * col_w
                arcade.draw_text(
                    label, ax, row_y, color,
                    font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
                )
                col += 1
                if col >= 3:
                    col = 0
                    row_y -= TEXT_SM + PAD_SM

        cur_y = row_y - PAD_MD * 2 if self._actor.actions else cur_y - PAD_SM

        # --- Class kits ---
        if self._kits:
            arcade.draw_text(
                "KITS", x + PAD_MD, cur_y, TEAL,
                font_size=TEXT_SM, font_name=FONT_UI, bold=True, anchor_y="top",
            )
            cur_y -= TEXT_SM + PAD_SM

            for kit in self._kits:
                cur_c = kit.get("charges_current", 0)
                max_c = kit.get("charges_max", 0)
                at_max = cur_c >= max_c
                arcade.draw_text(
                    kit.get("display_name", kit.get("slug", "")),
                    x + PAD_MD, cur_y, INK_2,
                    font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
                )
                cur_y -= TEXT_SM + 2

                pip_x = x + PAD_MD
                pip_y = cur_y - _PIP_H
                for i in range(max_c):
                    pip_color = TEAL if i < cur_c else (EMBER if at_max else BG_3)
                    arcade.draw_rect_filled(
                        arcade.XYWH(pip_x + _PIP_W / 2, pip_y + _PIP_H / 2, _PIP_W, _PIP_H),
                        pip_color,
                    )
                    pip_x += _PIP_W + _PIP_GAP
                cur_y -= _PIP_H + PAD_SM

        # --- Dungeon items ---
        if self._dungeon_items:
            cur_y -= PAD_SM
            arcade.draw_text(
                "ITEMS", x + PAD_MD, cur_y, INK_2,
                font_size=TEXT_SM, font_name=FONT_UI, bold=True, anchor_y="top",
            )
            cur_y -= TEXT_SM + PAD_SM

            for item in self._dungeon_items:
                name = item.get("display_name", item.get("slug", ""))
                status = item.get("status", "active")
                level_bound = item.get("level_bound", False)
                suffix = " [L]" if level_bound else ""
                color = INK_3 if status != "active" else INK_2
                arcade.draw_text(
                    f"{name}{suffix}",
                    x + PAD_MD, cur_y, color,
                    font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
                )
                cur_y -= TEXT_SM + PAD_SM

        # --- Equipped gear ---
        if self._equipped:
            cur_y -= PAD_SM
            arcade.draw_text(
                "GEAR", x + PAD_MD, cur_y, VIOLET,
                font_size=TEXT_SM, font_name=FONT_UI, bold=True, anchor_y="top",
            )
            cur_y -= TEXT_SM + PAD_SM

            for gear in self._equipped:
                name = gear.get("display_name", gear.get("slug", ""))
                arcade.draw_text(
                    name, x + PAD_MD, cur_y, INK_2,
                    font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
                )
                cur_y -= TEXT_SM + 2

                for feat in gear.get("features", []):
                    ftype = feat.get("feature_type", "")
                    action = feat.get("action_key", "").upper()
                    if ftype == "rating_modifier":
                        mod = feat.get("modifier", 0)
                        sign = "+" if mod >= 0 else ""
                        badge = f"  {action} {sign}{mod}"
                    else:
                        badge = f"  {action} [new]"
                    arcade.draw_text(
                        badge, x + PAD_MD, cur_y, INK_3,
                        font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
                    )
                    cur_y -= TEXT_SM + 2
                cur_y -= PAD_SM
