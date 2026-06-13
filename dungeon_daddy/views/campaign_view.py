"""Campaign Authoring UI — Phase 42."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import arcade
import arcade.gui

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest, FactionManifest
from dungeon_daddy.campaign.validator import ManifestError, validate_manifest
from dungeon_daddy.ui.chrome import MenuBar, draw_title_bar, title_bar_mode_at
from dungeon_daddy.ui.panels.campaign_edit_panel import CampaignEditPanel
from dungeon_daddy.ui.panels.campaign_list_panel import CampaignListPanel
from dungeon_daddy.ui.panels.campaign_nav_panel import CampaignNavPanel
from dungeon_daddy.ui.theme import (
    BG_0,
    BG_2,
    CHROME_TOTAL_HEIGHT,
    LINE,
)

_log = logging.getLogger(__name__)

_NAV_W = 220
_EDIT_W = 300


def _parse_rating_keys(data: dict) -> dict[str, int]:
    """Extract rating_<action> fields into an action_ratings dict, excluding zeros."""
    result: dict[str, int] = {}
    for key, value in data.items():
        if not key.startswith("rating_"):
            continue
        action_key = key[7:]
        try:
            rating = int(value)
        except (ValueError, TypeError):
            rating = 0
        if rating > 0:
            result[action_key] = rating
    return result


def _parse_stress_keys(data: dict, existing_tracks: list[dict]) -> list[dict]:
    """Rebuild stress_tracks list from stress_<key> form fields, preserving filled values."""
    filled_by_key = {t["track_key"]: t.get("filled", 0) for t in existing_tracks}
    result = []
    for key, value in data.items():
        if not key.startswith("stress_"):
            continue
        track_key = key[7:]
        try:
            capacity = int(value)
        except (ValueError, TypeError):
            capacity = 6
        result.append({
            "track_key": track_key,
            "capacity": capacity,
            "filled": filled_by_key.get(track_key, 0),
        })
    return result


class CampaignView(arcade.View):
    _SECTIONS = [
        "player_side",
        "monsters",
        "npcs",
        "factions",
        "clocks",
        "threats",
        "lore",
        "validation",
    ]

    def __init__(self, menu_bar: MenuBar) -> None:
        super().__init__()
        self._menu_bar = menu_bar
        self._manager = arcade.gui.UIManager()
        self._nav_panel = CampaignNavPanel()
        self._list_panel = CampaignListPanel()
        self._edit_panel = CampaignEditPanel()
        self._selected_item_index: int | None = None
        self._hovered_card_index: int | None = None
        self._manifest_path: Path | None = None
        self._ui_built = False
        self._init_state()

    def _init_state(self) -> None:
        self.manifest: CampaignManifest | None = None
        self.active_section: str | None = None
        self.is_dirty: bool = False
        self._validation_result: list[ManifestError] | None = None

    # ------------------------------------------------------------------
    # View lifecycle
    # ------------------------------------------------------------------

    def on_show_view(self) -> None:
        self.window.background_color = BG_0
        self._manager.enable()
        self._manager.on_resize(self.window.width, self.window.height)  # type: ignore[no-untyped-call]
        if not self._ui_built:
            self._build_ui()
            self._ui_built = True
        else:
            self._reposition_panels(self.window.width, self.window.height)

    def on_hide_view(self) -> None:
        self._manager.disable()

    def on_draw(self) -> None:
        self.clear()
        w = self.window.width
        h = self.window.height
        content_h = h - CHROME_TOTAL_HEIGHT
        list_w = w - _NAV_W - _EDIT_W

        # Panel background fills
        arcade.draw_rect_filled(
            arcade.XYWH(_NAV_W / 2, content_h / 2, _NAV_W, content_h), BG_2,
        )
        arcade.draw_rect_filled(
            arcade.XYWH(_NAV_W + list_w / 2, content_h / 2, list_w, content_h), BG_0,
        )
        arcade.draw_rect_filled(
            arcade.XYWH(_NAV_W + list_w + _EDIT_W / 2, content_h / 2, _EDIT_W, content_h), BG_2,
        )
        # Panel dividers
        arcade.draw_line(_NAV_W, 0, _NAV_W, content_h, LINE, 1)
        arcade.draw_line(_NAV_W + list_w, 0, _NAV_W + list_w, content_h, LINE, 1)

        draw_title_bar(self.window, mode="campaign")

        items = self._section_items()
        self._list_panel.set_item_count(len(items))

        self._nav_panel.draw(
            self.active_section,
            self.manifest.title if self.manifest else None,
            self._section_counts(),
            self.is_dirty,
        )
        self._list_panel.draw(self.active_section, items, self._hovered_card_index)
        self._edit_panel.draw()
        self._manager.draw()
        self._menu_bar.draw(self.window)

    def on_update(self, delta_time: float) -> None:
        pass

    def on_resize(self, width: int, height: int) -> None:
        self._reposition_panels(width, height)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        if self._menu_bar.handle_click(x, y, self.window):
            return
        pill = title_bar_mode_at(x, y, self.window)
        if pill and pill != "campaign":
            self.window.switch_mode(pill)
            return

        section = self._nav_panel.section_at(x, y)
        if section is not None:
            self.set_active_section(section)
            self._clear_selection()
            if section == "validation":
                self.run_validation()
            return
        if self._nav_panel.load_btn_at(x, y):
            self._load_campaign()
            return
        if self._nav_panel.new_btn_at(x, y):
            self._new_campaign()
            return
        if self._nav_panel.save_btn_at(x, y) and self.is_dirty:
            self._save_campaign()
            return

        if self._list_panel.add_btn_at(x, y):
            self._start_new_item()
            return
        del_idx = self._list_panel.delete_zone_at(x, y)
        if del_idx is not None:
            self._delete_item_at(del_idx)
            return
        item_idx = self._list_panel.item_at(x, y)
        if item_idx is not None:
            self._select_item_at(item_idx)
            return

    def on_mouse_motion(
        self, x: float, y: float, dx: float, dy: float
    ) -> None:
        self._hovered_card_index = self._list_panel.item_at(x, y)

    def on_mouse_scroll(
        self, x: float, y: float, scroll_x: float, scroll_y: float
    ) -> None:
        lx, lw = self._list_panel._x, self._list_panel._w
        if lx <= x <= lx + lw:
            new_off = max(0.0, self._list_panel._scroll_offset - scroll_y * 30)
            self._list_panel.set_scroll_offset(new_off)

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._reposition_panels(self.window.width, self.window.height)

    def _reposition_panels(self, w: int, h: int) -> None:
        content_h = h - CHROME_TOTAL_HEIGHT
        list_w = w - _NAV_W - _EDIT_W

        self._nav_panel.set_bounds(0.0, 0.0, float(_NAV_W), float(content_h))
        self._nav_panel.set_sections(self._SECTIONS)

        self._list_panel.set_bounds(float(_NAV_W), 0.0, float(list_w), float(content_h))

        self._edit_panel.setup(
            self._manager,
            float(_NAV_W + list_w), 0.0,
            float(_EDIT_W), float(content_h),
        )
        self._manager.on_resize(w, h)  # type: ignore[no-untyped-call]

    # ------------------------------------------------------------------
    # Item selection / editing
    # ------------------------------------------------------------------

    def _select_item_at(self, idx: int) -> None:
        items = self._section_items()
        if idx >= len(items):
            return
        self._selected_item_index = idx
        item = items[idx]
        s = self.active_section
        if s == "factions":
            self._edit_panel.show_faction(item, self._on_form_save, self._clear_selection)
        elif s in ("player_side", "monsters", "npcs"):
            self._edit_panel.show_actor(item, self._on_form_save, self._clear_selection)
        elif s == "clocks":
            self._edit_panel.show_clock(item, self._on_form_save, self._clear_selection)
        elif s == "lore":
            self._edit_panel.show_lore(str(item), self._on_form_save, self._clear_selection)
        elif s == "threats":
            threat = item if isinstance(item, dict) else {}
            self._edit_panel.show_threat(threat, self._on_form_save, self._clear_selection)

    def _start_new_item(self) -> None:
        if self.manifest is None:
            return
        self._selected_item_index = None
        s = self.active_section
        if s == "factions":
            blank = FactionManifest(slug="", display_name="")
            self._edit_panel.show_faction(blank, self._on_form_save, self._clear_selection, is_new=True)
        elif s in ("player_side", "monsters", "npcs"):
            blank = ActorManifest(slug="", display_name="", actor_type="pc")
            self._edit_panel.show_actor(blank, self._on_form_save, self._clear_selection, is_new=True)
        elif s == "clocks":
            blank_clk = ClockManifest(slug="", label="", segments=6)
            self._edit_panel.show_clock(blank_clk, self._on_form_save, self._clear_selection, is_new=True)
        elif s == "lore":
            self._edit_panel.show_lore("", self._on_form_save, self._clear_selection, is_new=True)
        elif s == "threats":
            self._edit_panel.show_threat({}, self._on_form_save, self._clear_selection, is_new=True)

    def _delete_item_at(self, idx: int) -> None:
        s = self.active_section
        items = self._section_items()
        if idx >= len(items):
            return
        item = items[idx]
        if s in ("player_side", "monsters", "npcs", "factions"):
            self.remove_actor(item.slug)
        elif s == "clocks":
            self.remove_clock(item.slug)
        elif s == "lore":
            real_idx = self.manifest.memory_seeds.index(item)
            self.remove_memory_seed(real_idx)
        elif s == "threats":
            real_idx = self.manifest.room_threats.index(item)
            self.remove_room_threat(real_idx)
        self._clear_selection()

    def _on_form_save(self, data: dict) -> None:
        s = self.active_section
        is_new = self._edit_panel.mode.startswith("new_")
        if s == "factions":
            if is_new:
                try:
                    faction = FactionManifest(
                        slug=data.get("slug", ""),
                        display_name=data.get("display_name", ""),
                        concept=data.get("concept") or None,
                        goal=data.get("goal") or None,
                        reputation=data.get("reputation", "neutral"),
                        tier=int(data.get("tier", "0")),
                    )
                    self.add_actor(faction)
                except Exception as exc:
                    _log.warning("Faction save failed: %s", exc)
            elif self._selected_item_index is not None:
                items = self._section_items()
                if self._selected_item_index < len(items):
                    slug = items[self._selected_item_index].slug
                    self.update_actor(
                        slug,
                        display_name=data.get("display_name", ""),
                        concept=data.get("concept") or None,
                        goal=data.get("goal") or None,
                        reputation=data.get("reputation", "neutral"),
                        tier=int(data.get("tier", "0")),
                    )
        elif s in ("player_side", "monsters", "npcs"):
            action_ratings = _parse_rating_keys(data)
            stress_tracks = _parse_stress_keys(data, [])
            clean = {
                k: v for k, v in data.items()
                if not k.startswith("rating_") and not k.startswith("stress_")
            }
            if is_new:
                try:
                    actor = ActorManifest(
                        action_ratings=action_ratings,
                        stress_tracks=stress_tracks,
                        **clean,
                    )
                    self.add_actor(actor)
                except Exception as exc:
                    _log.warning("Actor save failed: %s", exc)
            elif self._selected_item_index is not None:
                items = self._section_items()
                if self._selected_item_index < len(items):
                    existing = items[self._selected_item_index]
                    slug = existing.slug
                    stress_tracks = _parse_stress_keys(data, existing.stress_tracks)
                    self.update_actor(
                        slug,
                        action_ratings=action_ratings,
                        stress_tracks=stress_tracks,
                        **{k: v for k, v in clean.items() if k != "slug"},
                    )
        elif s == "clocks":
            if is_new:
                try:
                    segments = int(data.get("segments", 6))
                    filled = min(int(data.get("filled", 0)), segments)
                    clock = ClockManifest(
                        slug=data.get("slug", ""),
                        label=data.get("label", ""),
                        segments=segments,
                        filled=filled,
                        stakes=data.get("stakes") or None,
                    )
                    self.add_clock(clock)
                except Exception as exc:
                    _log.warning("Clock save failed: %s", exc)
            elif self._selected_item_index is not None:
                items = self._section_items()
                if self._selected_item_index < len(items):
                    slug = items[self._selected_item_index].slug
                    kwargs: dict = {}
                    if "label" in data:
                        kwargs["label"] = data["label"]
                    if "stakes" in data:
                        kwargs["stakes"] = data["stakes"] or None
                    self.update_clock(slug, **kwargs)
        elif s == "lore":
            text = data.get("text", "")
            if is_new:
                self.add_memory_seed(text)
            elif self._selected_item_index is not None:
                items = self._section_items()
                if self._selected_item_index < len(items):
                    real_idx = self.manifest.memory_seeds.index(items[self._selected_item_index])
                    self.manifest.memory_seeds[real_idx] = text
                    self.is_dirty = True
        elif s == "threats":
            if is_new:
                self.add_room_threat({
                    "location_slug": data.get("location_slug", ""),
                    "description": data.get("description", ""),
                })
            elif self._selected_item_index is not None:
                items = self._section_items()
                if self._selected_item_index < len(items):
                    real_idx = self.manifest.room_threats.index(items[self._selected_item_index])
                    self.manifest.room_threats[real_idx] = {
                        "location_slug": data.get("location_slug", ""),
                        "description": data.get("description", ""),
                    }
                    self.is_dirty = True
        self._clear_selection()

    def _clear_selection(self) -> None:
        self._selected_item_index = None
        self._edit_panel.clear()

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _load_campaign(self) -> None:
        from tkinter import filedialog
        root = self.window._make_tk_root()
        path = filedialog.askopenfilename(
            title="Load Campaign",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        root.destroy()
        if path:
            try:
                self._manifest_path = Path(path)
                self.load_from_path(self._manifest_path)
            except Exception as exc:
                _log.error("Failed to load campaign: %s", exc)

    def _new_campaign(self) -> None:
        blank = CampaignManifest(
            slug="new-campaign",
            title="New Campaign",
            dungeon_slug="",
        )
        self.load_manifest(blank)
        self._manifest_path = None
        self.is_dirty = True

    def _save_campaign(self) -> None:
        if self._manifest_path:
            self.save_to_path(self._manifest_path)
        else:
            from tkinter import filedialog
            root = self.window._make_tk_root()
            path = filedialog.asksaveasfilename(
                title="Save Campaign",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
            )
            root.destroy()
            if path:
                self._manifest_path = Path(path)
                self.save_to_path(self._manifest_path)

    # ------------------------------------------------------------------
    # CRUD — these methods are tested by test_campaign_view.py
    # ------------------------------------------------------------------

    def load_manifest(self, manifest: CampaignManifest) -> None:
        self.manifest = manifest
        self.is_dirty = False
        self.active_section = self._SECTIONS[0]

    def set_active_section(self, section: str) -> None:
        self.active_section = section

    def add_actor(self, actor: ActorManifest | FactionManifest) -> None:
        if isinstance(actor, FactionManifest):
            self.manifest.factions.append(actor)
        else:
            self.manifest.world_actors.append(actor)
        self.is_dirty = True

    def update_actor(self, slug: str, **kwargs: object) -> None:
        for collection in (self.manifest.world_actors, self.manifest.factions):
            for actor in collection:
                if actor.slug == slug:
                    for key, value in kwargs.items():
                        setattr(actor, key, value)
                    self.is_dirty = True
                    return

    def remove_actor(self, slug: str) -> None:
        for collection in (self.manifest.world_actors, self.manifest.factions):
            for actor in collection:
                if actor.slug == slug:
                    collection.remove(actor)
                    self.is_dirty = True
                    return

    def set_player_side(self, slugs: list[str]) -> None:
        self.manifest.player_side = slugs
        self.is_dirty = True

    def add_clock(self, clock: ClockManifest) -> None:
        self.manifest.clocks.append(clock)
        self.is_dirty = True

    def update_clock(self, slug: str, **kwargs: object) -> None:
        for clock in self.manifest.clocks:
            if clock.slug == slug:
                for key, value in kwargs.items():
                    setattr(clock, key, value)
                self.is_dirty = True
                return

    def remove_clock(self, slug: str) -> None:
        for clock in self.manifest.clocks:
            if clock.slug == slug:
                self.manifest.clocks.remove(clock)
                self.is_dirty = True
                return

    def add_memory_seed(self, text: str) -> None:
        self.manifest.memory_seeds.append(text)
        self.is_dirty = True

    def remove_memory_seed(self, index: int) -> None:
        del self.manifest.memory_seeds[index]
        self.is_dirty = True

    def add_room_threat(self, threat: dict) -> None:
        self.manifest.room_threats.append(threat)
        self.is_dirty = True

    def remove_room_threat(self, index: int) -> None:
        del self.manifest.room_threats[index]
        self.is_dirty = True

    def run_validation(self) -> list[ManifestError]:
        self._validation_result = validate_manifest(self.manifest)
        return self._validation_result

    def save_to_path(self, path: Path) -> None:
        data = self.manifest.model_dump()
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.is_dirty = False

    def load_from_path(self, path: Path) -> None:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.load_manifest(CampaignManifest(**data))

    # ------------------------------------------------------------------
    # Section helpers
    # ------------------------------------------------------------------

    def _section_counts(self) -> dict[str, int]:
        if self.manifest is None:
            return {}
        m = self.manifest
        ps = set(m.player_side)
        return {
            "player_side": sum(1 for a in m.world_actors if a.slug in ps),
            "monsters": sum(
                1 for a in m.world_actors
                if a.actor_type in {"monster", "dungeon", "dungeon_presence"}
            ),
            "npcs": sum(1 for a in m.world_actors if a.actor_type == "npc"),
            "factions": len(m.factions),
            "clocks": len(m.clocks),
            "threats": len(m.room_threats),
            "lore": len(m.memory_seeds),
        }

    def _section_items(self) -> list:
        if self.manifest is None or self.active_section is None:
            return []
        m = self.manifest
        s = self.active_section
        ps = set(m.player_side)
        if s == "player_side":
            return [a for a in m.world_actors if a.slug in ps]
        elif s == "monsters":
            return [
                a for a in m.world_actors
                if a.actor_type in {"monster", "dungeon", "dungeon_presence"}
            ]
        elif s == "npcs":
            return [a for a in m.world_actors if a.actor_type == "npc"]
        elif s == "factions":
            return list(m.factions)
        elif s == "clocks":
            return list(m.clocks)
        elif s == "threats":
            return list(m.room_threats)
        elif s == "lore":
            return list(m.memory_seeds)
        elif s == "validation":
            return list(self._validation_result) if self._validation_result is not None else []
        return []
