from __future__ import annotations

from dungeon_daddy.rpg.models import ActionRequest, ActionResolution, ActorState


class PlayerActionPanel:
    def __init__(self) -> None:
        self._actors: list[ActorState] = []
        self._last_result: dict | None = None
        self._on_resolve = None
        self._actor_idx: int = 0
        self._action_key: str = "fight"
        self._push_yourself: bool = False
        self._momentum_spend: int = 0
        self._all_widgets: list = []
        self._action_btn_refs: dict[str, object] = {}
        self._widget_params: tuple | None = None  # (manager, x, y, w, h)

    def set_actors(self, actors: list[ActorState]) -> None:
        self._actors = actors

    def _build_request(
        self,
        campaign_id: str,
        actor_id: str,
        intent: str,
        action_key: str,
        push_yourself: bool,
        momentum_spend: int,
        dice_pool: int,
    ) -> ActionRequest:
        return ActionRequest(
            campaign_id=campaign_id,
            actor_id=actor_id,
            action_key=action_key,
            dice_pool=dice_pool,
            push_yourself=push_yourself,
            momentum_spend=momentum_spend,
            intent=intent,
        )

    def _format_result(self, resolution: ActionResolution) -> dict:
        return {
            "outcome": resolution.outcome,
            "dice": resolution.dice_rolled,
            "stress_cost": resolution.stress_cost,
            "notes": resolution.notes,
        }

    def store_result(self, summary: dict) -> None:
        self._last_result = summary

    def set_resolve_callback(self, fn) -> None:
        self._on_resolve = fn

    def setup_widget(self, manager: object | None, x: float, y: float, w: float, h: float) -> None:
        if manager is None:
            return
        import arcade
        import arcade.gui
        from dungeon_daddy.ui.theme import (
            BG_2, BG_3, BG_HI, FONT_UI, FONT_UI_MED, FONT_MONO, INK_1, INK_2, INK_3, INK_4,
            LINE, LINE_HI, PAD_MD, TEXT_SM, TEAL,
        )
        self._widget_params = (manager, x, y, w, h)
        self.teardown_widget(manager)

        _ACTION_KEYS = ["fight", "move", "tinker", "study", "focus", "sway", "sense", "channel", "endure"]
        _BTN_H = 22
        _BTN_W = int((w - PAD_MD * 2) / 3) - 2

        def _btn_style(active: bool) -> dict:
            fg = (*TEAL, 255) if active else (*INK_3, 255)
            bg = (*BG_HI, 255) if active else (*BG_2, 255)
            border = (*TEAL, 255) if active else (*LINE, 255)
            return {
                "normal": arcade.gui.UIFlatButton.UIStyle(
                    font_size=8, font_name=FONT_UI,
                    font_color=fg, bg=bg, border=border, border_width=1,
                ),
                "hover": arcade.gui.UIFlatButton.UIStyle(
                    font_size=8, font_name=FONT_UI,
                    font_color=(*INK_1, 255), bg=(*BG_3, 255),
                    border=(*LINE_HI, 255), border_width=1,
                ),
                "press": arcade.gui.UIFlatButton.UIStyle(
                    font_size=8, font_name=FONT_UI,
                    font_color=fg, bg=(*BG_HI, 255), border=border, border_width=1,
                ),
                "disabled": arcade.gui.UIFlatButton.UIStyle(
                    font_size=8, font_name=FONT_UI,
                    font_color=(*INK_4, 255), bg=(*BG_2, 255),
                    border=(*LINE, 255), border_width=1,
                ),
            }

        cur_y = y + h - PAD_MD

        # Actor prev/next buttons (sit on the actor name row)
        _NAV_W = 18
        _NAV_H = 16
        prev_btn = arcade.gui.UIFlatButton(
            x=int(x + w - PAD_MD - _NAV_W * 2 - 2), y=int(cur_y - _NAV_H),
            width=_NAV_W, height=_NAV_H,
            text="<",
            style=_btn_style(False),
        )
        next_btn = arcade.gui.UIFlatButton(
            x=int(x + w - PAD_MD - _NAV_W), y=int(cur_y - _NAV_H),
            width=_NAV_W, height=_NAV_H,
            text=">",
            style=_btn_style(False),
        )

        @prev_btn.event
        def on_click(event) -> None:
            if self._actors:
                self._actor_idx = (self._actor_idx - 1) % len(self._actors)
                if self._widget_params:
                    self.setup_widget(*self._widget_params)

        @next_btn.event
        def on_click(event) -> None:  # type: ignore[no-redef]
            if self._actors:
                self._actor_idx = (self._actor_idx + 1) % len(self._actors)
                if self._widget_params:
                    self.setup_widget(*self._widget_params)

        manager.add(prev_btn)  # type: ignore[union-attr]
        manager.add(next_btn)  # type: ignore[union-attr]
        self._all_widgets.extend([prev_btn, next_btn])

        cur_y -= 18  # actor name row matches draw()

        # Intent input
        intent_h = 24
        cur_y -= 16 + intent_h  # label row + widget
        intent_w = w - PAD_MD * 2
        intent_widget = arcade.gui.UIInputText(
            x=int(x + PAD_MD), y=int(cur_y),
            width=int(intent_w), height=intent_h,
            text="",
            font_name=(FONT_MONO,),
            font_size=TEXT_SM,
            text_color=(*INK_2, 255),
            multiline=False,
        )
        manager.add(intent_widget)  # type: ignore[union-attr]
        self._all_widgets.append(intent_widget)
        self._intent_widget = intent_widget

        cur_y -= PAD_MD + 16

        # Action key grid (3 columns)
        current_actor = self._actors[min(self._actor_idx, len(self._actors) - 1)] if self._actors else None
        ratings = current_actor.actions if current_actor else {}
        col_gap = 2
        for i, key in enumerate(_ACTION_KEYS):
            col = i % 3
            row = i // 3
            bx = x + PAD_MD + col * (_BTN_W + col_gap)
            by = cur_y - row * (_BTN_H + 2)
            rating = ratings.get(key, 0)
            btn = arcade.gui.UIFlatButton(
                x=int(bx), y=int(by),
                width=_BTN_W, height=_BTN_H,
                text=f"{key.upper()} {rating}",
                style=_btn_style(key == self._action_key),
            )
            _key = key
            self._action_btn_refs[key] = btn

            @btn.event
            def on_click(event, k=_key) -> None:
                self._action_key = k
                for bk, b in self._action_btn_refs.items():
                    b.style = _btn_style(bk == k)  # type: ignore[union-attr]

            manager.add(btn)  # type: ignore[union-attr]
            self._all_widgets.append(btn)

        rows = (len(_ACTION_KEYS) + 2) // 3
        cur_y -= rows * (_BTN_H + 2) + PAD_MD

        # Push yourself toggle
        push_w = int(w / 2 - PAD_MD * 1.5)
        push_btn = arcade.gui.UIFlatButton(
            x=int(x + PAD_MD), y=int(cur_y - _BTN_H),
            width=push_w, height=_BTN_H,
            text="PUSH" if not self._push_yourself else "PUSH ✓",
            style=_btn_style(self._push_yourself),
        )

        @push_btn.event
        def on_click(event) -> None:  # type: ignore[no-redef]
            self._push_yourself = not self._push_yourself

        manager.add(push_btn)  # type: ignore[union-attr]
        self._all_widgets.append(push_btn)
        cur_y -= _BTN_H + PAD_MD

        # Resolve button
        resolve_h = 28
        resolve_w = int(w - PAD_MD * 2)
        resolve_btn = arcade.gui.UIFlatButton(
            x=int(x + PAD_MD), y=int(cur_y - resolve_h),
            width=resolve_w, height=resolve_h,
            text="RESOLVE",
            style=_btn_style(False),
        )

        @resolve_btn.event
        def on_click(event) -> None:  # type: ignore[no-redef]
            if not self._on_resolve or not self._actors:
                return
            actor = self._actors[min(self._actor_idx, len(self._actors) - 1)]
            intent = self._intent_widget.text if self._intent_widget else ""  # type: ignore[union-attr]
            dice_pool = max(1, actor.actions.get(self._action_key, 1))
            self._on_resolve(
                campaign_id=actor.campaign_id,
                actor_id=actor.actor_id,
                intent=intent,
                action_key=self._action_key,
                push_yourself=self._push_yourself,
                momentum_spend=self._momentum_spend,
                dice_pool=dice_pool,
            )

        manager.add(resolve_btn)  # type: ignore[union-attr]
        self._all_widgets.append(resolve_btn)
        self._intent_widget = intent_widget

    def teardown_widget(self, manager: object | None) -> None:
        if manager is None:
            return
        for w in self._all_widgets:
            try:
                manager.remove(w)  # type: ignore[union-attr]
            except Exception:
                pass
        self._all_widgets.clear()
        self._action_btn_refs.clear()
        self._intent_widget = None

    def draw(self, x: float, y: float, width: float, height: float) -> None:
        import arcade
        from dungeon_daddy.ui.theme import BG_1, INK_3, INK_4, FONT_UI, FONT_MONO, PAD_MD, TEXT_SM

        _ACTION_KEYS = ["fight", "move", "tinker", "study", "focus", "sway", "sense", "channel", "endure"]

        arcade.draw_rect_filled(arcade.XYWH(x + width / 2, y + height / 2, width, height), BG_1)
        cur_y = y + height - PAD_MD

        # Actor name
        if not self._actors:
            actor_label = "Actor: No actors"
        else:
            idx = min(self._actor_idx, len(self._actors) - 1)
            name = self._actors[idx].display_name
            actor_label = f"Actor: {name}  ({idx + 1}/{len(self._actors)})"
        arcade.draw_text(
            actor_label, x + PAD_MD, cur_y,
            INK_3, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
        )
        cur_y -= 18

        # Intent label (widget floats above)
        arcade.draw_text(
            "Intent:", x + PAD_MD, cur_y,
            INK_4, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
        )
        cur_y -= 16 + 24 + PAD_MD  # label + widget height + gap

        # Action label
        arcade.draw_text(
            "Action:", x + PAD_MD, cur_y,
            INK_4, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
        )
        cur_y -= 16

        # Action key grid labels (drawn under widget buttons)
        rows = (len(_ACTION_KEYS) + 2) // 3
        cur_y -= rows * 24 + PAD_MD * 2 + 28  # action grid + push + resolve

        # Result area
        if self._last_result:
            outcome = self._last_result.get("outcome", "?")
            dice = self._last_result.get("dice", [])
            stress = self._last_result.get("stress_cost", 0)
            arcade.draw_text(
                f"► {outcome.upper()}  dice={dice}  stress={stress}",
                x + PAD_MD, y + PAD_MD + 20,
                INK_3, font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="bottom",
            )
