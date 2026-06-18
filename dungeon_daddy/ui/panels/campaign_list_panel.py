"""Campaign List Panel — center item card list for Campaign Mode."""
from __future__ import annotations

import arcade

from dungeon_daddy.ui.theme import (
    BG_0,
    BG_2,
    BG_3,
    EMBER,
    FONT_MONO,
    FONT_SERIF,
    GOLD,
    INK_1,
    INK_2,
    INK_3,
    INK_4,
    LINE,
    PAD_MD,
    PAD_SM,
    TEAL,
    TEXT_2XL,
    TEXT_BASE,
    TEXT_SM,
    TEAL_DIM,
    VIOLET,
    VIOLET_DIM,
    draw_chip,
    draw_kicker,
    draw_rounded_rect,
)

HEADER_H: float = 38
CARD_H: float = 80
GAP: float = 8
DELETE_ZONE_SIZE: float = 20
DELETE_ZONE_MARGIN: float = 8

_ADD_BTN_W: float = 70.0
_ADD_BTN_H: float = 22.0
_ADD_BTN_PAD: float = 8.0

# Back affordance occupies the left portion of the header (breadcrumb text).
_BACK_ZONE_W: float = 200.0

# Actor type → chip colour key
_ACTOR_CHIP: dict[str, str] = {
    "pc": "violet",
    "npc": "teal",
    "monster": "ember",
    "dungeon": "ember",
    "dungeon_presence": "ember",
}

_REPUTATION_CHIP: dict[str, str] = {
    "hostile": "ember",
    "cold": "default",
    "neutral": "default",
    "warm": "teal",
    "allied": "gold",
}

_TIER_LABELS = ["Fringe", "Established", "Influential", "Powerful", "Dominant"]

_SECTION_LABELS: dict[str, str] = {
    "player_side": "PLAYER SIDE",
    "monsters":    "MONSTERS",
    "npcs":        "NPCS",
    "factions":    "FACTIONS",
    "clocks":      "CLOCKS",
    "threats":     "THREATS",
    "lore":        "LORE",
    "rooms":       "ROOMS",
    "validation":  "VALIDATION",
}


class CampaignListPanel:
    def __init__(self) -> None:
        self._x = self._y = self._w = self._h = 0.0
        self._item_count: int = 0
        self._scroll_offset: float = 0.0

    def set_bounds(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h

    def set_item_count(self, count: int) -> None:
        self._item_count = count

    def set_scroll_offset(self, offset: float) -> None:
        self._scroll_offset = offset

    def _card_top(self, index: int) -> float:
        top_of_list = self._y + self._h - HEADER_H
        return top_of_list - index * (CARD_H + GAP) + self._scroll_offset

    # ------------------------------------------------------------------
    # Hit-test helpers
    # ------------------------------------------------------------------

    def item_at(self, x: float, y: float) -> int | None:
        if self._item_count == 0:
            return None
        if not (self._x <= x <= self._x + self._w):
            return None
        for i in range(self._item_count):
            card_top = self._card_top(i)
            card_bot = card_top - CARD_H
            if card_bot <= y <= card_top:
                return i
        return None

    def delete_zone_at(self, x: float, y: float) -> int | None:
        right = self._x + self._w
        zone_x_left = right - DELETE_ZONE_MARGIN - DELETE_ZONE_SIZE
        zone_x_right = right - DELETE_ZONE_MARGIN
        if not (zone_x_left <= x <= zone_x_right):
            return None
        for i in range(self._item_count):
            card_top = self._card_top(i)
            zone_y_top = card_top - DELETE_ZONE_MARGIN
            zone_y_bot = zone_y_top - DELETE_ZONE_SIZE
            if zone_y_bot <= y <= zone_y_top:
                return i
        return None

    def add_btn_at(self, x: float, y: float) -> bool:
        right = self._x + self._w
        cx = right - _ADD_BTN_PAD - _ADD_BTN_W / 2
        cy = self._y + self._h - HEADER_H / 2
        return (cx - _ADD_BTN_W / 2 <= x <= cx + _ADD_BTN_W / 2 and
                cy - _ADD_BTN_H / 2 <= y <= cy + _ADD_BTN_H / 2)

    def back_btn_at(self, x: float, y: float) -> bool:
        """Hit-test the breadcrumb/back zone in the left of the header strip."""
        header_top = self._y + self._h
        header_bot = header_top - HEADER_H
        if not (header_bot <= y <= header_top):
            return False
        return self._x <= x <= self._x + _BACK_ZONE_W

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(
        self,
        section: str | None,
        items: list,
        hovered_index: int | None = None,
        breadcrumb: str | None = None,
    ) -> None:
        px, py, pw, ph = self._x, self._y, self._w, self._h

        # Panel background
        arcade.draw_rect_filled(arcade.XYWH(px + pw / 2, py + ph / 2, pw, ph), BG_0)

        # Header strip
        header_cy = py + ph - HEADER_H / 2
        arcade.draw_rect_filled(arcade.XYWH(px + pw / 2, header_cy, pw, HEADER_H), BG_2)

        if breadcrumb:
            # Drill-down view: show a clickable back/breadcrumb in the kicker spot.
            arcade.draw_text(
                f"‹ {breadcrumb}", px + PAD_MD, header_cy, TEAL,
                font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="left", anchor_y="center",
            )
        else:
            section_label = _SECTION_LABELS.get(section or "", "")
            if section_label:
                draw_kicker(section_label, px + PAD_MD, header_cy)

        # "+ ADD" button in header
        right = px + pw
        add_cx = right - _ADD_BTN_PAD - _ADD_BTN_W / 2
        add_cy = header_cy
        arcade.draw_rect_filled(arcade.XYWH(add_cx, add_cy, _ADD_BTN_W, _ADD_BTN_H), BG_2)
        arcade.draw_rect_outline(arcade.XYWH(add_cx, add_cy, _ADD_BTN_W, _ADD_BTN_H), TEAL, 1)
        arcade.draw_text(
            "+ ADD", add_cx, add_cy, TEAL,
            font_size=TEXT_SM, font_name=FONT_MONO,
            anchor_x="center", anchor_y="center",
        )

        if not section or not items:
            # Empty state placeholder
            mid_x = px + pw / 2
            mid_y = py + (ph - HEADER_H) / 2
            arcade.draw_text(
                "No items" if section else "Select a section",
                mid_x, mid_y, INK_4,
                font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="center", anchor_y="center", italic=True,
            )
            return

        card_x = px + PAD_MD
        card_w = pw - 2 * PAD_MD
        panel_top = py + ph - HEADER_H
        panel_bot = py

        ctx = arcade.get_window().ctx
        old_scissor = ctx.scissor
        ctx.scissor = (int(px), int(py), int(pw), int(ph - HEADER_H))
        try:
            for i, item in enumerate(items):
                card_top = self._card_top(i)
                card_bot = card_top - CARD_H
                if card_top < panel_bot or card_bot > panel_top:
                    continue
                card_cy = (card_top + card_bot) / 2
                self._draw_card(
                    section, item, i,
                    card_x, card_cy, card_w, CARD_H,
                    hovered=(i == hovered_index),
                )
        finally:
            ctx.scissor = old_scissor

    def _draw_card(
        self,
        section: str,
        item: object,
        index: int,
        x: float, cy: float, w: float, h: float,
        hovered: bool,
    ) -> None:
        cx = x + w / 2
        draw_rounded_rect(cx, cy, w, h, 6, BG_2, LINE, 1)

        if section == "factions":
            self._draw_faction_card(item, x, cy, w, h, hovered)
        elif section in ("player_side", "monsters", "npcs"):
            self._draw_actor_card(item, x, cy, w, h, hovered)
        elif section == "clocks":
            self._draw_clock_card(item, x, cy, w, h, hovered)
        elif section == "threats":
            self._draw_threat_card(item, x, cy, w, h, hovered)
        elif section == "lore":
            self._draw_lore_card(item, x, cy, w, h, hovered)
        elif section == "rooms":
            if hasattr(item, "archetype"):  # RoomObjectManifest
                self._draw_room_object_card(item, x, cy, w, h, hovered)
            else:  # Room from dungeon
                self._draw_room_card(item, x, cy, w, h)
        elif section == "validation":
            self._draw_validation_card(item, x, cy, w, h)

        if hovered:
            # Delete ✕ top-right corner
            right = x + w
            zx = right - DELETE_ZONE_MARGIN - DELETE_ZONE_SIZE / 2
            zy = cy + h / 2 - DELETE_ZONE_MARGIN - DELETE_ZONE_SIZE / 2
            arcade.draw_text(
                "✕", zx, zy, EMBER,
                font_size=TEXT_BASE, font_name=FONT_MONO,
                anchor_x="center", anchor_y="center",
            )

    def _draw_actor_card(
        self, actor: object, x: float, cy: float, w: float, h: float, hovered: bool,
    ) -> None:
        top = cy + h / 2
        name = getattr(actor, "display_name", "?")
        atype = getattr(actor, "actor_type", "pc")
        status = getattr(actor, "status", "active")
        concept = getattr(actor, "concept", None) or ""

        # Name
        arcade.draw_text(
            name, x + PAD_MD, top - 18,
            INK_1, font_size=TEXT_2XL, font_name=FONT_SERIF,
            anchor_x="left", anchor_y="center",
        )

        # Type chip
        chip_color = _ACTOR_CHIP.get(atype, "default")
        draw_chip(atype.upper(), x + w - PAD_MD - 52, top - 18, chip_color, width=64)

        # Status dot + text
        status_color = TEAL if status == "active" else (EMBER if status in ("dead", "lost") else INK_4)
        arcade.draw_text(
            f"● {status}", x + PAD_MD, top - 38,
            status_color, font_size=TEXT_SM, font_name=FONT_MONO,
            anchor_x="left", anchor_y="center",
        )

        # Concept (one line, truncated)
        if concept:
            max_chars = int(w / 7)
            truncated = concept[:max_chars] + "…" if len(concept) > max_chars else concept
            arcade.draw_text(
                truncated, x + PAD_MD, top - 56,
                INK_3, font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="left", anchor_y="center", italic=True,
            )

        # Action ratings row
        ratings = getattr(actor, "action_ratings", {})
        if ratings:
            parts = [f"{k[:5]}{'●' * v}" for k, v in list(ratings.items())[:5]]
            arcade.draw_text(
                "  ".join(parts), x + PAD_MD, top - 72,
                INK_3, font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="left", anchor_y="center",
            )

    def _draw_faction_card(
        self, faction: object, x: float, cy: float, w: float, h: float, hovered: bool,
    ) -> None:
        top = cy + h / 2
        name = getattr(faction, "display_name", "?")
        reputation = getattr(faction, "reputation", "neutral")
        tier = int(getattr(faction, "tier", 0))
        concept = getattr(faction, "concept", None) or ""

        arcade.draw_text(
            name, x + PAD_MD, top - 18,
            INK_1, font_size=TEXT_2XL, font_name=FONT_SERIF,
            anchor_x="left", anchor_y="center",
        )

        draw_chip("FACTION", x + w - PAD_MD - 52, top - 18, "gold", width=64)

        rep_color = _REPUTATION_CHIP.get(reputation, "default")
        draw_chip(reputation.upper(), x + PAD_MD + 36, top - 40, rep_color, width=72)

        tier_label = _TIER_LABELS[max(0, min(4, tier))]
        arcade.draw_text(
            tier_label, x + PAD_MD + 80, top - 40,
            INK_3, font_size=TEXT_SM, font_name=FONT_MONO,
            anchor_x="left", anchor_y="center",
        )

        if concept:
            max_chars = int(w / 7)
            truncated = concept[:max_chars] + "…" if len(concept) > max_chars else concept
            arcade.draw_text(
                truncated, x + PAD_MD, top - 60,
                INK_3, font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="left", anchor_y="center", italic=True,
            )

    def _draw_clock_card(
        self, clock: object, x: float, cy: float, w: float, h: float, hovered: bool,
    ) -> None:
        top = cy + h / 2
        label = getattr(clock, "label", "?")
        segments = getattr(clock, "segments", 6)
        filled = getattr(clock, "filled", 0)
        level = getattr(clock, "clock_level", "dungeon")

        arcade.draw_text(
            label, x + PAD_MD, top - 18,
            INK_1, font_size=TEXT_2XL, font_name=FONT_SERIF,
            anchor_x="left", anchor_y="center",
        )
        draw_chip(level.upper(), x + w - PAD_MD - 52, top - 18, "violet", width=64)

        # Pip row
        pip_x = x + PAD_MD
        pip_y = top - 44
        pip_r = 4
        pip_gap = 10
        for seg in range(segments):
            if seg < filled:
                arcade.draw_circle_filled(pip_x, pip_y, pip_r, TEAL)  # type: ignore[arg-type]
            else:
                arcade.draw_circle_outline(pip_x, pip_y, pip_r, INK_4, 1)  # type: ignore[arg-type]
            pip_x += pip_gap + pip_r * 2

    def _draw_threat_card(
        self, threat: object, x: float, cy: float, w: float, h: float, hovered: bool,
    ) -> None:
        top = cy + h / 2
        if isinstance(threat, dict):
            loc = threat.get("location_slug", "")
            desc = threat.get("description", "")
        else:
            loc = getattr(threat, "location_slug", "")
            desc = getattr(threat, "description", "")

        arcade.draw_text(
            (loc or "?").upper(), x + PAD_MD, top - 18,
            INK_3, font_size=TEXT_SM, font_name=FONT_MONO,
            anchor_x="left", anchor_y="center",
        )
        max_chars = int(w / 7)
        desc_short = desc[:max_chars] + "…" if len(desc) > max_chars else desc
        arcade.draw_text(
            desc_short, x + PAD_MD, top - 40,
            INK_2, font_size=TEXT_BASE, font_name=FONT_SERIF,
            anchor_x="left", anchor_y="center",
        )

    def _draw_lore_card(
        self, text: object, x: float, cy: float, w: float, h: float, hovered: bool,
    ) -> None:
        # Gold left accent bar (blockquote style)
        arcade.draw_rect_filled(arcade.XYWH(x + 3, cy, 2, h - 8), GOLD)
        max_chars = int((w - PAD_MD * 2) / 7)
        snippet = str(text)
        snippet = snippet[:max_chars] + "…" if len(snippet) > max_chars else snippet
        arcade.draw_text(
            snippet, x + PAD_MD + 8, cy,
            INK_2, font_size=TEXT_BASE, font_name=FONT_SERIF,
            anchor_x="left", anchor_y="center", italic=True,
        )

    def _draw_validation_card(
        self, error: object, x: float, cy: float, w: float, h: float,
    ) -> None:
        msg = str(getattr(error, "message", error))
        max_chars = int((w - PAD_MD * 2) / 7)
        msg_short = msg[:max_chars] + "…" if len(msg) > max_chars else msg
        arcade.draw_text(
            msg_short, x + PAD_MD, cy,
            EMBER, font_size=TEXT_SM, font_name=FONT_MONO,
            anchor_x="left", anchor_y="center",
        )

    def _draw_room_card(
        self, room: object, x: float, cy: float, w: float, h: float,
    ) -> None:
        top = cy + h / 2
        name = str(getattr(room, "name", "?"))
        room_id = str(getattr(room, "id", ""))
        arcade.draw_text(
            name, x + PAD_MD, top - 18,
            INK_1, font_size=TEXT_2XL, font_name=FONT_SERIF,
            anchor_x="left", anchor_y="center",
        )
        arcade.draw_text(
            room_id, x + PAD_MD, top - 40,
            INK_3, font_size=TEXT_SM, font_name=FONT_MONO,
            anchor_x="left", anchor_y="center",
        )

    def _draw_room_object_card(
        self, obj: object, x: float, cy: float, w: float, h: float, hovered: bool,
    ) -> None:
        top = cy + h / 2
        name = str(getattr(obj, "display_name", "?"))
        archetype = str(getattr(obj, "archetype", ""))
        state = str(getattr(obj, "current_state", getattr(obj, "initial_state", "")))
        arcade.draw_text(
            name, x + PAD_MD, top - 18,
            INK_1, font_size=TEXT_2XL, font_name=FONT_SERIF,
            anchor_x="left", anchor_y="center",
        )
        draw_chip(archetype.upper(), x + w - PAD_MD - 52, top - 18, "teal", width=80)
        arcade.draw_text(
            state, x + PAD_MD, top - 40,
            INK_3, font_size=TEXT_SM, font_name=FONT_MONO,
            anchor_x="left", anchor_y="center",
        )
