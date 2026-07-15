"""PlayView — Play Mode view with ChatPanel, GridMap, and RPG side panels."""
from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import arcade
import arcade.gui

if TYPE_CHECKING:
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.command import PlayerCommand
    from dungeon_daddy.rpg.dice import Outcome
    from dungeon_daddy.rpg.models import (
        ActionResolution,
        RoomObject,
        WorldReaction,
    )
    from dungeon_daddy.rpg.obstacles import ObstacleRollResolution

from dungeon_daddy.data.models import Dungeon, SessionState
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent
from dungeon_daddy.llm.provider import LLMMessage
from dungeon_daddy.map.graph_renderer import GraphRenderer
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.play.actions import ActionOrchestrator
from dungeon_daddy.play.controller import PlaySessionController
from dungeon_daddy.play.dialogue import DialogueCoordinator, DialogueSession
from dungeon_daddy.play.memory_coordinator import MemoryCoordinator
from dungeon_daddy.play.narration import DMResult, NarrationCoordinator
from dungeon_daddy.play.navigation import NavigationCoordinator
from dungeon_daddy.play.session_context import PlaySessionContext
from dungeon_daddy.rpg.classifier import classify_intent
from dungeon_daddy.rpg.intent import PendingIntent
from dungeon_daddy.rpg.models import ActorState, ClockState
from dungeon_daddy.rpg.service import RpgService
from dungeon_daddy.ui.chrome import PILLS_CLUSTER_W, draw_title_bar, title_bar_mode_at
from dungeon_daddy.ui.panels.action_builder import InChatActionBuilder
from dungeon_daddy.ui.panels.character_sheet_panel import CharacterSheetPanel
from dungeon_daddy.ui.panels.chat_panel import ChatPanel
from dungeon_daddy.ui.panels.debug_controls import DebugControls
from dungeon_daddy.ui.panels.fallout_panel import FalloutPanel
from dungeon_daddy.ui.panels.map_panel import MapPanel
from dungeon_daddy.ui.panels.memory_inspector_panel import MemoryInspectorPanel
from dungeon_daddy.ui.panels.player_action_panel import PlayerActionPanel
from dungeon_daddy.ui.panels.scene_state_panel import SceneStatePanel
from dungeon_daddy.ui.panels.vna_action_panel import VnaActionPanel
from dungeon_daddy.ui.player_action_state import PlayerActionState
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

# DMResult + NarrationCoordinator moved to dungeon_daddy/play/narration.py
# (Phase 51.7, Slice 2); DMResult is re-exported above for the existing
# ``from dungeon_daddy.views.play_view import DMResult`` import sites.
# describe_spawned_loot moved to dungeon_daddy/play/actions.py (Slice 4) —
# import it from there.
# _PositionedRoom moved to dungeon_daddy/play/navigation.py (Slice 5).

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
        x, y = self._x, self._y
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
            self._debug.bundle_section_lines(),
            self._debug.lookup_section_lines(),
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
        # The play session's shared domain state (dungeon, session state, repo
        # handles, actor roster). `_dungeon`/`_state`/`_mem_repo`/
        # `_rpg_campaign_id` are thin properties delegating here, so the context
        # is the single source of truth (Phase 51.7, Slice 0).
        self._session = PlaySessionContext()
        self._repo = repo
        self._dm_agent = dm_agent
        self._rpg_service = rpg_service
        self._mem_repo = mem_repo
        self._dungeon = None
        self._state = None
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
        # DM-narration plumbing (queue / busy flag / history / worker thread)
        # lives in the lazily-materialized NarrationCoordinator (Slice 2); the
        # ``_result_queue``/``_llm_busy``/``_active_thread``/``_dm_history``
        # bridge properties below delegate to it.
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
        self._rpg_campaign_id = None
        self._action_state = PlayerActionState()
        self._chat.set_actor_switch_callback(self._on_actor_switch)
        # Phase 51 "Talk to the Dungeon": the voice agent reuses the DM agent's
        # injected provider (no new dependency). The open channel + persona state
        # (voice/knowledge, seed-authored, populated when a campaign is attached)
        # live on the ``DialogueCoordinator``, bridged below (Phase 51.7 Slice 3).
        self._dungeon_voice_agent = (
            DungeonVoiceAgent(dm_agent._provider) if dm_agent is not None else None
        )

    # ------------------------------------------------------------------
    # Session context bridge (Phase 51.7, Slice 0)
    #
    # These four attributes historically lived directly on the view and are
    # read/written from ~60 call sites (and set on `__new__`-constructed test
    # views). They now delegate to the shared ``PlaySessionContext`` so the
    # context is the single source of truth without churning every call site.
    # ``_session`` lazily materializes so ``PlayView.__new__`` test setups that
    # assign ``view._dungeon``/``view._state`` before anything else still work.
    # ------------------------------------------------------------------

    def _ensure_session(self) -> PlaySessionContext:
        ctx = self.__dict__.get("_session_ctx")
        if ctx is None:
            ctx = PlaySessionContext()
            self.__dict__["_session_ctx"] = ctx
        return ctx

    @property
    def _session(self) -> PlaySessionContext:
        return self._ensure_session()

    @_session.setter
    def _session(self, ctx: PlaySessionContext) -> None:
        self.__dict__["_session_ctx"] = ctx

    @property
    def _dungeon(self) -> Dungeon | None:
        return self._ensure_session().dungeon

    @_dungeon.setter
    def _dungeon(self, value: Dungeon | None) -> None:
        self._ensure_session().dungeon = value

    @property
    def _state(self) -> SessionState | None:
        return self._ensure_session().state

    @_state.setter
    def _state(self, value: SessionState | None) -> None:
        self._ensure_session().state = value

    @property
    def _mem_repo(self) -> MemoryRepository | None:
        return self._ensure_session().mem_repo

    @_mem_repo.setter
    def _mem_repo(self, value: MemoryRepository | None) -> None:
        self._ensure_session().mem_repo = value

    @property
    def _rpg_campaign_id(self) -> str | None:
        return self._ensure_session().campaign_id

    @_rpg_campaign_id.setter
    def _rpg_campaign_id(self, value: str | None) -> None:
        self._ensure_session().campaign_id = value

    # ------------------------------------------------------------------
    # Controller bridge (Phase 51.7, Slice 7)
    #
    # ``PlaySessionController`` is the composition root: it owns the five play
    # coordinators + the session-facade methods (bootstrap + the domain→panel
    # refresh fan-out), wiring every coordinator port against this view (its
    # ``PlayHost``) + the shared ``PlaySessionContext`` (owned by the Slice 0
    # session bridge above, passed in so both agree on one source of truth). It
    # is lazily materialized so ``PlayView.__new__`` test setups still work. The
    # coordinator + narration/dialogue state bridge properties below delegate to
    # it so the existing view tests and ``__new__`` factories read the single
    # source of truth without churn.
    # ------------------------------------------------------------------

    def _ensure_controller(self) -> PlaySessionController:
        controller = self.__dict__.get("_controller_obj")
        if controller is None:
            controller = PlaySessionController(self, session=self._session)
            self.__dict__["_controller_obj"] = controller
        return controller

    @property
    def _controller(self) -> PlaySessionController:
        return self._ensure_controller()

    @property
    def _narration(self) -> NarrationCoordinator:
        return self._ensure_controller().narration

    @property
    def _dm_history(self) -> list[LLMMessage]:
        return self._ensure_controller().narration.history

    @_dm_history.setter
    def _dm_history(self, value: list[LLMMessage]) -> None:
        self._ensure_controller().narration.history = value

    @property
    def _llm_busy(self) -> bool:
        return self._ensure_controller().narration.is_busy

    @_llm_busy.setter
    def _llm_busy(self, value: bool) -> None:
        self._ensure_controller().narration.is_busy = value

    @property
    def _result_queue(self) -> queue.Queue[DMResult]:
        return self._ensure_controller().narration.queue

    @_result_queue.setter
    def _result_queue(self, value: queue.Queue[DMResult]) -> None:
        self._ensure_controller().narration.queue = value

    @property
    def _active_thread(self) -> threading.Thread | None:
        return self._ensure_controller().narration.active_thread

    @_active_thread.setter
    def _active_thread(self, value: threading.Thread | None) -> None:
        self._ensure_controller().narration.active_thread = value

    # -- Coordinator + dialogue-state bridges (all owned by the controller) --
    #
    # The five coordinators live on ``PlaySessionController``; these properties
    # are the view's thin accessors. Dialogue's open-channel + persona state is
    # bridged (get/set) so the existing view tests and the
    # ``window.set_dungeon_persona`` API read the single source of truth.

    @property
    def _dialogue_coord(self) -> DialogueCoordinator:
        return self._ensure_controller().dialogue

    @property
    def _dialogue(self) -> DialogueSession | None:
        return self._ensure_controller().dialogue.session

    @_dialogue.setter
    def _dialogue(self, value: DialogueSession | None) -> None:
        self._ensure_controller().dialogue.session = value

    @property
    def _dungeon_voice(self) -> str | None:
        return self._ensure_controller().dialogue.dungeon_voice

    @_dungeon_voice.setter
    def _dungeon_voice(self, value: str | None) -> None:
        self._ensure_controller().dialogue.dungeon_voice = value

    @property
    def _dungeon_knowledge(self) -> list[str]:
        return self._ensure_controller().dialogue.dungeon_knowledge

    @_dungeon_knowledge.setter
    def _dungeon_knowledge(self, value: list[str]) -> None:
        self._ensure_controller().dialogue.dungeon_knowledge = value

    @property
    def _actions(self) -> ActionOrchestrator:
        return self._ensure_controller().actions

    @property
    def _navigation(self) -> NavigationCoordinator:
        return self._ensure_controller().navigation

    @property
    def _memory(self) -> MemoryCoordinator:
        return self._ensure_controller().memory

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
        self._narration.poll()

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
                        self._narration.build_context_bundle()
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
                self._narration.request_narration(f"We enter {room.name}.")
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
        self._controller.load_dungeon_transient(dungeon)

    def load_dungeon_session(self, dungeon: Dungeon) -> None:
        self._controller.load_dungeon_session(dungeon)

    def load_dungeon(self, dungeon: Dungeon) -> None:
        """Alias for load_dungeon_transient — kept until window.py callers are updated."""
        self.load_dungeon_transient(dungeon)

    def _save_session(self) -> None:
        self._controller.save_session()

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
        self._controller.set_rpg_context(mem_repo, campaign_id, portraits_dir)

    def _sync_debug_level_id(self) -> None:
        self._controller.sync_debug_level_id()

    def _load_player_actors(self) -> None:
        self._controller.load_player_actors()

    def _load_memory_entries(self) -> None:
        self._memory.load_memory_entries()

    # ------------------------------------------------------------------
    # Action delegators (Phase 51.7, Slice 4)
    #
    # The action logic lives in ``ActionOrchestrator``; these thin wrappers
    # are the view's input-routing surface (panel callbacks, chip clicks, and
    # the chat-send action path all target them).
    # ------------------------------------------------------------------

    def _run_chat_action(
        self,
        campaign_id: str,
        actor_id: str,
        action_key: str,
        intent: str,
    ) -> None:
        self._actions.run_chat_action(campaign_id, actor_id, action_key, intent)

    def _refresh_right_panel_from_actors(self, actor_id: str) -> None:
        self._controller.refresh_right_panel_from_actors(actor_id)

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
        self._controller.refresh_chat_mini_card()

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
        self._narration.request_narration(narration_text)

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
        self._actions.on_resolve_action(
            campaign_id, actor_id, intent, action_key,
            push_yourself, momentum_spend, dice_pool,
        )

    # ------------------------------------------------------------------
    # Dungeon navigation (Phase 48) — click-to-move
    # ------------------------------------------------------------------

    def _focus_party_room(self) -> None:
        self._navigation.focus_party_room()

    def _clear_dungeon_connection_lock(self, from_room: str, to_room: str) -> None:
        self._controller.clear_connection_lock(from_room, to_room)

    def _acting_actor(self) -> ActorState | None:
        return self._controller.acting_actor()

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
        return self._controller.room_world_flags(room_id)

    def _refresh_vna_panel(self) -> None:
        self._controller.refresh_vna_panel()

    def _push_things_here_overlay(self) -> None:
        """Push the current room contents + builder selection to the map overlay.

        Rebuilds the :class:`RoomThings` view-model from the retained room
        context (cheap; no set_context) and marks the builder's selected noun so
        its row shows the larger TEAL marker (Phase 50.6 §5.3). Safe to call
        before the first refresh.
        """
        from dungeon_daddy.rpg.action_options import room_things
        from dungeon_daddy.rpg.dungeon_channel import dungeon_channel_available

        map_panel = getattr(self, "_map", None)
        room_context = getattr(self, "_last_room_context", None)
        if map_panel is None or room_context is None:
            return
        actor_dict = getattr(self, "_last_actor_dict", {})
        selected = self._rpg_vna.selected_noun_option()
        selected_noun_id = selected.noun_id if selected is not None else None
        # Phase 51 Slice 9 (§4.6c): the "Speak to the Dungeon" entry affordance is
        # shown only when both gates pass — a resonance point with intimacy met.
        available, _ = dungeon_channel_available(
            room_context, self._dungeon_intimacy_clock()
        )
        map_panel.set_things_here(
            room_things(room_context, actor_dict),
            selected_noun_id=selected_noun_id,
            dungeon_channel_open=available,
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
        from dungeon_daddy.map.dungeon_layout.detail_panel_renderer import (
            DUNGEON_SPEAK_NOUN_ID,
        )
        from dungeon_daddy.rpg.action_options import (
            SOURCE_EXIT,
            SOURCE_LOOSE_ITEM,
            VERB_MOVE,
            VERB_PICK_UP,
        )

        # Phase 51 Slice 9: the synthetic "Speak to the Dungeon" row opens the
        # freeform dungeon channel instead of selecting a noun (D2b).
        if noun_id == DUNGEON_SPEAK_NOUN_ID:
            self._begin_dungeon_dialogue()
            return

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

    def _prepare_vna_exits(self, room_context: dict[str, Any], room_id: str) -> dict[str, Any]:
        return self._navigation.prepare_vna_exits(room_context, room_id)

    def _on_vna_submit(self, card: ActionCard) -> None:
        self._actions.on_vna_submit(card)

    # ------------------------------------------------------------------
    # Dialogue delegators (Phase 51.7, Slice 3)
    #
    # The dialogue logic lives in ``DialogueCoordinator``; these thin wrappers
    # are the view's input-routing surface (call sites, the window persona API,
    # and the narration ``on_dungeon_reply`` port all target them).
    # ------------------------------------------------------------------

    def _begin_dialogue(
        self,
        *,
        kind: Literal["dungeon", "npc"],
        room_id: str,
        target_id: str | None = None,
        opener: str | None = None,
    ) -> None:
        self._dialogue_coord.begin_dialogue(
            kind=kind, room_id=room_id, target_id=target_id, opener=opener
        )

    def _end_dialogue(self) -> None:
        self._dialogue_coord.end_dialogue()

    def _maybe_end_dialogue_on_room_change(self) -> None:
        self._dialogue_coord.maybe_end_on_room_change()

    def _on_dialogue_send(self, text: str) -> None:
        self._dialogue_coord.send_line(text)

    def _send_dungeon_line(self, text: str) -> None:
        self._dialogue_coord.send_dungeon_line(text)

    def _dungeon_intimacy_clock(self) -> ClockState | None:
        return self._dialogue_coord.dungeon_intimacy_clock()

    def _begin_dungeon_dialogue(self) -> None:
        self._dialogue_coord.begin_dungeon_dialogue()

    def set_dungeon_persona(self, voice: str | None, knowledge: list[str]) -> None:
        """Attach the seed-authored dungeon persona (P4 attach-time reader).

        ``window._attach_rpg_context`` resolves the campaign's persona Markdown
        refs and calls this so the voice agent reads them at play time.
        """
        self._dialogue_coord.set_persona(voice, knowledge)

    def _dungeon_agent_inputs(self, text: str) -> dict[str, Any]:
        return self._dialogue_coord.agent_inputs(text)

    def _apply_dungeon_reply(self, player_message: str, reply: str) -> None:
        self._dialogue_coord.apply_dungeon_reply(player_message, reply)

    def _apply_vna_command(self, command: PlayerCommand | None) -> bool:
        return self._actions.apply_vna_command(command)

    def _resolve_vna_roll(self, card: ActionCard, actor: ActorState) -> None:
        self._actions.resolve_vna_roll(card, actor)

    def _resolve_acted_object(self, noun_id: str) -> RoomObject | None:
        return self._actions.resolve_acted_object(noun_id)

    def _maybe_resolve_obstacle(
        self,
        card: ActionCard,
        actor: ActorState,
        outcome: Outcome,
        acted_object: RoomObject | None = None,
    ) -> ObstacleRollResolution | None:
        return self._actions.maybe_resolve_obstacle(
            card, actor, outcome, acted_object=acted_object
        )

    def _on_exit_move(self, exit_id: str, how: str, *, item_slug: str | None = None) -> None:
        self._navigation.on_exit_move(exit_id, how, item_slug=item_slug)

    def _run_proposal_pipeline(self, resolution: ActionResolution, campaign_id: str) -> None:
        self._actions.run_proposal_pipeline(resolution, campaign_id)

    def _apply_world_reaction(
        self, resolution: ActionResolution, acted_object: RoomObject | None = None
    ) -> WorldReaction | None:
        return self._actions.apply_world_reaction(resolution, acted_object)

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
        return self._memory.has_level_memory()

    def open_memory_overlay(self) -> None:
        loaded = self._memory.load_level_memory()
        if loaded is None:
            return
        level_id, content = loaded
        self._overlay_level_id = level_id
        self._overlay_content = content
        self._open_overlay_ui(content, level_id)

    def save_memory_overlay(self) -> None:
        if self._overlay_level_id is None or self._state is None:
            return
        input_widget = self._overlay_input
        content = input_widget.text if input_widget is not None else (self._overlay_content or "")
        self._memory.save_level_memory(self._overlay_level_id, content)
        self.close_memory_overlay()

    def close_memory_overlay(self) -> None:
        self._overlay_level_id = None
        self._overlay_content = None
        self._close_overlay_ui()

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
        # While a dialogue channel is open, a sent line is a dialogue line, not
        # a DM free-text query — route it to the channel (dispatched by kind).
        if getattr(self, "_dialogue", None) is not None:
            self._on_dialogue_send(text)
            return
        self._chat.add_message("gm", text)
        if text.strip() == "/clear":
            self._narration.clear_history()
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
            self._narration.request_narration(narration_text)
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
            actor = next((a for a in self._session.actors if a.actor_id == actor_id), None)
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
        self._narration.request_narration(text)

    def _handle_remember(self, event: str) -> None:
        self._memory.handle_remember(event)

    def _extract_remember(self, text: str) -> tuple[str | None, str]:
        return self._memory.extract_remember(text)

    def _auto_remember(self, event: str) -> None:
        self._memory.auto_remember(event)

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
        self._memory.persist_pending_commit()

    # ------------------------------------------------------------------
    # Memory state cache
    # ------------------------------------------------------------------

    def _refresh_memory_state(self) -> None:
        self._controller.refresh_memory_state()

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
        self._navigation.on_graph_room_select(room_id)

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
