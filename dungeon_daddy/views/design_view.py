"""
DesignView — the design/wizard/edit mode view for Dungeon Daddy.

Phase 5: skeleton with stub LLM (placeholder "…" response).
No real LLM calls are made here; that is wired in Phase 7.
"""
from __future__ import annotations

import logging
import os
import queue
import threading
from dataclasses import dataclass

import arcade
import arcade.gui

from dungeon_daddy.data.models import (
    DesignMode,
    Dungeon,
    DungeonMeta,
    validate_dungeon,
)
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.llm.agents.design_agent import DesignAgent
from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent
from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent
from dungeon_daddy.llm.provider import LLMMessage
from dungeon_daddy.ui.chrome import MenuBar, draw_title_bar
from dungeon_daddy.ui.panels.chat_panel import ChatPanel
from dungeon_daddy.ui.panels.dungeon_tree_panel import DungeonTreePanel
from dungeon_daddy.ui.panels.inspector_panel import InspectorPanel
from dungeon_daddy.ui.theme import (
    BG_0,
    BG_1,
    BG_2,
    BG_3,
    BG_HI,
    CHROME_TOTAL_HEIGHT,
    FONT_MONO,
    FONT_UI_MED,
    INK_1,
    INK_2,
    INK_4,
    LINE,
    LINE_HI,
    PAD_MD,
    PANEL_INSPECTOR_WIDTH,
    PANEL_TREE_WIDTH,
    TEAL,
    TEXT_BASE,
    TEXT_SM,
)


def _overlay_btn_style(variant: str) -> dict:
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

_log = logging.getLogger(__name__)


@dataclass
class LLMResult:
    content: str
    error: str | None = None
    result_type: str = "chat"  # "wizard" | "level" | "chat"


_WIZARD_GREETING = (
    "Hail, Game Master! I am your Dungeon Daddy. "
    "What manner of dungeon shall we craft today? "
    "Tell me its theme, mood, and the number of levels you desire."
)


class DesignView(arcade.View):
    """
    Design Mode view.

    Modes:
      "wizard"     — no dungeon yet; wizard collects brief from GM
      "generation" — levels are being generated (Phase 7)
      "edit"       — dungeon is loaded; DesignAgent refines it
    """

    def __init__(
        self,
        repo: DungeonRepository,
        menu_bar: MenuBar,
        wizard_agent: DungeonWizardAgent | None = None,
        generator_agent: DungeonGeneratorAgent | None = None,
        design_agent: DesignAgent | None = None,
    ) -> None:
        super().__init__()
        self._repo = repo
        self._menu_bar = menu_bar
        self._dungeon: Dungeon | None = None
        self._design_mode = DesignMode.WIZARD
        self._manager = arcade.gui.UIManager()
        self._chat = ChatPanel(self._on_chat_send)
        self._tree = DungeonTreePanel()
        self._inspector = InspectorPanel(on_activate_loop=self._on_loop_activated)
        self._inspector.set_on_context_doc_click(self._on_context_doc_click)
        self._ui_built = False
        self._result_queue: queue.Queue[LLMResult] = queue.Queue()
        self._llm_busy = False
        self._active_thread: threading.Thread | None = None
        self._wizard_agent = wizard_agent
        self._generator_agent = generator_agent
        self._design_agent = design_agent
        self._brief = None
        self._current_level_brief = None
        self._current_level = 1
        self._generation_retries = 0
        self._wizard_history: list[LLMMessage] = []
        self._design_history: list[LLMMessage] = []
        # Context doc overlay state
        self._overlay_open: bool = False
        self._overlay_doc_type: object = None
        self._overlay_dungeon_name: str | None = None
        self._overlay_level_id: int | None = None
        self._overlay_content: str | None = None
        self._overlay_widgets: list = []
        self._overlay_input = None
        # CD-5: overwrite-or-rename prompt state
        self._context_overwrite_confirmed: bool = False
        self._awaiting_name_choice: bool = False

    # ------------------------------------------------------------------
    # View lifecycle
    # ------------------------------------------------------------------

    def on_show_view(self) -> None:
        self.window.background_color = BG_0
        self._manager.enable()
        # Sync UIManager camera to current window size — it may have changed
        # while this view was inactive (e.g. window resized in Play mode).
        self._manager.on_resize(self.window.width, self.window.height)
        if not self._ui_built:
            self._build_ui()
            self._ui_built = True
            self._chat.add_message("dm", _WIZARD_GREETING)
        else:
            self._reposition_panels(self.window.width, self.window.height)

    def on_hide_view(self) -> None:
        self._manager.disable()
        if self._active_thread is not None:
            self._active_thread.join(timeout=3.0)

    def on_draw(self) -> None:
        self.clear()
        draw_title_bar(
            self.window,
            mode="design",
            on_mode=lambda m: self.window.switch_mode(m),  # type: ignore[attr-defined]
        )
        self._tree.draw()
        self._chat.draw()
        self._inspector.draw()
        if self._overlay_open:
            self._draw_overlay_backdrop()
        self._manager.draw()
        self._menu_bar.draw(self.window)  # last — dropdown renders above all chrome

    def on_update(self, delta_time: float) -> None:
        self._chat.update(delta_time)
        self._drain_queue()

    def on_resize(self, width: int, height: int) -> None:
        self._reposition_panels(width, height)

    def on_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> None:
        if self._inspector.on_mouse_scroll(x, y, int(scroll_y)):
            return
        self._chat.on_mouse_scroll(x, y, scroll_y)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        if self._overlay_open:
            return  # overlay is modal — UIManager handles save/cancel clicks
        if self._menu_bar.handle_click(x, y, self.window):
            return
        if self._tree.handle_click(x, y):
            return
        if self._chat.on_mouse_press(x, y):
            return
        if self._inspector.on_mouse_press(x, y, modifiers):
            return
        if self._inspector.hit_test_drive(x, y):
            self._launch_test_drive()
        elif self._inspector.hit_start_play(x, y):
            self._launch_start_play()

    def on_key_press(self, key: int, modifiers: int) -> None:
        if self._overlay_open and key == arcade.key.ESCAPE:
            self.close_context_doc_overlay()
            return
        self._chat.handle_key_press(key, modifiers)

    def _launch_test_drive(self) -> None:
        if self._dungeon and self._dungeon.levels:
            self.window.launch_test_drive(self._dungeon)  # type: ignore[attr-defined]

    def _launch_start_play(self) -> None:
        if self._dungeon and self._dungeon.levels and self._dungeon.meta.save_name:
            self.window.launch_play_session(self._dungeon)  # type: ignore[attr-defined]

    def _refresh_play_button_state(self) -> None:
        is_saved = bool(self._dungeon and self._dungeon.meta.save_name)
        has_session = False
        if is_saved:
            save_name = self._dungeon.meta.save_name  # type: ignore[union-attr]
            if self._repo.load_session(save_name) is not None:
                has_session = True
            elif self._dungeon and self._dungeon.levels:  # type: ignore[union-attr]
                has_session = any(
                    bool(self._repo.load_room_memory(save_name, level.id))
                    for level in self._dungeon.levels  # type: ignore[union-attr]
                )
        self._inspector.set_saved_state(is_saved, has_session)
        self.window.set_switch_to_play_enabled(is_saved)


    # ------------------------------------------------------------------
    # Dungeon loading (called by DungeonDaddyWindow)
    # ------------------------------------------------------------------

    def load_dungeon(self, dungeon: Dungeon) -> None:
        """Switch to edit mode and populate the tree with the loaded dungeon."""
        self._dungeon = dungeon
        self._design_mode = DesignMode.EDIT
        self._tree.set_dungeon(dungeon, expand_all=True)
        self._inspector.set_dungeon(dungeon)
        self._refresh_context_doc_statuses()
        self._refresh_play_button_state()
        self._chat.set_mode_label("Edit Mode")
        self._chat.add_message(
            "dm",
            f'Loaded "{dungeon.meta.title}". '
            "I am ready to help you refine it. What would you like to change?",
        )
        _log.info("DesignView: switched to edit mode, dungeon=%s", dungeon.meta.title)

    def reset_to_wizard(self) -> None:
        """Clear dungeon and return to wizard mode."""
        self._dungeon = None
        self._design_mode = DesignMode.WIZARD
        self._tree.set_dungeon(None)
        self._inspector.set_dungeon(None)
        self._chat.set_mode_label("Wizard Mode")
        self._chat.add_message("dm", _WIZARD_GREETING)

    # ------------------------------------------------------------------
    # Context doc overlay
    # ------------------------------------------------------------------

    def _on_context_doc_click(self, doc_type: object, level_id: int | None) -> None:
        if self._dungeon is None:
            return
        dungeon_name = self._dungeon.meta.title
        content = self._repo.load_context_doc(dungeon_name, doc_type, level_id)
        self.open_context_doc_overlay(doc_type, dungeon_name, level_id, content)

    def open_context_doc_overlay(
        self,
        doc_type: object,
        dungeon_name: str,
        level_id: int | None,
        content: str,
    ) -> None:
        self._overlay_doc_type = doc_type
        self._overlay_dungeon_name = dungeon_name
        self._overlay_level_id = level_id
        self._overlay_content = content
        self._overlay_open = True
        self._open_overlay_ui(content)

    def save_context_doc_overlay(self) -> None:
        input_widget = self._overlay_input
        content = input_widget.text if input_widget is not None else (self._overlay_content or "")
        self._repo.save_context_doc(
            self._overlay_dungeon_name,
            self._overlay_doc_type,
            content,
            self._overlay_level_id,
        )
        self._close_overlay_ui()
        self._refresh_context_doc_statuses()

    def close_context_doc_overlay(self) -> None:
        self._close_overlay_ui()

    def _overlay_card_rect(self) -> tuple[float, float, float, float]:
        w = self.window.width
        content_h = self.window.height - CHROME_TOTAL_HEIGHT
        map_area_x = float(PANEL_TREE_WIDTH)
        map_area_w = float(w - PANEL_TREE_WIDTH - PANEL_INSPECTOR_WIDTH)
        card_w = map_area_w * 0.85
        card_h = content_h * 0.80
        card_x = map_area_x + (map_area_w - card_w) / 2
        card_y = (content_h - card_h) / 2
        return card_x, card_y, card_w, card_h

    def _open_overlay_ui(self, content: str) -> None:
        if not self._ui_built:
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
            self.save_context_doc_overlay()

        @cancel_btn.event
        def on_click(event: arcade.gui.UIOnClickEvent) -> None:  # noqa: F811
            self.close_context_doc_overlay()

        self._manager.add(self._overlay_input)
        self._manager.add(save_btn)
        self._manager.add(cancel_btn)
        self._overlay_widgets = [self._overlay_input, save_btn, cancel_btn]

    def _draw_overlay_backdrop(self) -> None:
        w = self.window.width
        content_h = self.window.height - CHROME_TOTAL_HEIGHT
        map_area_x = float(PANEL_TREE_WIDTH)
        map_area_w = float(w - PANEL_TREE_WIDTH - PANEL_INSPECTOR_WIDTH)
        map_cx = map_area_x + map_area_w / 2
        arcade.draw_rect_filled(
            arcade.XYWH(map_cx, content_h / 2, map_area_w, float(content_h)),
            (*BG_0, 210),
        )
        card_x, card_y, card_w, card_h = self._overlay_card_rect()
        card_cx, card_cy = card_x + card_w / 2, card_y + card_h / 2
        arcade.draw_rect_filled(arcade.XYWH(card_cx, card_cy, card_w, card_h), BG_1)
        arcade.draw_rect_outline(arcade.XYWH(card_cx, card_cy, card_w, card_h), LINE, 1)

    def _close_overlay_ui(self) -> None:
        for w in self._overlay_widgets:
            try:
                self._manager.remove(w)
            except Exception:
                _log.warning("Failed to remove overlay widget %r", w, exc_info=True)
        self._overlay_widgets.clear()
        self._overlay_input = None
        self._overlay_open = False

    def _refresh_context_doc_statuses(self) -> None:
        from dungeon_daddy.data.models import ContextDocType
        from dungeon_daddy.ui.panels.inspector_panel import ContextDocStatus
        if self._dungeon is None:
            return
        dungeon_name = self._dungeon.meta.title
        level_id = self._dungeon.levels[0].id if self._dungeon.levels else None

        def _word_count(content: str) -> int | None:
            if not content:
                return None
            return len(content.split())

        statuses = []
        for label, doc_type, lvl_id in [
            ("Dungeon Setting", ContextDocType.SETTING, None),
            ("Party Doc", ContextDocType.PARTY, None),
            ("Level Design", ContextDocType.LEVEL_DESIGN, level_id),
        ]:
            if doc_type == ContextDocType.LEVEL_DESIGN and lvl_id is None:
                continue
            content = self._repo.load_context_doc(dungeon_name, doc_type, lvl_id)
            statuses.append(ContextDocStatus(
                label=label,
                doc_type=doc_type,
                level_id=lvl_id,
                word_count=_word_count(content),
            ))
        self._inspector.set_context_doc_statuses(statuses)
        all_loaded = len(statuses) == 3 and all(s.word_count for s in statuses)
        self._chat.set_context_loaded(all_loaded)

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def _on_chat_send(self, text: str) -> None:
        if self._llm_busy:
            return
        self._chat.add_message("gm", text)
        if not os.environ.get("OPENAI_API_KEY"):
            self._chat.add_message("dm", "⚠ OPENAI_API_KEY is not set.")
            return
        if self._awaiting_name_choice:
            self._awaiting_name_choice = False
            if text.strip().lower() == "overwrite":
                self._context_overwrite_confirmed = True
            else:
                self._dungeon.meta.save_name = text.strip()
            self._continue_to_generation()
            return
        self._wizard_history.append(LLMMessage(role="user", content=text))
        if self._design_mode in (DesignMode.WIZARD, DesignMode.LEVEL_WIZARD):
            phase = 2 if self._design_mode == DesignMode.LEVEL_WIZARD else 1
            self._llm_busy = True
            self._chat.set_busy(True)
            self._active_thread = threading.Thread(
                target=self._run_llm,
                kwargs={"history": list(self._wizard_history), "phase": phase},
                daemon=True,
            )
            self._active_thread.start()
        elif self._design_mode == DesignMode.EDIT:
            self._design_history.append(LLMMessage(role="user", content=text))
            self._llm_busy = True
            self._chat.set_busy(True)
            self._active_thread = threading.Thread(
                target=self._run_design_chat,
                kwargs={"history": list(self._design_history), "dungeon": self._dungeon},
                daemon=True,
            )
            self._active_thread.start()

    # ------------------------------------------------------------------
    # Queue drain / result dispatch
    # ------------------------------------------------------------------

    def _drain_queue(self) -> None:
        try:
            while True:
                result = self._result_queue.get_nowait()
                match result.result_type:
                    case "wizard":
                        self._handle_wizard_result(result)
                    case "level":
                        self._handle_level_result(result)
                    case "chat":
                        self._handle_chat_result(result)
        except queue.Empty:
            pass

    def _handle_chat_result(self, result: LLMResult) -> None:
        self._chat.set_busy(False)
        if result.error:
            self._chat.add_message("dm", f"⚠ {result.error}")
        else:
            self._chat.add_message("dm", result.content)
        if result.error:
            return
        self._design_history.append(LLMMessage(role="assistant", content=result.content))

    def _handle_wizard_result(self, result: LLMResult) -> None:
        self._chat.set_busy(False)
        if result.error:
            self._chat.add_message("dm", f"⚠ {result.error}")
            return
        self._chat.add_message("dm", result.content)
        self._wizard_history.append(LLMMessage(role="assistant", content=result.content))
        brief = self._wizard_agent.parse_brief(result.content)
        if brief is not None:
            self._start_generation(brief)
            return
        level_brief = self._wizard_agent.parse_level_brief(result.content)
        if level_brief is not None:
            self._current_level_brief = level_brief
            self._current_level = level_brief.level_number
            self._generation_retries = 0
            self._launch_generation(level_brief, errors=None)

    def _start_generation(self, brief: object) -> None:
        from dungeon_daddy.data.models import ContextDocType
        self._brief = brief
        self._dungeon = Dungeon(
            meta=DungeonMeta(
                title=brief.title,
                theme=brief.theme,
                setting=brief.setting,
                party=brief.party,
                quest=brief.quest,
            ),
            levels=[],
        )
        self._current_level = 1
        self._generation_retries = 0
        self._current_level_brief = None
        self._design_mode = DesignMode.LEVEL_WIZARD
        name = self._dungeon.meta.effective_name
        existing = self._repo.load_context_doc(name, ContextDocType.SETTING)
        if existing and not self._context_overwrite_confirmed:
            self._awaiting_name_choice = True
            self._chat.add_message(
                "dm",
                f'A dungeon named "{name}" already exists. '
                'Type "overwrite" to replace its docs, or enter a new save name.',
            )
            return
        self._continue_to_generation()

    def _continue_to_generation(self) -> None:
        self._write_setting_party_docs()
        self._wizard_history.append(LLMMessage(role="user", content="Let's design Level 1."))
        self._llm_busy = True
        self._chat.set_busy(True)
        self._active_thread = threading.Thread(
            target=self._run_llm,
            kwargs={"history": list(self._wizard_history), "phase": 2},
            daemon=True,
        )
        self._active_thread.start()

    def _write_setting_party_docs(self) -> None:
        from dungeon_daddy.data.models import ContextDocType
        from dungeon_daddy.llm.context_docs import generate_party_doc, generate_setting_doc
        name = self._dungeon.meta.effective_name
        self._repo.save_context_doc(name, ContextDocType.SETTING, generate_setting_doc(self._dungeon.meta))
        self._repo.save_context_doc(name, ContextDocType.PARTY, generate_party_doc(self._dungeon.meta))
        self._refresh_context_doc_statuses()

    def _write_level_design_doc(self, level: object) -> None:
        from dungeon_daddy.data.models import ContextDocType
        from dungeon_daddy.llm.context_docs import generate_level_design_doc
        name = self._dungeon.meta.effective_name
        self._repo.save_context_doc(name, ContextDocType.LEVEL_DESIGN, generate_level_design_doc(level), level_id=level.id)
        self._refresh_context_doc_statuses()

    def _launch_generation(
        self,
        level_brief: object,
        errors: list[str] | None,
    ) -> None:
        self._llm_busy = True
        self._chat.set_busy(True)
        self._active_thread = threading.Thread(
            target=self._run_generation,
            kwargs={"level_brief": level_brief, "errors": errors},
            daemon=True,
        )
        self._active_thread.start()

    def _handle_level_result(self, result: LLMResult) -> None:
        self._chat.set_busy(False)
        if result.error:
            self._chat.add_message(
                "dm", f"⚠ Level {self._current_level}: {result.error}"
            )
            return
        try:
            level = self._generator_agent.parse_level(result.content)
        except Exception as exc:
            if self._generation_retries < 3:
                self._generation_retries += 1
                self._chat.add_message("dm", f"Revising level {self._current_level}…")
                self._launch_generation(self._current_level_brief, [str(exc)])
                return
            self._chat.add_message(
                "dm", f"⚠ Parse error for level {self._current_level}: {exc}"
            )
            return
        temp = Dungeon(meta=self._dungeon.meta, levels=[level])
        validation = validate_dungeon(temp)
        self._tree.set_validation(validation)
        if not validation.is_valid:
            if self._generation_retries < 3:
                self._generation_retries += 1
                self._chat.add_message("dm", f"Revising level {self._current_level}…")
                self._launch_generation(self._current_level_brief, validation.errors)
                return
            self._chat.add_message(
                "dm",
                f"⚠ Could not fix level {self._current_level}: "
                + "; ".join(validation.errors),
            )
            return
        self._dungeon.levels.append(level)
        self._write_level_design_doc(level)
        self._tree.set_dungeon(self._dungeon)
        self._tree.expand_level(len(self._dungeon.levels) - 1)
        self._inspector.set_dungeon(self._dungeon)
        self._generation_retries = 0
        if self._current_level < self._brief.num_levels:
            self._chat.add_message(
                "dm",
                f"Level {self._current_level} ready! "
                "Test Drive it, or send a message when you're ready to design the next level.",
            )
        else:
            self._design_mode = DesignMode.EDIT
            self._chat.add_message("dm", "All levels generated! You can now refine your dungeon.")
            self._chat.set_mode_label("Edit Mode")

    # ------------------------------------------------------------------
    # Thread targets
    # ------------------------------------------------------------------

    def _run_llm(self, history: list[LLMMessage], phase: int = 1) -> None:
        try:
            response = self._wizard_agent.chat(history, phase=phase)
            self._result_queue.put(LLMResult(content=response, result_type="wizard"))
        except Exception as exc:
            self._result_queue.put(LLMResult(content="", error=str(exc), result_type="wizard"))
        finally:
            self._llm_busy = False

    def _run_generation(
        self,
        level_brief: object,
        errors: list[str] | None = None,
    ) -> None:
        try:
            response = self._generator_agent.generate_level(
                self._brief, level_brief, self._dungeon, errors
            )
            self._result_queue.put(LLMResult(content=response, result_type="level"))
        except Exception as exc:
            self._result_queue.put(LLMResult(content="", error=str(exc), result_type="level"))
        finally:
            self._llm_busy = False

    def _run_design_chat(self, history: list[LLMMessage], dungeon: Dungeon) -> None:
        try:
            response = self._design_agent.chat(history, dungeon)
            self._result_queue.put(LLMResult(content=response, result_type="chat"))
        except Exception as exc:
            self._result_queue.put(LLMResult(content="", error=str(exc), result_type="chat"))
        finally:
            self._llm_busy = False

    # ------------------------------------------------------------------
    # Loop activation
    # ------------------------------------------------------------------

    def _on_loop_activated(self, loop_id: str) -> None:
        loop = None
        if self._dungeon:
            loop = next(
                (lp for level in self._dungeon.levels for lp in level.loops if lp.id == loop_id),
                None,
            )
        self._tree.set_active_loop(loop)

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        w, h = self.window.width, self.window.height
        content_h = h - CHROME_TOTAL_HEIGHT
        chat_w = w - PANEL_TREE_WIDTH - PANEL_INSPECTOR_WIDTH

        self._tree.set_bounds(0.0, 0.0, float(PANEL_TREE_WIDTH), float(content_h))
        self._chat.setup(
            self._manager,
            float(PANEL_TREE_WIDTH), 0.0, float(chat_w), float(content_h),
        )
        self._inspector.setup(
            self._manager,
            float(w - PANEL_INSPECTOR_WIDTH), 0.0,
            float(PANEL_INSPECTOR_WIDTH), float(content_h),
        )

    def _reposition_panels(self, w: int, h: int) -> None:
        content_h = h - CHROME_TOTAL_HEIGHT
        chat_w = w - PANEL_TREE_WIDTH - PANEL_INSPECTOR_WIDTH

        self._tree.set_bounds(0.0, 0.0, float(PANEL_TREE_WIDTH), float(content_h))
        self._chat.resize(
            float(PANEL_TREE_WIDTH), 0.0, float(chat_w), float(content_h)
        )
        self._inspector.resize(
            float(w - PANEL_INSPECTOR_WIDTH), 0.0,
            float(PANEL_INSPECTOR_WIDTH), float(content_h),
        )
