"""Campaign Edit Panel — right-side form panel for Campaign Mode."""
from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

import arcade
import arcade.gui

from dungeon_daddy.rpg.playbook import PlaybookLibrary
from dungeon_daddy.ui.theme import (
    BG_1,
    BG_2,
    BG_3,
    BG_HI,
    FONT_MONO,
    FONT_UI_MED,
    INK_1,
    INK_2,
    INK_3,
    INK_4,
    LINE,
    LINE_HI,
    PAD_SM,
    TEAL,
    TEXT_BASE,
    TEXT_SM,
)

_log = logging.getLogger(__name__)

_FIELD_H = 26

_DEFAULT_TRANSITIONS: dict[str, list[dict[str, str]]] = {
    "container": [
        {"from_state": "sealed", "to_state": "opened", "trigger": "open"},
        {"from_state": "sealed", "to_state": "locked", "trigger": "lock"},
        {"from_state": "locked", "to_state": "unlocked", "trigger": "unlock"},
        {"from_state": "unlocked", "to_state": "opened", "trigger": "open"},
        {"from_state": "locked", "to_state": "broken", "trigger": "force"},
    ],
    "door": [
        {"from_state": "closed", "to_state": "open", "trigger": "open"},
        {"from_state": "open", "to_state": "closed", "trigger": "close"},
        {"from_state": "locked", "to_state": "unlocked", "trigger": "unlock"},
        {"from_state": "unlocked", "to_state": "open", "trigger": "open"},
        {"from_state": "locked", "to_state": "broken", "trigger": "force"},
    ],
    "mechanism": [
        {"from_state": "inactive", "to_state": "activated", "trigger": "activate"},
        {"from_state": "on", "to_state": "off", "trigger": "toggle"},
        {"from_state": "off", "to_state": "on", "trigger": "toggle"},
    ],
    "structure": [
        {"from_state": "intact", "to_state": "damaged", "trigger": "damage"},
        {"from_state": "damaged", "to_state": "destroyed", "trigger": "damage"},
        {"from_state": "intact", "to_state": "activated", "trigger": "activate"},
    ],
    "trap": [
        {"from_state": "armed", "to_state": "triggered", "trigger": "trigger"},
        {"from_state": "triggered", "to_state": "spent", "trigger": "reset"},
        {"from_state": "armed", "to_state": "disarmed", "trigger": "disarm"},
    ],
    "lore_fixture": [
        {"from_state": "unexamined", "to_state": "examined", "trigger": "examine"},
    ],
    "resource": [
        {"from_state": "available", "to_state": "depleted", "trigger": "use"},
    ],
}


def default_transitions_for_archetype(archetype: str) -> list[dict[str, str]]:
    """Return default state machine transitions for the given archetype (empty list if unknown)."""
    return list(_DEFAULT_TRANSITIONS.get(archetype, []))
_FIELD_GAP = 8
_LABEL_H = 12
_LABEL_GAP = 3
_ROW_H = 22       # compact input height for action/stress rows
_ROW_GAP = 4
_ROW_LABEL_W = 80  # px width of inline label column for action/stress rows
_BTN_H = 26
_BTN_W = 80

_ACTION_KEYS = ["fight", "move", "tinker", "study", "focus", "sway", "sense", "channel", "endure"]
_STRESS_KEYS = ["body", "composure", "bonds", "weird"]
_PLAYBOOK_NONE = "none"
_REPUTATION_TIERS = ["hostile", "cold", "neutral", "warm", "allied"]
# Archetype order matches the RoomObjectManifest.archetype Literal.
_ARCHETYPES = ["container", "door", "mechanism", "structure", "trap", "lore_fixture", "resource"]


def _slugify(text: str) -> str:
    """Lowercase kebab-case slug derived from free text (e.g. 'Iron Chest' -> 'iron-chest')."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _btn_style(variant: str) -> dict[str, Any]:
    if variant == "teal":
        fg = (*TEAL, 255)
        border = (*TEAL, 255)
    else:
        fg = (*INK_2, 255)
        border = (*LINE, 255)
    return {
        "normal": arcade.gui.UIFlatButton.UIStyle(
            font_size=TEXT_SM, font_name=FONT_UI_MED,
            font_color=fg, bg=(*BG_2, 255),
            border=border, border_width=1,
        ),
        "hover": arcade.gui.UIFlatButton.UIStyle(
            font_size=TEXT_SM, font_name=FONT_UI_MED,
            font_color=(*INK_1, 255), bg=(*BG_3, 255),
            border=(*LINE_HI, 255), border_width=1,
        ),
        "press": arcade.gui.UIFlatButton.UIStyle(
            font_size=TEXT_SM, font_name=FONT_UI_MED,
            font_color=fg, bg=(*BG_HI, 255),
            border=border, border_width=1,
        ),
        "disabled": arcade.gui.UIFlatButton.UIStyle(
            font_size=TEXT_SM, font_name=FONT_UI_MED,
            font_color=(*INK_4, 255), bg=(*BG_2, 255),
            border=(*LINE, 255), border_width=1,
        ),
    }


class CampaignEditPanel:
    """Right-side form panel.  Owns UIManager widgets for the active form."""

    def __init__(self) -> None:
        self._x = self._y = self._w = self._h = 0.0
        self._manager: arcade.gui.UIManager | None = None
        self._widgets: list[arcade.gui.UIWidget] = []
        self.mode: str = "none"
        self._on_save: Callable[[dict[str, Any]], None] | None = None
        self._on_cancel: Callable[[], None] | None = None
        self._inputs: dict[str, arcade.gui.UIInputText] = {}
        # (text, center_y, color) tuples drawn each frame by draw()
        self._labels: list[tuple[str, float, tuple[Any, ...]]] = []
        # Extra data merged into _collect_inputs() (e.g. actor_type)
        self._extra_data: dict[str, Any] = {}
        # Number-picker state: value and draw position for each numeric field
        self._number_values: dict[str, int] = {}
        self._number_label_centers: dict[str, tuple[float, float]] = {}
        # Choice-picker state: current index, option labels, and draw position
        self._choice_values: dict[str, int] = {}
        self._choice_options: dict[str, list[str]] = {}
        self._choice_label_centers: dict[str, tuple[float, float]] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setup(
        self,
        manager: arcade.gui.UIManager,
        x: float,
        y: float,
        w: float,
        h: float,
    ) -> None:
        self._manager = manager
        self._x, self._y, self._w, self._h = x, y, w, h

    def resize(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h
        # Widgets are fixed-position; rebuild on next show_* call.
        self.clear()

    # ------------------------------------------------------------------
    # Public show-form entry points
    # ------------------------------------------------------------------

    def show_actor(
        self,
        actor: object,
        on_save: Callable[[dict[str, Any]], None],
        on_cancel: Callable[[], None],
        *,
        is_new: bool = False,
    ) -> None:
        self.clear()
        self.mode = "new_actor" if is_new else "actor"
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._build_actor_form(actor)

    def show_clock(
        self,
        clock: object,
        on_save: Callable[[dict[str, Any]], None],
        on_cancel: Callable[[], None],
        *,
        is_new: bool = False,
    ) -> None:
        self.clear()
        self.mode = "new_clock" if is_new else "clock"
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._build_clock_form(clock)

    def show_lore(
        self,
        text: str,
        on_save: Callable[[dict[str, Any]], None],
        on_cancel: Callable[[], None],
        *,
        is_new: bool = False,
    ) -> None:
        self.clear()
        self.mode = "new_lore" if is_new else "lore"
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._build_lore_form(text)

    def show_faction(
        self,
        faction: object,
        on_save: Callable[[dict[str, Any]], None],
        on_cancel: Callable[[], None],
        *,
        is_new: bool = False,
    ) -> None:
        self.clear()
        self.mode = "new_faction" if is_new else "faction"
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._build_faction_form(faction)

    def show_threat(
        self,
        threat: dict[str, Any],
        on_save: Callable[[dict[str, Any]], None],
        on_cancel: Callable[[], None],
        *,
        is_new: bool = False,
    ) -> None:
        self.clear()
        self.mode = "new_threat" if is_new else "threat"
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._build_threat_form(threat)

    def show_room_object(
        self,
        obj: object,
        on_save: Callable[[dict[str, Any]], None],
        on_cancel: Callable[[], None],
        *,
        is_new: bool = False,
    ) -> None:
        self.clear()
        self.mode = "new_room_object" if is_new else "room_object"
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._build_room_object_form(obj)

    def clear(self) -> None:
        for widget in self._widgets:
            try:
                assert self._manager is not None
                self._manager.remove(widget)
            except Exception:
                pass
        self._widgets.clear()
        self._inputs.clear()
        self._labels.clear()
        self._extra_data.clear()
        self._number_values.clear()
        self._number_label_centers.clear()
        self._choice_values.clear()
        self._choice_options.clear()
        self._choice_label_centers.clear()
        self.mode = "none"

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self) -> None:
        """Draw the panel background, labels, and placeholder when no form is open."""
        px, py, pw, ph = self._x, self._y, self._w, self._h
        arcade.draw_rect_filled(arcade.XYWH(px + pw / 2, py + ph / 2, pw, ph), BG_1)

        if self.mode == "none":
            arcade.draw_text(
                "Select an item to edit",
                px + pw / 2,
                py + ph / 2,
                INK_4,
                font_size=TEXT_SM,
                font_name=FONT_MONO,
                anchor_x="center",
                anchor_y="center",
                italic=True,
            )

        for text, cy, color in self._labels:
            arcade.draw_text(
                text, px + PAD_SM, cy, color,
                font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="left", anchor_y="center",
            )

        for key, (vx, vy) in self._number_label_centers.items():
            arcade.draw_text(
                str(self._number_values.get(key, 0)),
                vx, vy,
                (*INK_1, 255),
                font_size=TEXT_BASE, font_name=FONT_MONO,
                anchor_x="center", anchor_y="center",
            )

        for key, (vx, vy) in self._choice_label_centers.items():
            opts = self._choice_options.get(key, [])
            idx = self._choice_values.get(key, 0)
            label = opts[idx].upper() if 0 <= idx < len(opts) else ""
            arcade.draw_text(
                label, vx, vy,
                (*INK_1, 255),
                font_size=TEXT_SM, font_name=FONT_MONO,
                anchor_x="center", anchor_y="center",
            )

    # ------------------------------------------------------------------
    # Widget y-position helper
    # ------------------------------------------------------------------

    def _widget_y(self, offset_from_top: float, height: float) -> int:
        """Arcade y (bottom-left) for a widget placed offset_from_top px below the panel top."""
        return int(self._y + self._h - offset_from_top - height)

    def _add(self, widget: arcade.gui.UIWidget) -> None:
        assert self._manager is not None
        self._manager.add(widget)
        self._widgets.append(widget)

    def _add_input(
        self,
        key: str,
        value: str,
        x: float,
        y_bottom: float,
        w: float,
        h: float,
        multiline: bool = False,
    ) -> arcade.gui.UIInputText:
        widget = arcade.gui.UIInputText(
            x=int(x),
            y=int(y_bottom),
            width=int(w),
            height=int(h),
            text=value,
            font_name=(FONT_MONO,),
            font_size=TEXT_BASE,
            text_color=(*INK_1, 255),
            multiline=multiline,
        )
        self._add(widget)
        self._inputs[key] = widget
        return widget

    def _add_save_cancel(self, offset_from_top: float) -> None:
        pad = PAD_SM
        fx = self._x + pad
        fw = self._w - 2 * pad
        y = self._widget_y(offset_from_top, _BTN_H)

        save_btn = arcade.gui.UIFlatButton(
            x=int(fx), y=int(y),
            width=int(fw / 2 - pad / 2), height=_BTN_H,
            text="SAVE", style=_btn_style("teal"),
        )
        cancel_btn = arcade.gui.UIFlatButton(
            x=int(fx + fw / 2 + pad / 2), y=int(y),
            width=int(fw / 2 - pad / 2), height=_BTN_H,
            text="CANCEL", style=_btn_style("default"),
        )

        @save_btn.event
        def on_click(event: arcade.gui.UIOnClickEvent) -> None:
            if self._on_save:
                self._on_save(self._collect_inputs())

        @cancel_btn.event  # type: ignore[no-redef]
        def on_click(event: arcade.gui.UIOnClickEvent) -> None:  # noqa: F811
            if self._on_cancel:
                self._on_cancel()

        self._add(save_btn)
        self._add(cancel_btn)

    def _collect_inputs(self) -> dict[str, Any]:
        if self.mode in ("actor", "new_actor"):
            return self._collect_actor_inputs()
        if self.mode in ("faction", "new_faction"):
            return self._collect_faction_inputs()
        if self.mode in ("room_object", "new_room_object"):
            return self._collect_room_object_inputs()
        result = {k: v.text for k, v in self._inputs.items()}
        result.update(self._extra_data)
        result.update({k: str(v) for k, v in self._number_values.items()})
        return result

    def _collect_actor_inputs(self) -> dict[str, Any]:
        result = {k: v.text for k, v in self._inputs.items()}
        result.update(self._extra_data)
        result.update({k: str(v) for k, v in self._number_values.items()})
        options = self._choice_options.get("playbook", [])
        idx = self._choice_values.get("playbook", 0)
        slug = options[idx] if 0 <= idx < len(options) else _PLAYBOOK_NONE
        result["playbook_slug"] = None if slug == _PLAYBOOK_NONE else slug
        return result

    def _apply_playbook_to_form(self, slug: str | None) -> None:
        """Pre-populate rating and stress number pickers from a playbook."""
        if not slug or slug == _PLAYBOOK_NONE:
            return
        try:
            pb = PlaybookLibrary().get(slug)
        except KeyError:
            return
        for action_key, rating in pb.starting_action_ratings.items():
            self._number_values[f"rating_{action_key}"] = rating
        track_caps = {t.track_key: t.capacity for t in pb.starting_stress_tracks}
        for stress_key in _STRESS_KEYS:
            self._number_values[f"stress_{stress_key}"] = track_caps.get(stress_key, 0)

    def _collect_room_object_inputs(self) -> dict[str, Any]:
        result = {k: v.text for k, v in self._inputs.items()}
        result.update(self._extra_data)  # room_id, level_id, archetype, transitions, slug
        # Archetype comes from the choice picker (source of truth); re-derive its
        # default transitions so they stay consistent with the chosen archetype.
        if "archetype" in self._choice_values:
            idx = self._choice_values["archetype"]
            arch = _ARCHETYPES[idx % len(_ARCHETYPES)]
            result["archetype"] = arch
            result["transitions"] = default_transitions_for_archetype(arch)
        # Slug is system-generated from the name for new objects; preserved on edit.
        name = result.get("display_name", "")
        original = str(self._extra_data.get("slug", ""))
        if self.mode == "new_room_object" or not original:
            result["slug"] = _slugify(name)
        else:
            result["slug"] = original
        return result

    def _collect_faction_inputs(self) -> dict[str, Any]:
        result = {k: v.text for k, v in self._inputs.items()}
        result.update(self._extra_data)
        rep_idx = self._number_values.get("reputation_idx", 2)
        result["reputation"] = _REPUTATION_TIERS[max(0, min(4, rep_idx))]
        result["tier"] = str(self._number_values.get("tier", 0))
        return result

    # ------------------------------------------------------------------
    # Form builders
    # ------------------------------------------------------------------

    def _build_actor_form(self, actor: object) -> None:
        pad = PAD_SM
        fw = self._w - 2 * pad
        fx = self._x + pad
        cursor = 48.0

        # Preserve actor_type (no UI selector yet — roundtrip via _extra_data)
        self._extra_data["actor_type"] = getattr(actor, "actor_type", "pc")

        initial_pb_slug: str | None = getattr(actor, "playbook_slug", None)
        action_ratings: dict[str, Any] = getattr(actor, "action_ratings", {}) or {}
        stress_caps: dict[str, int] = {}
        for track in getattr(actor, "stress_tracks", []):
            if isinstance(track, dict):
                k, v = track.get("track_key", ""), track.get("capacity", 6)
            else:
                k, v = getattr(track, "track_key", ""), getattr(track, "capacity", 6)
            if k:
                stress_caps[k] = v

        def _lbl(text: str, color: tuple[Any, ...] = INK_3) -> None:
            nonlocal cursor
            cy = self._widget_y(cursor, _LABEL_H) + _LABEL_H / 2
            self._labels.append((text, cy, color))
            cursor += _LABEL_H + _LABEL_GAP

        def _inp(key: str, value: str, h: float = _FIELD_H, multiline: bool = False) -> None:
            nonlocal cursor
            self._add_input(key, value, fx, self._widget_y(cursor, h), fw, h, multiline)
            cursor += h + _FIELD_GAP

        _BTN_W_PICKER = 22  # width of [-] and [+] buttons

        def _number_row(label: str, field_key: str, value: int, max_val: int = 9) -> None:
            """Row label + [-] value [+] number picker (no UIInputText — no hover jitter)."""
            nonlocal cursor
            h = _ROW_H
            input_x = fx + _ROW_LABEL_W
            input_w = fw - _ROW_LABEL_W
            wy = self._widget_y(cursor, h)
            cy = wy + h // 2

            self._labels.append((label, cy, INK_3))
            self._number_values[field_key] = value

            # Value center between the two buttons
            vx = input_x + _BTN_W_PICKER + (input_w - 2 * _BTN_W_PICKER) / 2
            self._number_label_centers[field_key] = (vx, cy)

            minus_btn = arcade.gui.UIFlatButton(
                x=int(input_x), y=wy,
                width=_BTN_W_PICKER, height=h,
                text="-", style=_btn_style("default"),
            )
            plus_btn = arcade.gui.UIFlatButton(
                x=int(input_x + input_w - _BTN_W_PICKER), y=wy,
                width=_BTN_W_PICKER, height=h,
                text="+", style=_btn_style("default"),
            )

            @minus_btn.event
            def on_click(event: arcade.gui.UIOnClickEvent, _k: str = field_key, _min: int = 0) -> None:
                self._number_values[_k] = max(_min, self._number_values[_k] - 1)

            @plus_btn.event  # type: ignore[no-redef]
            def on_click(event: arcade.gui.UIOnClickEvent, _k: str = field_key, _max: int = max_val) -> None:  # noqa: F811
                self._number_values[_k] = min(_max, self._number_values[_k] + 1)

            self._add(minus_btn)
            self._add(plus_btn)
            cursor += h + _ROW_GAP

        # Build playbook picker options: sentinel + slugs from library
        library = PlaybookLibrary()
        playbooks = library.list()
        pb_options = [_PLAYBOOK_NONE] + [pb.slug for pb in playbooks]
        initial_pb_idx = (
            pb_options.index(initial_pb_slug)
            if initial_pb_slug and initial_pb_slug in pb_options
            else 0
        )

        def _playbook_row(key: str, options: list[str], value_idx: int) -> None:
            nonlocal cursor
            h = _ROW_H
            input_x = fx + _ROW_LABEL_W
            input_w = fw - _ROW_LABEL_W
            wy = self._widget_y(cursor, h)
            cy = wy + h // 2

            self._choice_values[key] = value_idx
            self._choice_options[key] = options
            vx = input_x + _BTN_W_PICKER + (input_w - 2 * _BTN_W_PICKER) / 2
            self._choice_label_centers[key] = (vx, cy)

            prev_btn = arcade.gui.UIFlatButton(
                x=int(input_x), y=wy, width=_BTN_W_PICKER, height=h,
                text="<", style=_btn_style("default"),
            )
            next_btn = arcade.gui.UIFlatButton(
                x=int(input_x + input_w - _BTN_W_PICKER), y=wy, width=_BTN_W_PICKER, height=h,
                text=">", style=_btn_style("default"),
            )

            @prev_btn.event
            def on_click(event: arcade.gui.UIOnClickEvent, _k: str = key, _n: int = len(options)) -> None:
                new_idx = (self._choice_values[_k] - 1) % _n
                self._choice_values[_k] = new_idx
                self._apply_playbook_to_form(options[new_idx])

            @next_btn.event  # type: ignore[no-redef]
            def on_click(event: arcade.gui.UIOnClickEvent, _k: str = key, _n: int = len(options)) -> None:  # noqa: F811
                new_idx = (self._choice_values[_k] + 1) % _n
                self._choice_values[_k] = new_idx
                self._apply_playbook_to_form(options[new_idx])

            self._add(prev_btn)
            self._add(next_btn)
            cursor += h + _ROW_GAP

        # Basic fields
        _lbl("NAME")
        _inp("display_name", getattr(actor, "display_name", ""))
        _lbl("SLUG")
        _inp("slug", getattr(actor, "slug", ""))
        _lbl("CONCEPT")
        _inp("concept", getattr(actor, "concept", "") or "", h=80, multiline=True)

        # Playbook picker
        _lbl("── PLAYBOOK ──", INK_2)
        _playbook_row("playbook", pb_options, initial_pb_idx)

        # Action ratings — pre-populated from playbook if one is set
        _lbl("── ACTION RATINGS ──", INK_2)
        for key in _ACTION_KEYS:
            _number_row(key, f"rating_{key}", action_ratings.get(key, 0))

        # Stress tracks (max capacity)
        _lbl("── STRESS TRACKS ──", INK_2)
        for key in _STRESS_KEYS:
            _number_row(key, f"stress_{key}", stress_caps.get(key, 0))

        # Pre-populate number values from playbook (overrides manifest defaults if slug set)
        self._apply_playbook_to_form(initial_pb_slug)

        self._add_save_cancel(cursor + 8)

    def _build_clock_form(self, clock: object) -> None:
        pad = PAD_SM
        fw = self._w - 2 * pad
        fx = self._x + pad
        cursor = 48.0

        def _lbl(text: str) -> None:
            nonlocal cursor
            cy = self._widget_y(cursor, _LABEL_H) + _LABEL_H / 2
            self._labels.append((text, cy, INK_3))
            cursor += _LABEL_H + _LABEL_GAP

        def _input(key: str, value: str, h: float = _FIELD_H, multiline: bool = False) -> None:
            nonlocal cursor
            self._add_input(key, value, fx, self._widget_y(cursor, h), fw, h, multiline)
            cursor += h + _FIELD_GAP

        _lbl("NAME")
        _input("label", getattr(clock, "label", ""))
        _lbl("SLUG")
        _input("slug", getattr(clock, "slug", ""))
        _lbl("SEGMENTS")
        _input("segments", str(getattr(clock, "segments", 6)))
        _lbl("FILLED")
        _input("filled", str(getattr(clock, "filled", 0)))
        _lbl("STAKES")
        _input("stakes", getattr(clock, "stakes", "") or "", h=64, multiline=True)

        self._add_save_cancel(cursor + 8)

    def _build_lore_form(self, text: str) -> None:
        pad = PAD_SM
        fw = self._w - 2 * pad
        fx = self._x + pad
        cursor = 48.0

        cy = self._widget_y(cursor, _LABEL_H) + _LABEL_H / 2
        self._labels.append(("TEXT", cy, INK_3))
        cursor += _LABEL_H + _LABEL_GAP

        self._add_input("text", text, fx, self._widget_y(cursor, 160), fw, 160, multiline=True)
        self._add_save_cancel(cursor + 160 + _FIELD_GAP + 8)

    def _build_threat_form(self, threat: dict[str, Any]) -> None:
        pad = PAD_SM
        fw = self._w - 2 * pad
        fx = self._x + pad
        cursor = 48.0

        def _lbl(text: str) -> None:
            nonlocal cursor
            cy = self._widget_y(cursor, _LABEL_H) + _LABEL_H / 2
            self._labels.append((text, cy, INK_3))
            cursor += _LABEL_H + _LABEL_GAP

        def _input(key: str, value: str, h: float = _FIELD_H, multiline: bool = False) -> None:
            nonlocal cursor
            self._add_input(key, value, fx, self._widget_y(cursor, h), fw, h, multiline)
            cursor += h + _FIELD_GAP

        _lbl("LOCATION")
        _input("location_slug", threat.get("location_slug", ""))
        _lbl("DESCRIPTION")
        _input("description", threat.get("description", ""), h=80, multiline=True)

        self._add_save_cancel(cursor + 8)

    def _build_room_object_form(self, obj: object) -> None:
        pad = PAD_SM
        fw = self._w - 2 * pad
        fx = self._x + pad
        cursor = 48.0

        archetype = str(getattr(obj, "archetype", "container"))
        self._extra_data["room_id"] = str(getattr(obj, "room_id", ""))
        self._extra_data["level_id"] = str(getattr(obj, "level_id", ""))
        self._extra_data["archetype"] = archetype
        self._extra_data["transitions"] = default_transitions_for_archetype(archetype)
        # Slug is system-generated from NAME; the existing value is preserved on edit.
        self._extra_data["slug"] = str(getattr(obj, "slug", ""))

        def _lbl(text: str, color: tuple[Any, ...] = INK_3) -> None:
            nonlocal cursor
            cy = self._widget_y(cursor, _LABEL_H) + _LABEL_H / 2
            self._labels.append((text, cy, color))
            cursor += _LABEL_H + _LABEL_GAP

        def _inp(key: str, value: str, h: float = _FIELD_H, multiline: bool = False) -> None:
            nonlocal cursor
            self._add_input(key, value, fx, self._widget_y(cursor, h), fw, h, multiline)
            cursor += h + _FIELD_GAP

        _BTN_W_PICKER = 22

        def _choice_row(label: str, key: str, options: list[str], value_idx: int) -> None:
            """Row label + [<] choice [>] picker that cycles through string options."""
            nonlocal cursor
            h = _ROW_H
            input_x = fx + _ROW_LABEL_W
            input_w = fw - _ROW_LABEL_W
            wy = self._widget_y(cursor, h)
            cy = wy + h // 2

            self._labels.append((label, cy, INK_3))
            self._choice_values[key] = value_idx
            self._choice_options[key] = options
            vx = input_x + _BTN_W_PICKER + (input_w - 2 * _BTN_W_PICKER) / 2
            self._choice_label_centers[key] = (vx, cy)

            prev_btn = arcade.gui.UIFlatButton(
                x=int(input_x), y=wy, width=_BTN_W_PICKER, height=h,
                text="<", style=_btn_style("default"),
            )
            next_btn = arcade.gui.UIFlatButton(
                x=int(input_x + input_w - _BTN_W_PICKER), y=wy, width=_BTN_W_PICKER, height=h,
                text=">", style=_btn_style("default"),
            )

            @prev_btn.event
            def on_click(event: arcade.gui.UIOnClickEvent, _k: str = key, _n: int = len(options)) -> None:
                self._choice_values[_k] = (self._choice_values[_k] - 1) % _n

            @next_btn.event  # type: ignore[no-redef]
            def on_click(event: arcade.gui.UIOnClickEvent, _k: str = key, _n: int = len(options)) -> None:  # noqa: F811
                self._choice_values[_k] = (self._choice_values[_k] + 1) % _n

            self._add(prev_btn)
            self._add(next_btn)
            cursor += h + _ROW_GAP

        arch_idx = _ARCHETYPES.index(archetype) if archetype in _ARCHETYPES else 0

        _lbl("NAME")
        _inp("display_name", str(getattr(obj, "display_name", "")))
        _lbl("DESCRIPTION")
        _inp("description", str(getattr(obj, "description", "")), h=64, multiline=True)
        _choice_row("ARCHETYPE", "archetype", _ARCHETYPES, arch_idx)
        _lbl("INITIAL STATE")
        _inp("initial_state", str(getattr(obj, "initial_state", "")))

        self._add_save_cancel(cursor + 8)

    def _build_faction_form(self, faction: object) -> None:
        pad = PAD_SM
        fw = self._w - 2 * pad
        fx = self._x + pad
        cursor = 48.0

        def _lbl(text: str, color: tuple[Any, ...] = INK_3) -> None:
            nonlocal cursor
            cy = self._widget_y(cursor, _LABEL_H) + _LABEL_H / 2
            self._labels.append((text, cy, color))
            cursor += _LABEL_H + _LABEL_GAP

        def _inp(key: str, value: str, h: float = _FIELD_H, multiline: bool = False) -> None:
            nonlocal cursor
            self._add_input(key, value, fx, self._widget_y(cursor, h), fw, h, multiline)
            cursor += h + _FIELD_GAP

        _BTN_W_PICKER = 22

        def _rep_row(label: str, field_key: str, value: int) -> None:
            nonlocal cursor
            h = _ROW_H
            input_x = fx + _ROW_LABEL_W
            input_w = fw - _ROW_LABEL_W
            wy = self._widget_y(cursor, h)
            cy = wy + h // 2

            self._labels.append((label, cy, INK_3))
            self._number_values[field_key] = value
            vx = input_x + _BTN_W_PICKER + (input_w - 2 * _BTN_W_PICKER) / 2
            self._number_label_centers[field_key] = (vx, cy)

            minus_btn = arcade.gui.UIFlatButton(
                x=int(input_x), y=wy, width=_BTN_W_PICKER, height=h,
                text="-", style=_btn_style("default"),
            )
            plus_btn = arcade.gui.UIFlatButton(
                x=int(input_x + input_w - _BTN_W_PICKER), y=wy, width=_BTN_W_PICKER, height=h,
                text="+", style=_btn_style("default"),
            )

            @minus_btn.event
            def on_click(event: arcade.gui.UIOnClickEvent, _k: str = field_key) -> None:
                self._number_values[_k] = max(0, self._number_values[_k] - 1)

            @plus_btn.event  # type: ignore[no-redef]
            def on_click(event: arcade.gui.UIOnClickEvent, _k: str = field_key, _max: int = 4) -> None:  # noqa: F811
                self._number_values[_k] = min(_max, self._number_values[_k] + 1)

            self._add(minus_btn)
            self._add(plus_btn)
            cursor += h + _ROW_GAP

        rep_idx = _REPUTATION_TIERS.index(getattr(faction, "reputation", "neutral"))
        tier_val = int(getattr(faction, "tier", 0))

        _lbl("NAME")
        _inp("display_name", getattr(faction, "display_name", ""))
        _lbl("SLUG")
        _inp("slug", getattr(faction, "slug", ""))
        _lbl("CONCEPT")
        _inp("concept", getattr(faction, "concept", "") or "", h=80, multiline=True)
        _lbl("GOAL")
        _inp("goal", getattr(faction, "goal", "") or "", h=60, multiline=True)
        _rep_row("REPUTATION", "reputation_idx", rep_idx)
        _rep_row("TIER", "tier", tier_val)

        self._add_save_cancel(cursor + 8)
