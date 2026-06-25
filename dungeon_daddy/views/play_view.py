"""PlayView — Play Mode view with ChatPanel, GridMap, and RPG side panels."""
from __future__ import annotations

import logging
import queue
import re
import threading
from dataclasses import dataclass
from pathlib import Path

import arcade
import arcade.gui

from dungeon_daddy.data.models import Dungeon, Level, Room, SessionState
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
from dungeon_daddy.llm.provider import LLMMessage
from dungeon_daddy.map.graph_renderer import GraphRenderer
from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.models import MemoryEntry
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.actor_control import filter_player_actors
from dungeon_daddy.rpg.classifier import classify_intent
from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
from dungeon_daddy.rpg.intent import PendingIntent
from dungeon_daddy.rpg.models import ActorState, StressTrack
from dungeon_daddy.rpg.proposal import parse_proposal
from dungeon_daddy.rpg.proposal_applier import ApplyResult, apply_low_risk_proposals
from dungeon_daddy.rpg.proposal_validator import ValidationResult, validate_proposal
from dungeon_daddy.rpg.service import RpgService
from dungeon_daddy.ui.chrome import PILLS_CLUSTER_W, draw_title_bar, title_bar_mode_at
from dungeon_daddy.ui.mechanical_bubble import format_mechanical_bubble
from dungeon_daddy.ui.player_action_state import PlayerActionState
from dungeon_daddy.ui.panels.character_sheet_panel import CharacterSheetPanel
from dungeon_daddy.ui.panels.chat_panel import ChatPanel
from dungeon_daddy.ui.panels.debug_controls import DebugControls
from dungeon_daddy.ui.panels.fallout_panel import FalloutPanel
from dungeon_daddy.ui.panels.map_panel import MapPanel
from dungeon_daddy.ui.panels.memory_inspector_panel import MemoryInspectorPanel
from dungeon_daddy.ui.panels.player_action_panel import PlayerActionPanel
from dungeon_daddy.ui.panels.action_builder import InChatActionBuilder
from dungeon_daddy.ui.panels.vna_action_panel import VnaActionPanel
from dungeon_daddy.ui.panels.scene_state_panel import SceneStatePanel
from dungeon_daddy.ui.theme import (
    BG_0,
    BG_1,
    BG_2,
    BG_3,
    BG_HI,
    CHROME_TITLEBAR_HEIGHT,
    CHROME_TOTAL_HEIGHT,
    FONT_MONO,
    FONT_UI,
    FONT_UI_MED,
    INK_1,
    INK_2,
    INK_3,
    INK_4,
    LINE,
    LINE_HI,
    PAD_MD,
    PANEL_CHAT_WIDTH,
    PANEL_STEPPER_WIDTH,
    TEAL,
    TEXT_BASE,
    TEXT_SM,
)


@dataclass
class DMResult:
    content: str
    error: str | None = None


@dataclass(frozen=True)
class _PositionedRoom:
    """A room's rendered-layout geometry + name, for exit compass labels.

    Exposes the same ``x``/``y``/``w``/``h``/``name`` surface a ``Room`` does so
    :func:`dungeon_daddy.rpg.exit_labels.exit_noun_label` can consume it, but the
    coordinates are the layout-pipeline positions the map actually draws.
    """
    x: float
    y: float
    w: float
    h: float
    name: str

_log = logging.getLogger(__name__)

_CELL_PX = 48
_OVERLAY_TAB_H = 0   # tab bar is now an in-canvas overlay, not a reserved strip
_BTN_EDIT_W = 100
_BTN_EDIT_H = 24

_RPG_PANEL_W = 300
_RPG_TAB_H = 26
_BTN_RPG_W = 88

_RPG_TAB_LABELS = ["CHAR", "SCENE", "FALLOUT", "MEM", "DBG"]
_TAB_CHAR = 0
_TAB_MEM = 3
_TAB_DBG = 4
_DBG_LINE_MAX = 36


def _format_intent_framing(pending: PendingIntent, actor_name: str | None = None) -> str:
    chips = " ".join(f"[{k.upper()}]" for k in pending.suggested_action_keys)
    who = f"Acting as: {actor_name}\n" if actor_name else ""
    return f"{who}Suggested: {chips}\nClick an action below, or send text to skip the roll."


def _wrap_debug_line(line: str, max_chars: int = _DBG_LINE_MAX) -> list[str]:
    if len(line) <= max_chars:
        return [line]
    indent = len(line) - len(line.lstrip())
    cont = " " * (indent + 2)
    result: list[str] = []
    cur_min = indent
    while len(line) > max_chars:
        cut = line.rfind(" ", cur_min, max_chars)
        if cut <= cur_min:
            cut = max_chars
        result.append(line[:cut])
        line = cont + line[cut:].lstrip()
        cur_min = len(cont)
    result.append(line)
    return result


def _overlay_btn_style(variant: str) -> dict[str, arcade.gui.UIFlatButton.UIStyle]:
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


class _RpgSidePanel:
    """Collapsible side panel housing the RPG/memory display panels."""

    def __init__(
        self,
        char_panel: CharacterSheetPanel,
        scene_panel: SceneStatePanel,
        fallout_panel: FalloutPanel,
        memory_panel: MemoryInspectorPanel,
        debug_controls: DebugControls | None,
        manager: arcade.gui.UIManager | None = None,
    ) -> None:
        self._char = char_panel
        self._scene = scene_panel
        self._fallout = fallout_panel
        self._memory = memory_panel
        self._debug = debug_controls
        self._manager = manager
        self._active = 0
        self._x = self._y = self._w = self._h = 0.0
        self._tab_rects: list[tuple[float, float, float, float]] = []

    def setup(self, x: float, y: float, w: float, h: float) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h
        tab_w = w / len(_RPG_TAB_LABELS)
        tab_y = y + h - _RPG_TAB_H
        self._tab_rects = [
            (x + i * tab_w, tab_y, tab_w, float(_RPG_TAB_H))
            for i in range(len(_RPG_TAB_LABELS))
        ]
        content_h = h - _RPG_TAB_H
        for panel in (self._char, self._scene, self._fallout, self._memory):
            panel.setup(x, y, w, content_h)
        if self._active == _TAB_MEM:
            self._memory.setup_widget(self._manager, x, y, w, content_h)

    def teardown(self) -> None:
        """Remove any active UI widgets (call before hiding the panel)."""
        self._memory.teardown_widget(self._manager)

    def set_active(self, index: int) -> None:
        if 0 <= index < len(_RPG_TAB_LABELS):
            if self._active == _TAB_MEM:
                self._memory.teardown_widget(self._manager)
            self._active = index
            if self._active == _TAB_MEM:
                content_h = self._h - _RPG_TAB_H
                self._memory.setup_widget(
                    self._manager, self._x, self._y, self._w, content_h,
                )

    @property
    def active_tab(self) -> int:
        return self._active

    def hit_tab(self, x: float, y: float) -> int | None:
        for i, (tx, ty, tw, th) in enumerate(self._tab_rects):
            if tx <= x < tx + tw and ty <= y < ty + th:
                return i
        return None

    def draw(self) -> None:
        x, y, w, h = self._x, self._y, self._w, self._h
        arcade.draw_rect_filled(arcade.XYWH(x + w / 2, y + h / 2, w, h), BG_1)
        arcade.draw_rect_outline(arcade.XYWH(x + w / 2, y + h / 2, w, h), LINE, 1)

        if self._active == 0:
            self._char.draw()
        elif self._active == 1:
            self._scene.draw()
        elif self._active == 2:
            self._fallout.draw()
        elif self._active == _TAB_MEM:
            self._memory.draw()
        else:
            self._draw_debug_tab()

        self._draw_tab_bar()

    def _draw_tab_bar(self) -> None:
        tab_w = self._w / len(_RPG_TAB_LABELS)
        for i, label in enumerate(_RPG_TAB_LABELS):
            tx, ty, tw, th = self._tab_rects[i]
            tcx, tcy = tx + tw / 2, ty + th / 2
            bg = BG_HI if i == self._active else BG_2
            fg = INK_2 if i == self._active else INK_4
            arcade.draw_rect_filled(arcade.XYWH(tcx, tcy, tw, th), bg)
            arcade.draw_rect_outline(arcade.XYWH(tcx, tcy, tw, th), LINE, 1)
            arcade.draw_text(
                label, tcx, tcy, fg,
                font_size=9, font_name=FONT_UI,
                anchor_x="center", anchor_y="center",
            )

    def _draw_debug_tab(self) -> None:
        x, y, w = self._x, self._y, self._w
        content_h = self._h - _RPG_TAB_H
        if self._debug is None:
            arcade.draw_text(
                "No RPG service", x + PAD_MD, y + content_h / 2,
                INK_4, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="center",
            )
            return
        cur_y = y + content_h - PAD_MD
        arcade.draw_text(
            "DEBUG CONTROLS", x + PAD_MD, cur_y,
            INK_3, font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="top",
        )
        cur_y -= 20
        for section in (
            self._debug.last_action_section_lines(),
            self._debug.clock_section_lines(),
            self._debug.reaction_section_lines(),
            self._debug.proposal_section_lines(),
        ):
            for raw in section:
                for line in _wrap_debug_line(raw):
                    if cur_y < y + PAD_MD:
                        break
                    arcade.draw_text(
                        line, x + PAD_MD, cur_y,
                        INK_3, font_size=TEXT_SM, font_name=FONT_MONO, anchor_y="top",
                    )
                    cur_y -= 14
            cur_y -= 6
        sync = self._debug._last_sync_issues
        if sync is not None:
            label = "Sync: OK" if not sync else f"Sync: {len(sync)} issue(s)"
            arcade.draw_text(
                label, x + PAD_MD, cur_y,
                INK_3, font_size=TEXT_SM, font_name=FONT_UI, anchor_y="top",
            )


class PlayView(arcade.View):
    """
    Play Mode view.

    Layout: ChatPanel (440 px) left, MapPanel (flex) centre, optional RPG
    side panel (300 px) right.  The RPG panel is toggled via a button in
    the title bar and is collapsed by default.
    """

    def __init__(
        self,
        repo: DungeonRepository,
        dm_agent: DungeonMasterAgent | None = None,
        rpg_service: RpgService | None = None,
        mem_repo: MemoryRepository | None = None,
    ) -> None:
        super().__init__()
        self._repo = repo
        self._dm_agent = dm_agent
        self._rpg_service = rpg_service
        self._mem_repo = mem_repo
        self._dungeon: Dungeon | None = None
        self._state: SessionState | None = None
        self._manager = arcade.gui.UIManager()
        self._renderer = GraphRenderer(cell_px=_CELL_PX)
        self._chat = ChatPanel(self._on_chat_send, mode="play")
        self._map = MapPanel(
            self._on_level_change,
            renderer=self._renderer,
            on_variant_change=None,
            on_activate_loop=self.on_activate_loop,
            on_room_select=self._on_graph_room_select,
            on_connection_select=self._on_graph_connection_select,
            on_noun_click=self._on_overlay_noun_click,
        )
        self._ui_built = False
        self._result_queue: queue.Queue[DMResult] = queue.Queue()
        self._llm_busy = False
        self._active_thread: threading.Thread | None = None
        self._dm_history: list[LLMMessage] = []
        # Edit Memory button and overlay state
        self._has_memory: bool = False
        self._overlay_open: bool = False
        self._overlay_widgets: list[arcade.gui.UIWidget] = []
        self._overlay_input: arcade.gui.UIInputText | None = None
        self._overlay_level_id: int | None = None
        self._overlay_content: str | None = None
        self._edit_memory_rect: tuple[float, float, float, float] | None = None
        self._is_test_drive: bool = False
        # RPG side panel
        self._rpg_char = CharacterSheetPanel()
        self._rpg_scene = SceneStatePanel()
        self._rpg_fallout = FalloutPanel()
        self._rpg_memory = MemoryInspectorPanel()
        self._rpg_action = PlayerActionPanel()
        self._rpg_vna = VnaActionPanel()
        self._rpg_debug = DebugControls(rpg_service) if rpg_service is not None else None
        self._rpg_side = _RpgSidePanel(
            self._rpg_char, self._rpg_scene, self._rpg_fallout,
            self._rpg_memory, self._rpg_debug,
            manager=self._manager,
        )
        self._rpg_open: bool = False
        self._rpg_toggle_rect: tuple[float, float, float, float] | None = None
        self._rpg_action.set_resolve_callback(self._on_resolve_action)
        self._rpg_action.set_action_select_callback(self._on_action_key_selected)
        self._rpg_vna.set_submit_callback(self._on_vna_submit)
        # In-chat Action Builder (Phase 50.6) — relocates the V·N·A surface into
        # the left chat column. Wraps the same VnaActionPanel logic core, so
        # _refresh_vna_panel feeds it and submit() routes through _on_vna_submit.
        self._chat_action_builder = InChatActionBuilder(self._rpg_vna)
        self._chat.set_action_builder(self._chat_action_builder)
        self._rpg_campaign_id: str | None = None
        self._action_state = PlayerActionState()
        self._chat.set_actor_switch_callback(self._on_actor_switch)

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
        self._save_session()
        self._manager.disable()
        if self._active_thread is not None and self._active_thread.is_alive():
            self._active_thread.join(timeout=3.0)

    def on_draw(self) -> None:
        self.clear()
        draw_title_bar(
            self.window,
            mode="play",
            on_mode=lambda m: self.window.switch_mode(m),
        )
        self._chat.draw()
        self._map.draw()
        if self._dungeon is not None and self._edit_memory_rect:
            self._draw_edit_memory_btn()
        self._draw_rpg_toggle_btn()
        if self._rpg_open:
            self._rpg_side.draw()
        if getattr(self, "_overlay_open", False):
            self._draw_overlay_backdrop()
        self._manager.draw()

    def on_update(self, delta_time: float) -> None:
        self._chat.update(delta_time)
        try:
            result = self._result_queue.get_nowait()
        except queue.Empty:
            return
        self._llm_busy = False
        self._chat.set_busy(False)
        if result.error:
            self._chat.add_message("system", f"⚠ The dungeon is silent. ({result.error})")
        else:
            remembered, display = self._extract_remember(result.content)
            self._dm_history.append(LLMMessage(role="assistant", content=display))
            self._chat.add_message("dm", display)
            if remembered:
                self._auto_remember(remembered)

    def on_resize(self, width: int, height: int) -> None:
        self._reposition_panels(width, height)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        # Overlay is modal — absorb all clicks (save/cancel handled by UIManager)
        if getattr(self, "_overlay_open", False):
            return
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        pill = title_bar_mode_at(x, y, self.window)
        if pill and pill != "play":
            if pill == "library" and self._dungeon is not None:
                confirmed = self.window._ask_yes_no(
                    "Return to Library",
                    "Your session progress is saved. Return to Library?",
                )
                if not confirmed:
                    return
            self.window.switch_mode(pill)
            return
        # RPG panel toggle button (title bar)
        if self._rpg_toggle_rect and self._point_in_rect(x, y, self._rpg_toggle_rect):
            self._toggle_rpg_panel()
            return
        # RPG panel content area (absorbs clicks when open, content area only)
        if self._rpg_open:
            rpg_x = float(PANEL_CHAT_WIDTH) + self._map_area_w(self.window.width)
            content_h = float(self.window.height - CHROME_TOTAL_HEIGHT)
            if x >= rpg_x and y < content_h:
                tab_idx = self._rpg_side.hit_tab(x, y)
                if tab_idx is not None:
                    self._rpg_side.set_active(tab_idx)
                    if tab_idx == _TAB_MEM:
                        self._load_memory_entries()
                    elif tab_idx == _TAB_DBG:
                        self._build_context_bundle()
                elif self._rpg_side.active_tab == _TAB_CHAR:
                    delta = self._rpg_char.hit_picker(x, y)
                    if delta:
                        actor_id = self._rpg_char.cycle(delta)
                        if actor_id:
                            self._refresh_right_panel_from_actors(actor_id)
                            self._set_acting_actor(actor_id)
                elif self._rpg_side._active == _TAB_MEM:
                    self._handle_mem_click(x, y)
                return
        # Edit Memory button
        if (self._dungeon is not None and self._edit_memory_rect
                and self._point_in_rect(x, y, self._edit_memory_rect)):
            self.open_memory_overlay()
            return
        # Route clicks in chat panel area to the chat panel first
        if x < PANEL_CHAT_WIDTH:
            self._chat.on_mouse_press(x, y)
            return
        # Delegate to map panel — pan tool consumes the press
        if self._map.handle_mouse_press(x, y, button):
            return
        if self._dungeon is None or self._state is None:
            return

        pan_x, pan_y = self._map.pan_offset
        zoom = self._map.zoom_level
        level = self._dungeon.levels[self._state.current_level_idx]
        origin_x = PANEL_CHAT_WIDTH + PAD_MD + pan_x
        origin_y = PAD_MD + pan_y
        effective_cell_px = _CELL_PX * zoom

        cell_x = int((x - origin_x) / effective_cell_px)
        cell_y = int((y - origin_y) / effective_cell_px)

        for room in level.rooms:
            if (room.x <= cell_x < room.x + room.w
                    and room.y <= cell_y < room.y + room.h):
                self._state.current_room_id = room.id
                if room.id not in self._state.visited_rooms:
                    self._state.visited_rooms.append(room.id)
                total = len(self._dungeon.levels)
                self._map.update_state(self._state, total)
                self._chat.set_current_room(room.name, room.note or "", room_id=room.id)
                self._rpg_scene.set_scene(room.name, str(level.id))
                _log.debug("Selected room: %s", room.id)
                self._compact_history()
                self._dm_history.append(LLMMessage(role="user", content=f"We enter {room.name}."))
                self._chat.set_busy(True)
                self._spawn_dm_thread(room, level)
                self._save_session()
                return

        conn = self._renderer.hit_test_connection(
            level, self._state, x, y, origin_x, origin_y, zoom
        )
        if conn is not None:
            loops = [
                lp for lp in level.loops
                if conn.from_room in lp.rooms or conn.to_room in lp.rooms
            ]
            loop_info = ", ".join(lp.id for lp in loops) or "none"
            note_part = f": {conn.note}" if conn.note else ""
            msg = (
                f"Connection: {conn.from_room} → {conn.to_room}"
                f" [{conn.type}]{note_part} (loops: {loop_info})"
            )
            self._chat.add_message("dm", msg)
            _log.debug("Selected connection: %s → %s", conn.from_room, conn.to_room)

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> None:
        if x < PANEL_CHAT_WIDTH:
            self._chat.on_mouse_motion(x, y)
        self._map.handle_mouse_motion(x, y)

    def on_mouse_drag(self, x: float, y: float, dx: float, dy: float, buttons: int, modifiers: int) -> None:
        self._map.handle_mouse_drag(x, y, dx, dy, buttons)

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> None:
        self._map.handle_mouse_release(x, y, button)

    def on_mouse_scroll(self, x: float, y: float, scroll_x: int, scroll_y: int) -> None:
        if x < PANEL_CHAT_WIDTH:
            self._chat.on_mouse_scroll(x, y, float(scroll_y))
            return
        self._map.handle_mouse_scroll(x, y, scroll_x, scroll_y)

    def on_key_press(self, key: int, modifiers: int) -> None:
        if getattr(self, "_overlay_open", False) and key == arcade.key.ESCAPE:
            self.close_memory_overlay()
            return
        # Suppress map shortcuts while the MEM search box is active
        if self._rpg_open and self._rpg_side._active == _TAB_MEM:
            return
        self._map.handle_key_press(key)

    # ------------------------------------------------------------------
    # Dungeon loading
    # ------------------------------------------------------------------

    def load_dungeon_transient(self, dungeon: Dungeon) -> None:
        self._is_test_drive = True
        self._dungeon = dungeon
        self._state = SessionState(dungeon_id="__test_drive__", current_level_idx=0)
        level = dungeon.levels[0]
        self._map.load(level, self._state, len(dungeon.levels))
        self._map.set_loops_visible(True)  # loop chips are a test-drive affordance
        self._map.set_dungeon_title(dungeon.meta.title)
        self._chat.set_mode_label("Play Mode")
        self._chat.add_message(
            "dm",
            f'Loaded "{dungeon.meta.title}" — Level 1: {level.name}. '
            "Click rooms on the map to explore.",
        )
        _log.info("PlayView: loaded dungeon=%s (test drive)", dungeon.meta.title)
        self._refresh_memory_state()
        self._load_player_actors()
        self._sync_debug_level_id()
        self._focus_party_room()

    def load_dungeon_session(self, dungeon: Dungeon) -> None:
        self._is_test_drive = False
        self._dungeon = dungeon
        save_name = dungeon.meta.effective_name
        existing = self._repo.load_session(save_name)
        if existing is not None:
            self._state = existing
            level = dungeon.levels[existing.current_level_idx]
            self._map.load(level, self._state, len(dungeon.levels))
            self._map.set_dungeon_title(dungeon.meta.title)
            self._chat.set_mode_label("Play Mode")
            self._chat.add_message(
                "dm",
                f"Resuming session — Level {existing.current_level_idx + 1}: {level.name}.",
            )
        else:
            self._state = SessionState(dungeon_id=save_name, current_level_idx=0)
            level = dungeon.levels[0]
            self._map.load(level, self._state, len(dungeon.levels))
            self._map.set_dungeon_title(dungeon.meta.title)
            self._chat.set_mode_label("Play Mode")
            self._chat.add_message(
                "dm",
                f'Loaded "{dungeon.meta.title}" — Level 1: {level.name}. '
                "Click rooms on the map to explore.",
            )
        # Loop pattern chips are an authoring/test-drive affordance, not shown in
        # a normal play session.
        self._map.set_loops_visible(False)
        _log.info("PlayView: loaded dungeon=%s (session)", dungeon.meta.title)
        self._refresh_memory_state()
        self._load_player_actors()
        self._sync_debug_level_id()
        self._focus_party_room()

    def load_dungeon(self, dungeon: Dungeon) -> None:
        """Alias for load_dungeon_transient — kept until window.py callers are updated."""
        self.load_dungeon_transient(dungeon)

    def _save_session(self) -> None:
        if not self._is_test_drive and self._state is not None:
            self._repo.save_session(self._state)

    # ------------------------------------------------------------------
    # Player actors
    # ------------------------------------------------------------------

    def set_session_repo(self, repo: DungeonRepository) -> None:
        """Switch the repository used for session and room-memory persistence."""
        self._repo = repo

    def set_rpg_context(
        self,
        mem_repo: MemoryRepository | None,
        campaign_id: str | None,
        portraits_dir: Path | None = None,
    ) -> None:
        """Update the active RPG repository and campaign id. Closes the previous repo if any."""
        old = getattr(self, "_mem_repo", None)
        if old is not None and old is not mem_repo:
            try:
                old.close()
            except Exception:
                pass
        self._mem_repo = mem_repo
        self._rpg_campaign_id = campaign_id
        self._portraits_dir = portraits_dir
        self._load_player_actors()
        # set_rpg_context runs *after* load_dungeon_session (where _focus_party_room
        # fires while _mem_repo is still None), so this is the first point where the
        # room, actors, and repo are all available. Populate the in-chat Action
        # Builder now so it is usable on load.
        self._refresh_vna_panel()

    def _sync_debug_level_id(self) -> None:
        if self._rpg_debug is None or self._state is None:
            return
        idx = self._state.current_level_idx
        self._rpg_debug.set_current_level_id(f"level-{idx + 1}")
        if self._dungeon is not None:
            room_ids = {r.id for r in self._dungeon.levels[idx].rooms}
            self._rpg_debug.set_current_level_room_ids(room_ids)

    def _load_player_actors(self) -> None:
        if not hasattr(self, "_mem_repo") or self._mem_repo is None:
            return
        if not hasattr(self, "_state") or self._state is None:
            return
        campaign_id = getattr(self, "_rpg_campaign_id", None) or self._state.dungeon_id
        raw = self._mem_repo.get_actors_by_campaign(campaign_id)
        actor_states = []
        for a in raw:
            ratings = {
                r["action_key"]: r["rating"]
                for r in self._mem_repo.get_actor_action_ratings(a["actor_id"])
            }
            stress = {
                t["track_key"]: StressTrack(
                    track_key=t["track_key"],
                    capacity=t["capacity"],
                    filled=t["filled"],
                )
                for t in self._mem_repo.get_actor_stress_tracks(a["actor_id"])
            }
            actor_states.append(ActorState(
                actor_id=a["actor_id"],
                campaign_id=a["campaign_id"],
                actor_type=a["actor_type"],
                slug=a["slug"],
                display_name=a["display_name"],
                status=a["status"],
                actions=ratings,
                stress=stress,
                playbook_slug=a.get("playbook_slug"),
            ))
        pc_actors = filter_player_actors(actor_states)
        self._rpg_action.set_actors(pc_actors)
        self._rpg_char.set_party(pc_actors)
        if pc_actors:
            self._refresh_right_panel_from_actors(pc_actors[0].actor_id)
        pc_ids = [a.actor_id for a in pc_actors]
        if pc_ids and hasattr(self, "_action_state"):
            self._action_state.set_actor_roster(pc_ids)
        self._refresh_chat_mini_card()

    def _load_memory_entries(self) -> None:
        if self._mem_repo is None:
            return
        campaign_id = self._rpg_campaign_id or (self._state.dungeon_id if self._state else None)
        if campaign_id is None:
            return
        raw = self._mem_repo.get_memory_entries_by_campaign(campaign_id)
        entries = []
        for r in raw:
            tags = self._mem_repo.get_memory_tags(r["memory_id"])
            entries.append(MemoryEntry(
                memory_id=r["memory_id"],
                campaign_id=r["campaign_id"],
                type=r["type"],
                title=r["title"],
                summary=r["summary"],
                status=r["status"],
                importance=r["importance"],
                markdown_path=r["markdown_path"],
                checksum=r["checksum"],
                tags=tags,
            ))
        self._rpg_memory.set_entries(entries)

    def _run_chat_action(
        self,
        campaign_id: str,
        actor_id: str,
        action_key: str,
        intent: str,
    ) -> None:
        if self._rpg_service is None:
            self._chat.add_message("system", "RPG service unavailable.")
            return
        actor = next(
            (a for a in self._rpg_action._actors if a.actor_id == actor_id),
            None,
        )
        dice_pool = (actor.actions.get(action_key) or 1) if actor else 1
        actor_name = actor.display_name if actor else actor_id
        request = self._rpg_action._build_request(
            campaign_id=campaign_id,
            actor_id=actor_id,
            intent=intent,
            action_key=action_key,
            push_yourself=False,
            momentum_spend=0,
            dice_pool=dice_pool,
        )
        try:
            resolution, _event = self._rpg_service.resolve_action(request)
            summary = self._rpg_action._format_result(resolution)
            self._rpg_action.store_result(summary)
            reaction = self._apply_world_reaction(resolution)
            self._run_proposal_pipeline(resolution, campaign_id)
            self._chat.add_message(
                "system",
                format_mechanical_bubble(actor_name, action_key, resolution, reaction),
            )
            if self._dungeon is not None and self._state is not None:
                level = self._dungeon.levels[self._state.current_level_idx]
                room = None
                if self._state.current_room_id:
                    room_map = {r.id: r for r in level.rooms}
                    room = room_map.get(self._state.current_room_id)
                if room is None:
                    self._chat.add_message("system", "Select a room to get DM narration.")
                else:
                    outcome = resolution.outcome.upper()
                    msg = (
                        f"{actor_name} [{action_key.upper()}] {intent or '(no intent)'}"
                        f" — {outcome}"
                    )
                    self._compact_history()
                    self._dm_history.append(LLMMessage(role="user", content=msg))
                    self._chat.set_busy(True)
                    self._spawn_dm_thread(room, level)
            self._refresh_right_panel_from_actors(actor_id)
        except Exception:
            _log.exception("_run_chat_action failed")

    def _refresh_right_panel_from_actors(self, actor_id: str) -> None:
        """Sync right panel inspector with the actor who just acted."""
        actors = getattr(self._rpg_action, "_actors", [])
        if not actors:
            return
        actor = next((a for a in actors if a.actor_id == actor_id), actors[0])
        self._rpg_char.set_actor(actor)
        if actor.playbook_slug:
            from dungeon_daddy.rpg.playbook import PlaybookLibrary
            try:
                self._rpg_char.set_playbook(PlaybookLibrary().get(actor.playbook_slug))
            except KeyError:
                self._rpg_char.set_playbook(None)
        else:
            self._rpg_char.set_playbook(None)
        if self._mem_repo is not None:
            self._rpg_char.set_abilities(self._mem_repo.get_actor_abilities(actor.actor_id))
        self._refresh_chat_mini_card()
        if self._mem_repo is not None and self._rpg_campaign_id:
            from dungeon_daddy.rpg.models import FalloutRecord
            raw = self._mem_repo.get_fallout_records(self._rpg_campaign_id, actor.actor_id)
            entries = [
                FalloutRecord(
                    fallout_id=r["fallout_id"],
                    campaign_id=r["campaign_id"],
                    actor_id=r["actor_id"],
                    track_key=r["track_key"],
                    severity=r["severity"],
                    title=r["title"],
                    summary=r["summary"],
                    status=r["status"],
                )
                for r in raw
            ]
            self._rpg_fallout.set_entries(entries)

    def _on_action_key_selected(self, action_key: str) -> None:
        try:
            self._action_state.select_action(action_key)
        except ValueError:
            pass

    def _on_pending_chip_click(self, label: str) -> None:
        if label == "No Roll":
            self._do_no_roll_from_chip()
        else:
            self._do_action_from_chip(label.lower())

    def _do_action_from_chip(self, action_key: str) -> None:
        if not self._action_state.awaiting_confirmation:
            return
        pi = self._action_state.pending_intent
        if pi is None:
            return
        intent_text = pi.raw_text
        try:
            self._action_state.select_action(action_key)
        except ValueError:
            return
        campaign_id = self._rpg_campaign_id or (self._state.dungeon_id if self._state else "")
        actor_id = self._action_state.actor_id or ""
        self._chat.resolve_active_card(action_key.upper())
        self._action_state.reset()
        self._run_chat_action(campaign_id, actor_id, action_key, intent_text)

    def _refresh_chat_mini_card(self) -> None:
        if not hasattr(self, "_action_state"):
            return
        actor_id = self._action_state.actor_id
        actors = getattr(self._rpg_action, "_actors", [])
        actor = next((a for a in actors if a.actor_id == actor_id), None) if actor_id else None
        portraits_dir = getattr(self, "_portraits_dir", None)
        self._chat.set_actor_mini_card(
            build_actor_mini_card(actor, portraits_dir=portraits_dir) if actor else None
        )
        self._chat.set_has_multiple_actors(self._action_state.has_multiple_actors)

    def _on_actor_switch(self, direction: str) -> None:
        if self._action_state.awaiting_confirmation:
            return
        if direction == "prev":
            self._action_state.select_prev_actor()
        else:
            self._action_state.select_next_actor()
        self._refresh_chat_mini_card()
        # The in-chat Action Builder is bound to the acting actor (its sentence,
        # carried-item nouns, and abilities), so re-populate it on a switch —
        # mirroring the CHAR-tab picker's _set_acting_actor path.
        self._refresh_vna_panel()

    def _do_no_roll_from_chip(self) -> None:
        if not self._action_state.awaiting_confirmation:
            return
        pi = self._action_state.pending_intent
        narration_text = pi.raw_text if pi else ""
        self._chat.resolve_active_card("No Roll")
        self._action_state.reset()
        if self._dungeon is None or self._state is None:
            return
        level = self._dungeon.levels[self._state.current_level_idx]
        room = None
        if self._state.current_room_id:
            room_map = {r.id: r for r in level.rooms}
            room = room_map.get(self._state.current_room_id)
        if room is None:
            self._chat.add_message("system", "Click a room first to give the DM context.")
            return
        self._compact_history()
        self._dm_history.append(LLMMessage(role="user", content=narration_text))
        self._chat.set_busy(True)
        self._spawn_dm_thread(room, level)

    def _on_resolve_action(
        self,
        campaign_id: str,
        actor_id: str,
        intent: str,
        action_key: str,
        push_yourself: bool,
        momentum_spend: int,
        dice_pool: int,
    ) -> None:
        if self._rpg_service is None:
            return
        request = self._rpg_action._build_request(
            campaign_id=campaign_id,
            actor_id=actor_id,
            intent=intent,
            action_key=action_key,
            push_yourself=push_yourself,
            momentum_spend=momentum_spend,
            dice_pool=dice_pool,
        )
        try:
            resolution, _event = self._rpg_service.resolve_action(request)
            summary = self._rpg_action._format_result(resolution)
            self._rpg_action.store_result(summary)
            self._apply_world_reaction(resolution)
            self._run_proposal_pipeline(resolution, campaign_id)
            if self._dungeon is not None and self._state is not None:
                level = self._dungeon.levels[self._state.current_level_idx]
                room = None
                if self._state.current_room_id:
                    room_map = {r.id: r for r in level.rooms}
                    room = room_map.get(self._state.current_room_id)
                if room is None:
                    self._chat.add_message("system", "Select a room to get DM narration.")
                else:
                    outcome = summary.get("outcome", "?").upper()
                    dice = summary.get("dice", [])
                    actor_name = next(
                        (a.display_name for a in self._rpg_action._actors if a.actor_id == actor_id),
                        actor_id,
                    )
                    msg = (
                        f"{actor_name} [{action_key.upper()}] {intent or '(no intent)'}"
                        f" — {outcome}  dice={dice}"
                    )
                    self._compact_history()
                    self._dm_history.append(LLMMessage(role="user", content=msg))
                    self._chat.set_busy(True)
                    self._spawn_dm_thread(room, level)
            self._refresh_right_panel_from_actors(actor_id)
        except Exception:
            _log.exception("resolve_action failed")

    # ------------------------------------------------------------------
    # Dungeon navigation (Phase 48) — click-to-move
    # ------------------------------------------------------------------

    def _focus_party_room(self) -> None:
        """Reflect the party's current room in the map + side panels.

        Used on load/resume so the player always opens a save where the party
        actually is: the room is selected on the map (selection frame + detail
        overlay) and the chat/scene panels are populated. No narration.
        """
        if self._dungeon is None or self._state is None:
            return
        room_id = self._state.current_room_id
        if not room_id:
            return
        level = self._dungeon.levels[self._state.current_level_idx]
        room = {r.id: r for r in level.rooms}.get(room_id)
        if room is None:
            return
        self._map.set_selected_room(room.id)
        self._chat.set_current_room(room.name, room.note or "", room_id=room.id)
        self._rpg_scene.set_scene(room.name, str(level.id))

    def _clear_dungeon_connection_lock(self, from_room: str, to_room: str) -> None:
        """Clear lock styling on the dungeon model connection so the map re-renders it open."""
        if self._dungeon is None or self._state is None:
            return
        level = self._dungeon.levels[self._state.current_level_idx]
        for conn in level.connections:
            if conn.from_room == from_room and conn.to_room == to_room:
                conn.connection_style = None
                conn.layout_connection_role = None
                break

    def _acting_actor(self):
        """The actor a Card acts as: the selected one, else the first PC."""
        actors = getattr(self._rpg_action, "_actors", []) or []
        actor_id = getattr(self, "_action_state", None) and self._action_state.actor_id
        if actor_id:
            return next((a for a in actors if a.actor_id == actor_id), actors[0] if actors else None)
        return actors[0] if actors else None

    def _set_acting_actor(self, actor_id: str) -> None:
        """Make ``actor_id`` the actor whose Cards/rolls resolve.

        Drives the acting-actor selection from the CHAR-tab picker so the
        Character Sheet, the chat actor mini-card, and the ACTION panel all
        agree on whose turn it is (``_acting_actor`` reads
        ``_action_state.actor_id``).
        """
        self._action_state.select_actor(actor_id)
        self._refresh_chat_mini_card()
        self._refresh_vna_panel()

    def _room_world_flags(self, room_id: str) -> set[str]:
        """World-context flags gating conditional adverbs (mirrors the room-context build)."""
        flags: set[str] = set()
        actors = getattr(self._rpg_action, "_actors", []) or []
        if max((a.actions.get("sense", 0) for a in actors), default=0) >= 1:
            flags.add("can_sense")
        exits = self._mem_repo.get_exits_by_room(self._rpg_campaign_id, room_id)
        if any(e.get("status") == "one_way" for e in exits):
            flags.add("one_way")
        if any(e.get("connector_type") == "ritual_gate" for e in exits):
            flags.add("ritual_connector")
        if any(
            o["archetype"] == "trap" and o["current_state"] == "armed"
            for o in self._mem_repo.get_objects_by_room(self._rpg_campaign_id, room_id)
        ):
            flags.add("armed_trap")
        return flags

    def _refresh_vna_panel(self) -> None:
        """Populate the VNA action panel from the current room + acting actor."""
        from dungeon_daddy.memory.context_bundle import build_room_noun_context

        if (self._mem_repo is None or self._rpg_campaign_id is None
                or self._state is None or not self._state.current_room_id):
            return
        actor = self._acting_actor()
        if actor is None:
            return
        room_id = self._state.current_room_id
        room_context = build_room_noun_context(self._mem_repo, self._rpg_campaign_id, room_id)
        room_context = self._prepare_vna_exits(room_context, room_id)
        # Party PCs move as a group — their location is in session state, not
        # per-actor room_id, so we inject them here from the loaded actor roster.
        all_actors = getattr(self._rpg_action, "_actors", []) or []
        room_context = {
            **room_context,
            "party": [
                {"actor_id": a.actor_id, "display_name": a.display_name}
                for a in all_actors
                if a.actor_id != actor.actor_id
            ],
        }
        actor_dict = {
            "actor_id": actor.actor_id,
            "display_name": actor.display_name,
            "carried_items": self._mem_repo.get_items_by_actor(actor.actor_id),
        }
        self._rpg_vna.set_context(
            actor_abilities=self._mem_repo.get_actor_abilities(actor.actor_id),
            room_context=room_context,
            actor=actor_dict,
            playbook_slug=actor.playbook_slug or "",
            world_flags=self._room_world_flags(room_id),
        )
        # Retain the prepared context so the lighter overlay-push path
        # (_on_overlay_noun_click) can rebuild the "Things Here" view-model
        # without re-running set_context, which would reset the noun selection.
        self._last_room_context = room_context
        self._last_actor_dict = actor_dict
        # Feed the map's "Things Here" overlay from the same room context, so it
        # auto-tracks the current room (Phase 50.6 §5). The in-chat Action
        # Builder reads _rpg_vna's options live each draw, so no widget rebuild
        # is needed here.
        self._push_things_here_overlay()

    def _push_things_here_overlay(self) -> None:
        """Push the current room contents + builder selection to the map overlay.

        Rebuilds the :class:`RoomThings` view-model from the retained room
        context (cheap; no set_context) and marks the builder's selected noun so
        its row shows the larger TEAL marker (Phase 50.6 §5.3). Safe to call
        before the first refresh.
        """
        from dungeon_daddy.rpg.action_options import room_things

        map_panel = getattr(self, "_map", None)
        room_context = getattr(self, "_last_room_context", None)
        if map_panel is None or room_context is None:
            return
        actor_dict = getattr(self, "_last_actor_dict", {})
        selected = self._rpg_vna.selected_noun_option()
        selected_noun_id = selected.noun_id if selected is not None else None
        map_panel.set_things_here(
            room_things(room_context, actor_dict),
            selected_noun_id=selected_noun_id,
        )

    def _on_overlay_noun_click(self, noun_id: str) -> None:
        """Overlay "Things Here" row click → act on the clicked noun (§5.3).

        The two most common overlay actions are done in one click, no verb pick:
        an **open exit** is walked through (``move``) and a **loose item** is
        picked up (``pick_up``) by the acting character. Any other noun (incl. a
        *locked* exit, which can't be walked) just fills the builder's noun slot
        and re-pushes the overlay so the clicked row shows its selection cue.
        Selecting does **not** rebuild the panel context — the room is unchanged,
        and a full refresh would reset the selection back to the default noun.
        """
        from dungeon_daddy.rpg.action_options import (
            SOURCE_EXIT, SOURCE_LOOSE_ITEM, VERB_MOVE, VERB_PICK_UP,
        )

        _AUTO_VERB = {SOURCE_EXIT: VERB_MOVE, SOURCE_LOOSE_ITEM: VERB_PICK_UP}
        clicked = next(
            (n for n in self._rpg_vna._nouns if n.noun_id == noun_id), None
        )
        auto_verb = _AUTO_VERB.get(clicked.source) if clicked is not None else None
        if auto_verb is not None:
            self._rpg_vna.select_verb(auto_verb)
            self._rpg_vna.select_noun(noun_id)
            self._rpg_vna.submit()
            return
        self._rpg_vna.select_noun(noun_id)
        self._push_things_here_overlay()

    def _prepare_vna_exits(self, room_context: dict, room_id: str) -> dict:
        """Player-facing exit nouns: drop unknown exits and disambiguate labels.

        Hidden/sealed exits aren't surfaced as move targets. Same-type exits
        ('Door' x2) are relabelled with a compass direction, upgrading to the
        destination room name once that room has been visited (immersion-safe —
        see :func:`dungeon_daddy.rpg.exit_labels.exit_noun_label`).
        """
        from dungeon_daddy.rpg.exit_labels import exit_noun_label
        from dungeon_daddy.rpg.room_context import PLAYER_KNOWN_EXIT_STATUSES

        rooms_by_id, from_room = self._current_level_rooms(room_id)
        visited = set(self._state.visited_rooms) if self._state else set()
        prepared = [
            {
                **ext,
                "label": exit_noun_label(
                    ext, from_room=from_room,
                    rooms_by_id=rooms_by_id, visited_rooms=visited,
                ),
            }
            for ext in room_context.get("exits", [])
            if ext.get("status") in PLAYER_KNOWN_EXIT_STATUSES
        ]
        return {**room_context, "exits": prepared}

    def _current_level_rooms(self, room_id: str):
        """``({room_id: positioned room}, current room)`` for the active level.

        Positions come from the **rendered layout** (the same
        ``run_layout_pipeline`` output the map draws), so exit compass
        directions match what the player sees — the layout re-grids rooms by
        their connections, which can move a raw "far east" room directly south
        of the hub. Falls back to raw geometry if the layout can't be built,
        and to ``({}, None)`` when no dungeon is loaded.
        """
        if self._dungeon is None or self._state is None:
            return {}, None
        idx = self._state.current_level_idx
        if not (0 <= idx < len(self._dungeon.levels)):
            return {}, None
        from dungeon_daddy.map.dungeon_layout import run_layout_pipeline

        level = self._dungeon.levels[idx]
        names = {r.id: r.name for r in level.rooms}
        try:
            result = run_layout_pipeline(level)
        except Exception:
            rooms = {r.id: r for r in level.rooms}
            return rooms, rooms.get(room_id)
        rooms = {
            rid: _PositionedRoom(
                x=rect.x, y=rect.y, w=rect.w, h=rect.h, name=names.get(rid, ""),
            )
            for rid, rect in result.rooms.items()
        }
        return rooms, rooms.get(room_id)

    def _on_vna_submit(self, card) -> None:
        """Route a validated ``ActionCard`` to the engine.

        Three branches: (1) ``look`` — read-only description fetch, no dice,
        no state change; (2) mutation verbs via ``resolve_card`` (``activate``
        pre-routes through trigger selection); (3) skill verbs — action roll.
        """
        from dungeon_daddy.rpg.action_options import (
            VERB_ACTIVATE, VERB_LOOK, VERB_USE,
            SOURCE_EXIT, SOURCE_LOCKED_EXIT, SOURCE_OBJECT,
        )
        from dungeon_daddy.rpg.action_resolution import resolve_card
        from dungeon_daddy.rpg.command import MoveParty

        actor = self._acting_actor()
        if actor is None:
            return

        if card.verb == VERB_LOOK:
            self._on_look_submit(card)
            return

        if card.verb == VERB_ACTIVATE:
            self._on_activate_submit(card, actor)
            return

        if card.verb == VERB_USE and card.target_id is not None:
            target_noun = next(
                (n for n in self._rpg_vna._nouns if n.noun_id == card.target_id),
                None,
            )
            if target_noun and target_noun.source in {SOURCE_EXIT, SOURCE_LOCKED_EXIT}:
                item_noun = next(
                    (n for n in self._rpg_vna._nouns if n.noun_id == card.noun_id),
                    None,
                )
                item_slug = item_noun.slug if item_noun else None
                if item_slug and self._mem_repo is not None:
                    from dungeon_daddy.rpg.unlock_exit import clear_exit_key_requirement
                    exit_row = self._mem_repo.get_exit_by_id(card.target_id)
                    if exit_row and exit_row.get("requires_item_slug") == item_slug:
                        clear_exit_key_requirement(
                            card.target_id, self._rpg_campaign_id or "", self._mem_repo
                        )
                        self._clear_dungeon_connection_lock(
                            exit_row["from_room_id"], exit_row["to_room_id"]
                        )
                        from dungeon_daddy.rpg.exit_labels import LOCK_PREFIX
                        exit_label = target_noun.label.removeprefix(LOCK_PREFIX)
                        self._chat.add_message("system", f"{exit_label}: unlocked.")
                        self._refresh_vna_panel()
                        return
                self._on_exit_move(card.target_id, card.adverb, item_slug=item_slug)
                return
            if target_noun and target_noun.source == SOURCE_OBJECT:
                from dungeon_daddy.rpg.action_options import ActionCard
                activate_card = ActionCard(
                    verb=VERB_ACTIVATE, noun_id=card.target_id, adverb=card.adverb,
                )
                self._on_activate_submit(activate_card, actor)
                return

        command = resolve_card(card, actor_id=actor.actor_id)
        if command is None:
            self._resolve_vna_roll(card, actor)
        elif isinstance(command, MoveParty):
            self._on_exit_move(command.exit_id, command.how)
        else:
            self._apply_vna_command(command)

    def _on_look_submit(self, card) -> None:
        """Read-only branch: fetch the noun's authoritative description and post it.

        No dice rolled, no state changed. The description is ground truth —
        it can gate puzzles (e.g. journal → key clue) and must never be
        LLM-invented. The chat bubble makes it visible; the DM agent sees it
        in history for narration context on subsequent turns.
        """
        description = self._look_up_noun_description(card.noun_id)
        noun_label = card.noun_id
        for noun in (getattr(self, "_rpg_vna", None) and self._rpg_vna._nouns or []):
            if noun.noun_id == card.noun_id:
                noun_label = noun.label
                break
        if description:
            self._chat.add_message("system", f"{noun_label}: {description}")
        else:
            self._chat.add_message("system", f"⚠ Nothing to read about {noun_label}.")

    def _look_up_noun_description(self, noun_id: str) -> str | None:
        """Return the authoritative description for ``noun_id``, or ``None``."""
        if self._mem_repo is None:
            return None
        obj = self._mem_repo.get_room_object(noun_id)
        if obj is not None:
            return obj.get("description") or None
        campaign_id = self._rpg_campaign_id
        if campaign_id is not None:
            items = self._mem_repo.get_items(campaign_id)
            item = next((i for i in items if i["item_id"] == noun_id), None)
            if item is not None:
                return item.get("description") or None
        actor = self._mem_repo.get_actor(noun_id)
        if actor is not None:
            return actor.get("description") or actor.get("display_name") or None
        return None

    def _on_activate_submit(self, card, actor) -> None:
        """Handle ``activate`` verb: pick trigger from the object, then route.

        Looks up the object's current transitions, selects the first one
        matching the current state, and routes deterministic transitions to the
        command pipeline and contested transitions to the action-roll path.
        """
        from dungeon_daddy.rpg.action_options import ActionCard
        from dungeon_daddy.rpg.action_resolution import resolve_card

        if self._mem_repo is None or self._rpg_campaign_id is None:
            return

        obj = self._mem_repo.get_room_object(card.noun_id)
        if obj is None:
            self._chat.add_message("system", f"⚠ Object not found: {card.noun_id}")
            return

        transition = next(
            (t for t in obj.get("transitions", [])
             if t.get("from_state") == obj.get("current_state")),
            None,
        )
        if transition is None:
            self._chat.add_message("system", f"⚠ Nothing to do with this object right now.")
            return

        if transition.get("contested"):
            roll_verb = transition.get("action_verb") or "fight"
            roll_card = ActionCard(verb=roll_verb, noun_id=card.noun_id, adverb=card.adverb)
            self._resolve_vna_roll(roll_card, actor)
        else:
            command = resolve_card(card, actor_id=actor.actor_id, trigger=transition["trigger"])
            if self._apply_vna_command(command):
                noun_label = obj.get("display_name") or card.noun_id
                from_state = obj.get("current_state", "")
                to_state = transition.get("to_state", "activated")
                self._chat.add_message("system", f"{noun_label}: {to_state}.")
                self._narrate_object_transition(actor, noun_label, from_state, to_state, transition)

    def _narrate_object_transition(self, actor, noun_label: str, from_state: str, to_state: str, transition: dict) -> None:
        """Inject the deterministic transition result into DM history and request narration."""
        if self._dungeon is None or self._state is None:
            return
        level = self._dungeon.levels[self._state.current_level_idx]
        room = {r.id: r for r in level.rooms}.get(self._state.current_room_id or "")
        if room is None:
            return
        from dungeon_daddy.llm.agents.dm_agent import LLMMessage
        self._compact_history()
        self._dm_history.append(LLMMessage(
            role="user",
            content=(
                f"{actor.display_name} {transition.get('trigger', 'activates')} the {noun_label}. "
                f"[{noun_label}: {from_state} → {to_state}]"
            ),
        ))
        self._chat.set_busy(True)
        self._spawn_dm_thread(room, level)

    def _apply_vna_command(self, command) -> bool:
        """Validate + apply a non-move mutation command, then refresh.

        Returns True if the command was accepted and applied, False if rejected.
        """
        from dungeon_daddy.rpg.command_applier import apply_command
        from dungeon_daddy.rpg.command_validator import validate_command

        if self._mem_repo is None or self._rpg_campaign_id is None:
            return False
        room_id = self._state.current_room_id if self._state else None
        validation = validate_command(
            command, self._mem_repo, self._rpg_campaign_id, party_room_id=room_id,
        )
        if not validation.accepted:
            self._chat.add_message("system", f"⚠ Can't do that: {validation.rejection_reason}")
            return False
        apply_command(command, validation, self._mem_repo, self._rpg_campaign_id)
        self._refresh_vna_panel()
        return True

    def _resolve_vna_roll(self, card, actor) -> None:
        """Resolve a skill-verb Card as an action roll and narrate the outcome."""
        from dungeon_daddy.rpg.action_resolution import resolve_card_roll

        if self._rpg_service is None or self._state is None:
            return
        campaign_id = self._rpg_campaign_id or self._state.dungeon_id
        card_roll = resolve_card_roll(
            card,
            campaign_id=campaign_id,
            actor={"actor_id": actor.actor_id, "actions": actor.actions},
        )
        resolution = card_roll.resolution
        reaction = self._apply_world_reaction(resolution)
        self._run_proposal_pipeline(resolution, campaign_id)
        self._chat.add_message(
            "system",
            format_mechanical_bubble(actor.display_name, card.verb, resolution, reaction),
        )
        if self._dungeon is not None and self._state.current_room_id:
            level = self._dungeon.levels[self._state.current_level_idx]
            room = {r.id: r for r in level.rooms}.get(self._state.current_room_id)
            if room is not None:
                noun_label = self._rpg_vna.noun_label_for(card.noun_id) or card.noun_id
                msg = (
                    f"{actor.display_name} [{card.verb.upper()}] {noun_label}"
                    f" ({card.adverb}) — {resolution.outcome.upper()}"
                )
                self._compact_history()
                self._dm_history.append(LLMMessage(role="user", content=msg))
                self._chat.set_busy(True)
                self._spawn_dm_thread(room, level)
        self._refresh_right_panel_from_actors(actor.actor_id)

    def _on_exit_move(self, exit_id: str, how: str, *, item_slug: str | None = None) -> None:
        """Apply an engine-validated party move, then narrate the result."""
        from dungeon_daddy.rpg.command import MoveParty
        from dungeon_daddy.rpg.move_party import apply_move_party

        if self._mem_repo is None or self._rpg_campaign_id is None or self._state is None:
            return

        new_session, result = apply_move_party(
            MoveParty(exit_id=exit_id, how=how),
            self._mem_repo, self._rpg_campaign_id, self._state,
            extra_inventory_slugs=[item_slug] if item_slug else None,
        )
        if not result.accepted:
            self._chat.add_message("system", f"⚠ Can't move: {result.rejection_reason}")
            return

        old_level_idx = self._state.current_level_idx
        self._state = new_session
        room = None
        level = None
        if self._dungeon is not None:
            level = self._dungeon.levels[self._state.current_level_idx]
            room = {r.id: r for r in level.rooms}.get(self._state.current_room_id)
            if self._state.current_level_idx != old_level_idx:
                self._viewed_level_idx = self._state.current_level_idx
                self._map.load(level, self._state, len(self._dungeon.levels))
            else:
                self._map.update_state(self._state, len(self._dungeon.levels))
            if room is not None:
                # Move the selection cursor with the party so the selected frame
                # and detail/info overlay follow — same treatment as a click.
                self._map.set_selected_room(room.id)
                self._chat.set_current_room(room.name, room.note or "", room_id=room.id)
                self._rpg_scene.set_scene(room.name, str(level.id))

        self._refresh_vna_panel()
        self._save_session()

        if room is not None and level is not None:
            flags = ", ".join(sorted(result.modifier_flags)) or "none"
            self._compact_history()
            self._dm_history.append(LLMMessage(
                role="user",
                content=f"We move {how} through the exit into {room.name}. (effects: {flags})",
            ))
            self._chat.set_busy(True)
            self._spawn_dm_thread(room, level)

    def _run_proposal_pipeline(self, resolution, campaign_id: str) -> None:
        if self._dm_agent is None or self._mem_repo is None or self._rpg_debug is None:
            return
        raw_clocks = self._mem_repo.get_clocks(campaign_id)
        known_clocks = [
            {"clock_id": r["clock_id"], "label": r["label"],
             "filled": r["filled"], "segments": r["segments"]}
            for r in raw_clocks
        ]
        known_clock_ids = [c["clock_id"] for c in known_clocks]
        all_actors = getattr(self._rpg_action, "_actors", []) or []
        known_actors = [{"actor_id": a.actor_id, "display_name": a.display_name} for a in all_actors]
        known_actor_ids = [a["actor_id"] for a in known_actors]
        player_actor_ids = [a.actor_id for a in filter_player_actors(all_actors)]

        room_name = ""
        room_note = ""
        if self._dungeon is not None and self._state is not None and self._state.current_room_id:
            idx = self._state.current_level_idx
            rooms = {r.id: r for r in self._dungeon.levels[idx].rooms}
            room = rooms.get(self._state.current_room_id)
            if room is not None:
                room_name = room.name
                room_note = room.note or ""

        raw = self._dm_agent.request_proposal(
            resolution=resolution,
            context_bundle=None,
            known_clocks=known_clocks,
            known_actors=known_actors,
            player_actor_ids=player_actor_ids,
            room_name=room_name,
            room_note=room_note,
        )
        proposal = parse_proposal(raw)
        if proposal is not None:
            validation_result = validate_proposal(
                proposal,
                known_clock_ids=set(known_clock_ids),
                known_actor_ids=set(known_actor_ids),
                player_actor_ids=set(player_actor_ids),
            )
            apply_result = apply_low_risk_proposals(
                validation_result,
                self._mem_repo,
                campaign_id,
                action_key=resolution.action_key,
                intent=resolution.intent,
            )
        else:
            validation_result = ValidationResult()
            apply_result = ApplyResult()
        self._rpg_debug.set_proposal_result(validation_result, apply_result)

    def _apply_world_reaction(self, resolution):
        if self._rpg_service is None or self._mem_repo is None:
            return None
        campaign_id = self._rpg_campaign_id
        if campaign_id is None:
            return None
        from dungeon_daddy.rpg.models import ClockState
        raw_clocks = self._mem_repo.get_clocks(campaign_id)
        threat_clocks = [
            ClockState(
                clock_id=r["clock_id"],
                campaign_id=r["campaign_id"],
                label=r["label"],
                segments=r["segments"],
                filled=r["filled"],
                status=r["status"],
                scope_room_id=r.get("scope_room_id"),
                action_tags=r.get("action_tags", []),
                clock_level=r.get("clock_level", "dungeon"),
                category=r.get("category"),
                level_id=r.get("level_id"),
                owner_actor_id=r.get("owner_actor_id"),
                stakes=r.get("stakes"),
                completion_effect=r.get("completion_effect"),
                visible_to_player=r.get("visible_to_player", True),
            )
            for r in raw_clocks
        ]
        pc_pairs = []
        for actor in self._rpg_action._actors:
            raw_tracks = self._mem_repo.get_actor_stress_tracks(actor.actor_id)
            tracks = {
                t["track_key"]: StressTrack(
                    track_key=t["track_key"],
                    capacity=t["capacity"],
                    filled=t["filled"],
                )
                for t in raw_tracks
            }
            pc_pairs.append((actor, tracks))
        current_room_id = self._state.current_room_id if self._state else None
        current_level_id = (
            f"level-{self._state.current_level_idx + 1}" if self._state else None
        )
        try:
            reaction, _evt = self._rpg_service.react_to_resolution(
                resolution, threat_clocks, pc_pairs,
                current_room_id=current_room_id,
                current_level_id=current_level_id,
            )
            for cl in reaction.clock_lines:
                self._mem_repo.update_clock_progress(
                    clock_id=cl.clock_id,
                    filled=cl.new_filled,
                    status=cl.new_status,
                )
            for sl in reaction.stress_lines:
                self._mem_repo.save_actor_stress_track(
                    actor_id=sl.actor_id,
                    track_key=sl.track_key,
                    capacity=next(
                        (
                            tracks[sl.track_key].capacity
                            for actor, tracks in pc_pairs
                            if actor.actor_id == sl.actor_id and sl.track_key in tracks
                        ),
                        4,
                    ),
                    filled=sl.new_filled,
                )
            # Sync in-memory actors so _refresh_right_panel_from_actors sees new values
            for sl in reaction.stress_lines:
                for actor in self._rpg_action._actors:
                    if actor.actor_id == sl.actor_id and sl.track_key in actor.stress:
                        actor.stress[sl.track_key].filled = sl.new_filled
            if self._rpg_debug is not None:
                self._rpg_debug.set_reaction(reaction)
            return reaction
        except Exception:
            _log.exception("world_reaction failed")
        return None

    # ------------------------------------------------------------------
    # Map variant switching
    # ------------------------------------------------------------------

    def set_map_renderer(self, renderer: GraphRenderer) -> None:
        self._renderer = renderer
        self._map.set_renderer(renderer)

    # ------------------------------------------------------------------
    # RPG side panel
    # ------------------------------------------------------------------

    def _map_area_w(self, window_w: int) -> float:
        return float(window_w - PANEL_CHAT_WIDTH - (_RPG_PANEL_W if self._rpg_open else 0))

    def _toggle_rpg_panel(self) -> None:
        if self._rpg_open:
            self._rpg_side.teardown()
        self._rpg_open = not self._rpg_open
        self._reposition_panels(self.window.width, self.window.height)

    # ------------------------------------------------------------------
    # Edit Memory Overlay
    # ------------------------------------------------------------------

    def has_level_memory(self) -> bool:
        if self._dungeon is None or self._state is None:
            return False
        level = self._dungeon.levels[self._state.current_level_idx]
        return bool(self._repo.load_room_memory(self._state.dungeon_id, level.id))

    def open_memory_overlay(self) -> None:
        if self._dungeon is None or self._state is None:
            return
        level = self._dungeon.levels[self._state.current_level_idx]
        content = self._repo.load_room_memory(self._state.dungeon_id, level.id)
        self._overlay_level_id = level.id
        self._overlay_content = content
        self._open_overlay_ui(content, level.id)

    def save_memory_overlay(self) -> None:
        if self._overlay_level_id is None:
            return
        if self._state is None:
            return
        input_widget = self._overlay_input
        content = input_widget.text if input_widget is not None else (self._overlay_content or "")
        self._repo.save_room_memory(self._state.dungeon_id, self._overlay_level_id, content)
        self.close_memory_overlay()

    def close_memory_overlay(self) -> None:
        self._overlay_level_id = None
        self._overlay_content = None
        self._close_overlay_ui()

    # ------------------------------------------------------------------
    # DM threading
    # ------------------------------------------------------------------

    def _build_context_bundle(self):
        """Build a ContextBundle snapshot on the main thread. Returns None when RPG state is unavailable."""
        if self._rpg_service is None or self._mem_repo is None or self._state is None:
            return None
        campaign_id = self._rpg_campaign_id or self._state.dungeon_id
        raw_actors = self._mem_repo.get_actors_by_campaign(campaign_id)
        actor_states = [
            ActorState(
                actor_id=a["actor_id"],
                campaign_id=a["campaign_id"],
                actor_type=a["actor_type"],
                slug=a["slug"],
                display_name=a["display_name"],
                status=a["status"],
            )
            for a in raw_actors
        ]
        focus_ids = [a.actor_id for a in filter_player_actors(actor_states)]
        builder = ContextBundleBuilder(
            campaign_id=campaign_id,
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=focus_ids,
            token_budget=2000,
            current_room_id=self._state.current_room_id,
        )
        try:
            bundle = builder.build(self._mem_repo)
            if self._rpg_debug is not None:
                self._rpg_debug.set_bundle(bundle)
            return bundle
        except Exception:
            _log.exception("ContextBundle build failed — proceeding without bundle")
            return None

    def _spawn_dm_thread(self, room: Room, level: Level) -> None:
        if self._llm_busy:
            return
        if self._dm_agent is None:
            self._result_queue.put(DMResult(content="", error="DM agent unavailable — OPENAI_API_KEY not set."))
            return
        assert self._state is not None
        assert self._dungeon is not None
        memory = self._repo.load_room_memory(self._state.dungeon_id, level.id)
        bundle = self._build_context_bundle()
        self._llm_busy = True
        _history = list(self._dm_history)
        _agent = self._dm_agent
        _dungeon = self._dungeon

        def _run() -> None:
            try:
                response = _agent.respond(
                    history=_history,
                    room=room,
                    level=level,
                    dungeon=_dungeon,
                    room_memory=memory,
                    context_bundle=bundle,
                )
                self._result_queue.put(DMResult(content=response))
            except Exception as exc:
                self._result_queue.put(DMResult(content="", error=str(exc)))
            finally:
                self._llm_busy = False

        t = threading.Thread(target=_run, daemon=True)
        self._active_thread = t
        t.start()

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_level_change(self, delta: int) -> None:
        if self._dungeon is None or self._state is None:
            return
        current_viewed = getattr(self, "_viewed_level_idx", self._state.current_level_idx)
        new_idx = current_viewed + delta
        if 0 <= new_idx < len(self._dungeon.levels):
            self._viewed_level_idx = new_idx
            level = self._dungeon.levels[new_idx]
            self._map.load(level, self._state, len(self._dungeon.levels), viewed_level_idx=new_idx)

    def _on_chat_send(self, text: str) -> None:
        self._chat.add_message("gm", text)
        if text.strip() == "/clear":
            self._dm_history = []
            self._chat.add_message("system", "💬 Conversation cleared.")
            return
        if text.startswith("/remember "):
            self._handle_remember(text[len("/remember "):])
            return
        if self._dungeon is None or self._state is None:
            self._chat.add_message("system", "No dungeon loaded.")
            return
        if self._action_state.action_key is not None:
            campaign_id = self._rpg_campaign_id or self._state.dungeon_id
            if not self._state.current_room_id:
                self._chat.add_message("system", "Select a room to resolve an action.")
                return
            pi = self._action_state.pending_intent
            intent_text = pi.raw_text if (self._action_state.awaiting_confirmation and pi) else text
            self._chat.resolve_active_card(self._action_state.action_key.upper())
            self._run_chat_action(
                campaign_id,
                self._action_state.actor_id or "",
                self._action_state.action_key,
                intent_text,
            )
            self._action_state.reset()
            return
        # 39.5: no-roll path — pending intent exists but player sent without selecting a chip
        if self._action_state.awaiting_confirmation:
            pi = self._action_state.pending_intent
            narration_text = pi.raw_text if pi else text
            self._chat.resolve_active_card("No Roll")
            self._action_state.reset()
            level = self._dungeon.levels[self._state.current_level_idx]
            room = None
            if self._state.current_room_id:
                room_map = {r.id: r for r in level.rooms}
                room = room_map.get(self._state.current_room_id)
            if room is None:
                self._chat.add_message("system", "Click a room first to give the DM context.")
                return
            self._compact_history()
            self._dm_history.append(LLMMessage(role="user", content=narration_text))
            self._chat.set_busy(True)
            self._spawn_dm_thread(room, level)
            return
        level = self._dungeon.levels[self._state.current_level_idx]
        room = None
        if self._state.current_room_id:
            room_map = {r.id: r for r in level.rooms}
            room = room_map.get(self._state.current_room_id)
        if room is None:
            self._chat.add_message("system", "Click a room first to give the DM context.")
            return
        # 39.3: classify intent — show framing instead of immediate narration
        suggestions = classify_intent(text)
        if suggestions:
            actor_id = self._action_state.actor_id or ""
            actor = next((a for a in self._rpg_action._actors if a.actor_id == actor_id), None)
            pending = PendingIntent(
                actor_id=actor_id,
                raw_text=text,
                suggested_action_keys=suggestions[:3],
                suggested_primary_action=suggestions[0],
            )
            self._action_state.set_pending_intent(pending)
            self._action_state.set_awaiting_confirmation(True)
            self._chat.add_message("system", _format_intent_framing(pending, actor.display_name if actor else None))
            self._chat.set_chip_click_callback(self._on_pending_chip_click)
            self._chat.add_action_card(
                actor.display_name if actor else actor_id,
                text,
                [k.upper() for k in suggestions[:3]] + ["No Roll"],
            )
            return
        self._compact_history()
        self._dm_history.append(LLMMessage(role="user", content=text))
        self._chat.set_busy(True)
        self._spawn_dm_thread(room, level)

    def _handle_remember(self, event: str) -> None:
        if self._dungeon is None or self._state is None:
            self._chat.add_message("system", "No dungeon loaded.")
            return
        if not self._state.current_room_id:
            self._chat.add_message("system", "No room selected — click a room first.")
            return
        level = self._dungeon.levels[self._state.current_level_idx]
        room_map = {r.id: r for r in level.rooms}
        room = room_map.get(self._state.current_room_id)
        room_name = room.name if room else self._state.current_room_id
        self._repo.append_room_event(
            self._state.dungeon_id, level.id,
            self._state.current_room_id, room_name, event,
        )
        self._chat.add_message("system", f"Remembered: {event}")
        self._refresh_memory_state()

    _REMEMBER_RE = re.compile(r"\[REMEMBER:\s*(.+?)\]", re.IGNORECASE)

    def _extract_remember(self, text: str) -> tuple[str | None, str]:
        match = self._REMEMBER_RE.search(text)
        if match is None:
            return None, text
        remembered = match.group(1).strip()
        cleaned = self._REMEMBER_RE.sub("", text, count=1).strip()
        return remembered, cleaned

    def _auto_remember(self, event: str) -> None:
        if self._dungeon is None or self._state is None:
            return
        if not self._state.current_room_id:
            return
        level = self._dungeon.levels[self._state.current_level_idx]
        room_map = {r.id: r for r in level.rooms}
        room = room_map.get(self._state.current_room_id)
        room_name = room.name if room else self._state.current_room_id
        self._repo.append_room_event(
            self._state.dungeon_id, level.id,
            self._state.current_room_id, room_name, event,
        )
        self._chat.add_message("system", f"📝 Noted: {event}")

    def _compact_history(self) -> None:
        _TOKEN_BUDGET = 2000
        while len(self._dm_history) >= 2:
            tokens = sum(len(m.content) for m in self._dm_history) // 4
            if tokens <= _TOKEN_BUDGET:
                break
            self._dm_history.pop(0)
            self._dm_history.pop(0)

    # ------------------------------------------------------------------
    # MEM tab click routing
    # ------------------------------------------------------------------

    def _handle_mem_click(self, x: float, y: float) -> None:
        action = self._rpg_memory.hit_button(x, y)
        if action == "approve":
            self._rpg_memory.approve_selected()
            self._persist_pending_memory_commit()
            return
        if action == "reject":
            self._rpg_memory.reject_selected()
            self._persist_pending_memory_commit()
            return
        entry = self._rpg_memory.hit_entry(x, y)
        if entry is not None:
            self._rpg_memory.select_entry(entry)

    def _persist_pending_memory_commit(self) -> None:
        commit = self._rpg_memory.pop_pending_commit()
        if commit is None or self._mem_repo is None:
            return
        self._mem_repo.update_memory_status(commit.memory_id, commit.status)

    # ------------------------------------------------------------------
    # Memory state cache
    # ------------------------------------------------------------------

    def _refresh_memory_state(self) -> None:
        self._has_memory = self.has_level_memory()

    # ------------------------------------------------------------------
    # Overlay UI helpers
    # ------------------------------------------------------------------

    def _overlay_card_rect(self) -> tuple[float, float, float, float]:
        w = self.window.width
        content_h = self.window.height - CHROME_TOTAL_HEIGHT
        map_area_w = float(w - PANEL_CHAT_WIDTH - PANEL_STEPPER_WIDTH)
        map_area_h = float(content_h - _OVERLAY_TAB_H)
        card_w = map_area_w * 0.85
        card_h = map_area_h * 0.80
        card_x = PANEL_CHAT_WIDTH + (map_area_w - card_w) / 2
        card_y = (map_area_h - card_h) / 2
        return card_x, card_y, card_w, card_h

    def _open_overlay_ui(self, content: str, level_id: int) -> None:
        if not getattr(self, "_ui_built", False):
            return
        card_x, card_y, card_w, card_h = self._overlay_card_rect()

        pad = PAD_MD
        btn_h = 28
        text_y = card_y + pad + btn_h + pad
        text_h = max(card_h - 2 * pad - btn_h - pad, 40.0)
        text_w = card_w - 2 * pad
        text_x = card_x + pad

        self._overlay_input = arcade.gui.UIInputText(
            x=text_x, y=text_y, width=int(text_w), height=int(text_h),
            text=content,
            font_name=(FONT_MONO,),
            font_size=TEXT_BASE,
            text_color=(*INK_1, 255),
            multiline=True,
        )

        btn_w = 80.0
        save_x = card_x + card_w / 2 - btn_w - pad / 2
        cancel_x = card_x + card_w / 2 + pad / 2

        save_btn = arcade.gui.UIFlatButton(
            x=save_x, y=card_y + pad,
            width=int(btn_w), height=btn_h,
            text="Save",
            style=_overlay_btn_style("teal"),
        )
        cancel_btn = arcade.gui.UIFlatButton(
            x=cancel_x, y=card_y + pad,
            width=int(btn_w), height=btn_h,
            text="Cancel",
            style=_overlay_btn_style("default"),
        )

        @save_btn.event
        def on_click(event: arcade.gui.UIOnClickEvent) -> None:
            self.save_memory_overlay()

        @cancel_btn.event  # type: ignore[no-redef]
        def on_click(event: arcade.gui.UIOnClickEvent) -> None:  # noqa: F811
            self.close_memory_overlay()

        self._manager.add(self._overlay_input)
        self._manager.add(save_btn)
        self._manager.add(cancel_btn)
        self._overlay_widgets = [self._overlay_input, save_btn, cancel_btn]
        self._overlay_open = True

    def _close_overlay_ui(self) -> None:
        if not hasattr(self, "_overlay_widgets"):
            return
        for w in self._overlay_widgets:
            try:
                self._manager.remove(w)
            except Exception:
                pass
        self._overlay_widgets.clear()
        self._overlay_input = None
        self._overlay_open = False

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_edit_memory_btn(self) -> None:
        assert self._edit_memory_rect is not None
        x, y, w, h = self._edit_memory_rect
        cx, cy = x + w / 2, y + h / 2
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, w, h), BG_2)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, w, h), TEAL, 1)
        arcade.draw_text(
            "Edit Memory", cx, cy,
            color=TEAL,
            font_size=TEXT_SM,
            font_name=FONT_UI,
            anchor_x="center",
            anchor_y="center",
        )

    def _draw_rpg_toggle_btn(self) -> None:
        if self._rpg_toggle_rect is None:
            return
        x, y, w, h = self._rpg_toggle_rect
        cx, cy = x + w / 2, y + h / 2
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, w, h), BG_2)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, w, h), LINE, 1)
        label = "RPG ‹" if self._rpg_open else "RPG ›"
        arcade.draw_text(
            label, cx, cy,
            color=INK_2,
            font_size=TEXT_SM,
            font_name=FONT_UI,
            anchor_x="center",
            anchor_y="center",
        )

    def _draw_overlay_backdrop(self) -> None:
        w = self.window.width
        content_h = self.window.height - CHROME_TOTAL_HEIGHT
        map_w = float(w - PANEL_CHAT_WIDTH - PANEL_STEPPER_WIDTH)
        map_cx = PANEL_CHAT_WIDTH + map_w / 2
        # Dim the map area
        arcade.draw_rect_filled(
            arcade.XYWH(map_cx, content_h / 2, map_w, float(content_h)),
            (*BG_0, 210),
        )
        # Opaque card
        card_x, card_y, card_w, card_h = self._overlay_card_rect()
        card_cx = card_x + card_w / 2
        card_cy = card_y + card_h / 2
        arcade.draw_rect_filled(arcade.XYWH(card_cx, card_cy, card_w, card_h), BG_1)
        arcade.draw_rect_outline(arcade.XYWH(card_cx, card_cy, card_w, card_h), LINE, 1)
        # Card title
        arcade.draw_text(
            "EDIT MEMORY",
            card_cx, card_y + card_h - PAD_MD,
            INK_3,
            font_size=TEXT_SM,
            font_name=FONT_MONO,
            anchor_x="center",
            anchor_y="top",
        )

    @staticmethod
    def _point_in_rect(x: float, y: float, rect: tuple[float, float, float, float]) -> bool:
        rx, ry, rw, rh = rect
        return bool(rx <= x < rx + rw and ry <= y < ry + rh)

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        w, h = self.window.width, self.window.height
        content_h = h - CHROME_TOTAL_HEIGHT
        map_x = float(PANEL_CHAT_WIDTH)
        map_w = self._map_area_w(w)

        self._chat.setup(self._manager, 0.0, 0.0, float(PANEL_CHAT_WIDTH), float(content_h))
        self._map.setup(self._manager, map_x, 0.0, map_w, float(content_h))
        if self._rpg_open:
            rpg_x = map_x + map_w
            self._rpg_side.setup(rpg_x, 0.0, float(_RPG_PANEL_W), float(content_h))
        # Re-apply dungeon state so stepper buttons get correct enabled/disabled
        # state even when load_dungeon() was called before the UI was built.
        if self._dungeon is not None and self._state is not None:
            level = self._dungeon.levels[self._state.current_level_idx]
            self._map.load(level, self._state, len(self._dungeon.levels))
        self._edit_memory_rect = self._compute_edit_btn_rect(w, content_h)
        self._rpg_toggle_rect = self._compute_rpg_toggle_rect(w, content_h)

    def _reposition_panels(self, w: int, h: int) -> None:
        if getattr(self, "_overlay_open", False):
            self._close_overlay_ui()
        content_h = h - CHROME_TOTAL_HEIGHT
        map_x = float(PANEL_CHAT_WIDTH)
        map_w = self._map_area_w(w)

        self._chat.resize(0.0, 0.0, float(PANEL_CHAT_WIDTH), float(content_h))
        # MapPanel teardown/rebuild on resize (simplest for Phase 6)
        self._map.teardown(self._manager)
        self._map.setup(self._manager, map_x, 0.0, map_w, float(content_h))
        if self._rpg_open:
            rpg_x = map_x + map_w
            self._rpg_side.setup(rpg_x, 0.0, float(_RPG_PANEL_W), float(content_h))
        if self._dungeon is not None and self._state is not None:
            level = self._dungeon.levels[self._state.current_level_idx]
            self._map.load(level, self._state, len(self._dungeon.levels))
        self._edit_memory_rect = self._compute_edit_btn_rect(w, content_h)
        self._rpg_toggle_rect = self._compute_rpg_toggle_rect(w, content_h)

    def _on_graph_room_select(self, room_id: str) -> None:
        if self._dungeon is None or self._state is None:
            return
        level = self._dungeon.levels[self._state.current_level_idx]
        room_map = {r.id: r for r in level.rooms}
        room = room_map.get(room_id)
        if room is None:
            return
        self._state.current_room_id = room.id
        if room.id not in self._state.visited_rooms:
            self._state.visited_rooms.append(room.id)
        total = len(self._dungeon.levels)
        self._map.update_state(self._state, total)
        self._chat.set_current_room(room.name, room.note or "", room_id=room.id)
        self._rpg_scene.set_scene(room.name, str(level.id))
        _log.debug("Graph: selected room %s", room.id)
        self._compact_history()
        self._dm_history.append(LLMMessage(role="user", content=f"We enter {room.name}."))
        self._chat.set_busy(True)
        self._spawn_dm_thread(room, level)
        self._save_session()

    def _on_graph_connection_select(self, from_room: str, to_room: str) -> None:
        if self._dungeon is None or self._state is None:
            return
        level = self._dungeon.levels[self._state.current_level_idx]
        conn = next(
            (c for c in level.connections
             if (c.from_room == from_room and c.to_room == to_room)
             or (c.from_room == to_room and c.to_room == from_room)),
            None,
        )
        if conn is not None:
            loops = [lp for lp in level.loops
                     if from_room in lp.rooms or to_room in lp.rooms]
            loop_info = ", ".join(lp.id for lp in loops) or "none"
            note_part = f": {conn.note}" if conn.note else ""
            msg = (
                f"Connection: {conn.from_room} → {conn.to_room}"
                f" [{conn.type}]{note_part} (loops: {loop_info})"
            )
        else:
            msg = f"Connection: {from_room} → {to_room}"
        self._chat.add_message("dm", msg)
        _log.debug("Graph: selected connection %s → %s", from_room, to_room)

    def on_activate_loop(self, loop_id: str | None) -> None:
        if self._state is not None:
            self._state.active_loop_id = loop_id
        if loop_id is None:
            self._chat.add_message("system", "Loop overlay cleared.")
            return
        if self._dungeon is None or self._state is None:
            return
        level = self._dungeon.levels[self._state.current_level_idx]
        room_map = {r.id: r.name for r in level.rooms}
        loop = next((lp for lp in level.loops if lp.id == loop_id), None)
        if loop is None:
            return

        def resolve(rid: str) -> str:
            return room_map.get(rid, rid)

        path_a_names = ", ".join(resolve(r) for r in loop.path_a)
        path_b_names = ", ".join(resolve(r) for r in loop.path_b)
        msg = (
            f"Loop activated: {loop.pattern}\n"
            f"{loop.explanation}\n"
            f"Entry: {resolve(loop.entry)} → Goal: {resolve(loop.goal)}\n"
            f"Path A: {path_a_names}\n"
            f"Path B: {path_b_names}"
        )
        self._chat.add_message("system", msg)

    @staticmethod
    def _compute_rpg_toggle_rect(window_w: int, content_h: int) -> tuple[float, float, float, float]:
        # Sits immediately left of the pills cluster (Design/Campaign/Play).
        pills_left = window_w - PAD_MD - PILLS_CLUSTER_W
        btn_x = pills_left - PAD_MD - _BTN_RPG_W
        bar_mid = content_h + CHROME_TITLEBAR_HEIGHT / 2
        btn_y = bar_mid - _BTN_EDIT_H / 2
        return (float(btn_x), float(btn_y), float(_BTN_RPG_W), float(_BTN_EDIT_H))

    @staticmethod
    def _compute_edit_btn_rect(window_w: int, content_h: int) -> tuple[float, float, float, float]:
        # Sits immediately left of the RPG button.
        pills_left = window_w - PAD_MD - PILLS_CLUSTER_W
        rpg_x = pills_left - PAD_MD - _BTN_RPG_W
        btn_x = rpg_x - PAD_MD - _BTN_EDIT_W
        bar_mid = content_h + CHROME_TITLEBAR_HEIGHT / 2
        btn_y = bar_mid - _BTN_EDIT_H / 2
        return (float(btn_x), float(btn_y), float(_BTN_EDIT_W), float(_BTN_EDIT_H))
