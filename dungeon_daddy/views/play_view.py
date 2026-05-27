"""PlayView — Play Mode view with ChatPanel and GridMap."""
from __future__ import annotations

import logging
import queue
import re
import threading
from dataclasses import dataclass

import arcade
import arcade.gui

from dungeon_daddy.data.models import Dungeon, Level, Room, SessionState
from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.llm.provider import LLMMessage
from dungeon_daddy.map.grid_renderer import GridRenderer
from dungeon_daddy.ui.chrome import MenuBar, draw_title_bar
from dungeon_daddy.ui.panels.chat_panel import ChatPanel
from dungeon_daddy.ui.panels.map_panel import MapPanel
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

_log = logging.getLogger(__name__)

_CELL_PX = 48
_OVERLAY_TAB_H = 0   # tab bar is now an in-canvas overlay, not a reserved strip
_BTN_EDIT_W = 100
_BTN_EDIT_H = 24


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


class PlayView(arcade.View):
    """
    Play Mode view.

    Layout: ChatPanel (440 px) left, MapPanel (flex) right.
    Mouse clicks on the map highlight rooms and track visited state.
    """

    def __init__(self, repo: DungeonRepository, menu_bar: MenuBar, dm_agent: DungeonMasterAgent | None = None) -> None:
        super().__init__()
        self._repo = repo
        self._menu_bar = menu_bar
        self._dm_agent = dm_agent
        self._dungeon: Dungeon | None = None
        self._state: SessionState | None = None
        self._manager = arcade.gui.UIManager()
        self._renderer = GridRenderer(cell_px=_CELL_PX)
        self._chat = ChatPanel(self._on_chat_send, mode="play")
        self._map = MapPanel(
            self._on_level_change,
            renderer=self._renderer,
            on_variant_change=lambda variant: self.window.set_map_variant(variant),
            on_activate_loop=self.on_activate_loop,
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

    # ------------------------------------------------------------------
    # View lifecycle
    # ------------------------------------------------------------------

    def on_show_view(self) -> None:
        self.window.background_color = BG_0
        self._manager.enable()
        # Sync UIManager camera to current window size — it may have changed
        # while this view was inactive (e.g. window maximised in Design mode).
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
        if getattr(self, "_overlay_open", False):
            self._draw_overlay_backdrop()
        self._manager.draw()
        self._menu_bar.draw(self.window)  # last — dropdown renders above all chrome

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
        if self._menu_bar.handle_click(x, y, self.window):
            return
        if button != arcade.MOUSE_BUTTON_LEFT:
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
        self._map.set_dungeon_title(dungeon.meta.title)
        self._chat.set_mode_label("Play Mode")
        self._chat.add_message(
            "dm",
            f'Loaded "{dungeon.meta.title}" — Level 1: {level.name}. '
            "Click rooms on the map to explore.",
        )
        _log.info("PlayView: loaded dungeon=%s (test drive)", dungeon.meta.title)
        self._refresh_memory_state()

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
        _log.info("PlayView: loaded dungeon=%s (session)", dungeon.meta.title)
        self._refresh_memory_state()

    def load_dungeon(self, dungeon: Dungeon) -> None:
        """Alias for load_dungeon_transient — kept until window.py callers are updated."""
        self.load_dungeon_transient(dungeon)

    def _save_session(self) -> None:
        if not self._is_test_drive and self._state is not None:
            self._repo.save_session(self._state)

    # ------------------------------------------------------------------
    # Map variant switching
    # ------------------------------------------------------------------

    def set_map_renderer(self, renderer: GridRenderer) -> None:
        self._renderer = renderer
        self._map.set_renderer(renderer)

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

    def _spawn_dm_thread(self, room: Room, level: Level) -> None:
        if self._llm_busy:
            return
        if self._dm_agent is None:
            self._result_queue.put(DMResult(content="", error="DM agent unavailable — OPENAI_API_KEY not set."))
            return
        assert self._state is not None
        assert self._dungeon is not None
        memory = self._repo.load_room_memory(self._state.dungeon_id, level.id)
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
        new_idx = self._state.current_level_idx + delta
        if 0 <= new_idx < len(self._dungeon.levels):
            self._state.current_level_idx = new_idx
            self._state.current_room_id = None
            self._dm_history = []
            level = self._dungeon.levels[new_idx]
            self._map.load(level, self._state, len(self._dungeon.levels))
            self._chat.add_message("dm", f"Now on Level {new_idx + 1}: {level.name}.")
            self._refresh_memory_state()

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
        level = self._dungeon.levels[self._state.current_level_idx]
        room = None
        if self._state.current_room_id:
            room_map = {r.id: r for r in level.rooms}
            room = room_map.get(self._state.current_room_id)
        if room is None:
            self._chat.add_message("system", "Click a room first to give the DM context.")
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
        map_w = float(w - PANEL_CHAT_WIDTH)

        self._chat.setup(self._manager, 0.0, 0.0, float(PANEL_CHAT_WIDTH), float(content_h))
        self._map.setup(self._manager, map_x, 0.0, map_w, float(content_h))
        # Re-apply dungeon state so stepper buttons get correct enabled/disabled
        # state even when load_dungeon() was called before the UI was built.
        if self._dungeon is not None and self._state is not None:
            level = self._dungeon.levels[self._state.current_level_idx]
            self._map.load(level, self._state, len(self._dungeon.levels))
        self._edit_memory_rect = self._compute_edit_btn_rect(w, content_h)

    def _reposition_panels(self, w: int, h: int) -> None:
        if getattr(self, "_overlay_open", False):
            self._close_overlay_ui()
        content_h = h - CHROME_TOTAL_HEIGHT
        map_x = float(PANEL_CHAT_WIDTH)
        map_w = float(w - PANEL_CHAT_WIDTH)

        self._chat.resize(0.0, 0.0, float(PANEL_CHAT_WIDTH), float(content_h))
        # MapPanel teardown/rebuild on resize (simplest for Phase 6)
        self._map.teardown(self._manager)
        self._map.setup(self._manager, map_x, 0.0, map_w, float(content_h))
        if self._dungeon is not None and self._state is not None:
            level = self._dungeon.levels[self._state.current_level_idx]
            self._map.load(level, self._state, len(self._dungeon.levels))
        self._edit_memory_rect = self._compute_edit_btn_rect(w, content_h)

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
    def _compute_edit_btn_rect(window_w: int, content_h: int) -> tuple[float, float, float, float]:
        # Place button in the title bar, to the left of the PLAY MODE badge.
        # PLAY MODE badge: right edge at w - PAD_MD, width 100px.
        _PLAY_BADGE_W = 100
        btn_right = window_w - PAD_MD - _PLAY_BADGE_W - PAD_MD * 2
        btn_x = btn_right - _BTN_EDIT_W
        bar_mid = content_h + CHROME_TITLEBAR_HEIGHT / 2
        btn_y = bar_mid - _BTN_EDIT_H / 2
        return (float(btn_x), float(btn_y), float(_BTN_EDIT_W), float(_BTN_EDIT_H))
