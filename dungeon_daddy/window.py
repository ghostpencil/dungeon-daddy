"""
DungeonDaddyWindow — the application window.

Owns the active view, the loaded Dungeon, and mode-switching logic.
Fonts are loaded once here before any view is shown.
"""
from __future__ import annotations

import logging
from pathlib import Path

import arcade

from dungeon_daddy.config import AppConfig
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.ui.chrome import MenuAction, MenuBar, draw_menu_bar, draw_title_bar

_log = logging.getLogger(__name__)

FONT_DIR = Path(__file__).parent / "assets" / "fonts"

_FONT_FILES = [
    "IMFellEnglish-Regular.ttf",
    "IMFellEnglish-Italic.ttf",
    "IMFellEnglishSC-Regular.ttf",
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Medium.ttf",
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-Bold.ttf",
]


def _load_fonts() -> None:
    for filename in _FONT_FILES:
        path = FONT_DIR / filename
        if path.exists():
            arcade.load_font(str(path))
            _log.debug("Loaded font: %s", filename)
        else:
            _log.warning("Font file not found (will use fallback): %s", path)


# ---------------------------------------------------------------------------
# LLM agent factory
# ---------------------------------------------------------------------------

def _build_dm_agent() -> object:
    """Create the DM agent with OpenAI provider. Returns None on failure."""
    import os
    api_key = os.environ.get("OPENAI_API_KEY", "")
    _log.info("OPENAI_API_KEY present: %s (length=%d)", bool(api_key), len(api_key))
    try:
        from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
        from dungeon_daddy.llm.openai_provider import OpenAIProvider
        agent = DungeonMasterAgent(OpenAIProvider())
        _log.info("DM agent built successfully")
        return agent
    except Exception:
        _log.exception("Failed to build DM agent — Play Mode chat disabled")
        return None


def _build_agents() -> tuple:
    """Create OpenAI provider + the three design agents. Returns (wizard, generator, design)."""
    try:
        from dungeon_daddy.data.models import LoopPatternCatalog
        from dungeon_daddy.llm.agents.design_agent import DesignAgent
        from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent
        from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent
        from dungeon_daddy.llm.openai_provider import OpenAIProvider

        provider = OpenAIProvider()
        catalog = LoopPatternCatalog.load_bundled()
        wizard = DungeonWizardAgent(provider, catalog.patterns)
        generator = DungeonGeneratorAgent(provider)
        design = DesignAgent(provider)
        return wizard, generator, design
    except Exception:
        _log.exception("Failed to build LLM agents — AI features disabled")
        return None, None, None


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class DungeonDaddyWindow(arcade.Window):
    """Top-level application window."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__(
            width=config.window_width,
            height=config.window_height,
            title=config.window_title,
            resizable=True,
        )
        self._config = config
        self._mode: str = "design"

        # Repository — None-dir is fine for load_sample()
        self._repo = DungeonRepository(config.dungeons_dir)
        self._repo.migrate_legacy_layout()

        _load_fonts()

        # Import here to avoid circular dependency at module load
        from dungeon_daddy.views.design_view import DesignView
        from dungeon_daddy.views.play_view import PlayView

        self._menu: dict[str, list[MenuAction]] = self._build_menu()
        self._menu_bar = MenuBar(self._menu)

        wizard_agent, generator_agent, design_agent = _build_agents()
        dm_agent = _build_dm_agent()
        self._design_view = DesignView(
            self._repo, self._menu_bar,
            wizard_agent=wizard_agent,
            generator_agent=generator_agent,
            design_agent=design_agent,
        )
        self._play_view = PlayView(self._repo, self._menu_bar, dm_agent=dm_agent)
        self.show_view(self._design_view)

    def _build_menu(self) -> dict[str, list[MenuAction]]:
        return {
            "File": [
                MenuAction("New", self.new_dungeon),
                MenuAction("Open...", self.open_dungeon),
                MenuAction("Demo Dungeon", self.open_sample_dungeon),
                MenuAction("Save", self.save_dungeon),
            ],
            "Edit": [
                MenuAction("Undo", self._nyi, implemented=False),
                MenuAction("Redo", self._nyi, implemented=False),
            ],
            "Dungeon": [
                MenuAction("Validate", self.validate),
                MenuAction("Generate Level", self._nyi, implemented=False),
            ],
            "Play": [
                MenuAction("Switch to Play", lambda: self.switch_mode("play")),
                MenuAction("Switch to Design", lambda: self.switch_mode("design")),
            ],
            "View": [
                MenuAction("Map: Grid", lambda: self.set_map_variant("grid")),
                MenuAction("Map: Tiles", lambda: self.set_map_variant("tiles")),
                MenuAction("Map: Graph", lambda: self.set_map_variant("graph")),
            ],
            "Window": [
                MenuAction("Minimise", self.minimise),
            ],
            "Help": [
                MenuAction("About", self.about),
            ],
        }

    # ------------------------------------------------------------------
    # Menu actions
    # ------------------------------------------------------------------

    def _nyi(self) -> None:
        _log.info("Menu action not yet implemented")

    def new_dungeon(self) -> None:
        self._design_view.reset_to_wizard()
        self.switch_mode("design")

    def open_dungeon(self, _pick_fn=None, _error_fn=None) -> None:
        """Open a saved dungeon chosen via file dialog (or injectable picker for tests)."""
        if _pick_fn is None:
            _pick_fn = self._pick_dungeon_via_dialog
        if _error_fn is None:
            _error_fn = self._show_error
        name = _pick_fn()
        if not name:
            return
        try:
            dungeon = self._repo.load(name)
            if dungeon.meta.save_name is None:
                dungeon.meta.save_name = name
            self._design_view.load_dungeon(dungeon)
            self._play_view.load_dungeon(dungeon)
            self.switch_mode("design")
        except FileNotFoundError:
            msg = f"No dungeon file found in '{name}'.\nThe folder exists but contains no dungeon data."
            _log.error("Failed to open dungeon '%s': dungeon.json missing", name)
            _error_fn(msg)
        except Exception as exc:
            msg = f"Could not open '{name}':\n{exc}"
            _log.error("Failed to open dungeon '%s': %s", name, exc)
            _error_fn(msg)

    def _make_tk_root(self) -> "tk.Tk":
        """Create a hidden Tk root owned by the Arcade window so dialogs stay in front of it."""
        import ctypes
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        try:
            tk_hwnd = root.winfo_id()
            ctypes.windll.user32.SetWindowLongPtrW(tk_hwnd, -8, self._hwnd)  # GWL_HWNDPARENT
        except Exception:
            pass
        return root

    def _show_error(self, message: str) -> None:
        from tkinter import messagebox
        root = self._make_tk_root()
        messagebox.showerror("Open Dungeon Failed", message)
        root.destroy()

    def _show_info(self, title: str, message: str) -> None:
        from tkinter import messagebox
        root = self._make_tk_root()
        messagebox.showinfo(title, message)
        root.destroy()

    def _ask_yes_no(self, title: str, message: str) -> bool:
        from tkinter import messagebox
        root = self._make_tk_root()
        answer = messagebox.askyesno(title, message)
        root.destroy()
        return answer

    def _pick_dungeon_via_dialog(self) -> str | None:
        from tkinter import filedialog
        root = self._make_tk_root()
        path = filedialog.askdirectory(
            title="Open Dungeon",
            initialdir=str(self._config.dungeons_dir),
        )
        root.destroy()
        if not path:
            return None
        return Path(path).name

    def open_sample_dungeon(self) -> None:
        try:
            sample_repo = DungeonRepository(None)
            dungeon = sample_repo.load_sample()
            self._design_view.load_dungeon(dungeon)
            self._play_view.load_dungeon(dungeon)
            self.switch_mode("design")
        except Exception as exc:
            _log.error("Failed to load sample dungeon: %s", exc)

    def save_dungeon(self) -> None:
        dungeon = self._play_view._dungeon or self._design_view._dungeon
        state = self._play_view._state
        if dungeon is None:
            _log.info("Save: no dungeon loaded")
            return
        name = dungeon.meta.effective_name
        dungeon.meta.save_name = name
        try:
            self._repo.save(dungeon, name)
            if state is not None:
                self._repo.save_session(state)
            from dungeon_daddy.llm.context_docs import generate_all_context_docs
            generate_all_context_docs(dungeon, name, self._repo)
            _log.info("Saved dungeon: %s", name)
        except Exception as exc:
            _log.error("Save failed: %s", exc)

    def validate(self) -> None:
        from dungeon_daddy.data.models import auto_fix_dungeon, validate_dungeon
        dungeon = self._play_view._dungeon or self._design_view._dungeon
        if dungeon is None:
            self._show_info("Validate Dungeon", "No dungeon loaded.")
            return
        result = validate_dungeon(dungeon)
        if result.is_valid:
            self._show_info("Validate Dungeon", "Dungeon is valid.")
            return
        fixable = sum(1 for level in dungeon.levels for loop in level.loops if not loop.explanation)
        fixable += sum(
            max(0, sum(1 for lp in level.loops if lp.type == "main") - 1)
            for level in dungeon.levels
        )
        if fixable > 0:
            confirmed = self._ask_yes_no(
                "Validate Dungeon",
                f"{len(result.errors)} error(s) found. {fixable} can be fixed automatically.\n\nApply automatic fixes now?",
            )
            if confirmed:
                fixes = auto_fix_dungeon(dungeon)
                result = validate_dungeon(dungeon)
                fixes_text = "\n".join(f"• {f}" for f in fixes)
                if result.is_valid:
                    self._show_info("Validate Dungeon", f"All errors fixed.\n\n{fixes_text}")
                else:
                    remaining = "\n".join(result.errors)
                    self._show_info(
                        "Validate Dungeon",
                        f"Applied {len(fixes)} fix(es):\n{fixes_text}\n\n{len(result.errors)} remaining error(s):\n\n{remaining}",
                    )
                return
        msg = "\n".join(result.errors)
        self._show_info("Validate Dungeon", f"{len(result.errors)} error(s) found:\n\n{msg}")

    def minimise(self) -> None:
        self.minimize()

    def about(self) -> None:
        self._show_info(
            "About Dungeon Daddy",
            "Dungeon Daddy\n\nAI-powered tabletop dungeon crawl manager.\nBuilt with Arcade 2D.",
        )

    def set_map_variant(self, variant: str) -> None:
        from dungeon_daddy.map.graph_renderer import GraphRenderer
        from dungeon_daddy.map.grid_renderer import GridRenderer
        from dungeon_daddy.map.tiles_renderer import TilesRenderer

        _CELL_PX = 48
        renderers = {
            "grid": GridRenderer(cell_px=_CELL_PX),
            "tiles": TilesRenderer(cell_px=_CELL_PX),
            "graph": GraphRenderer(cell_px=_CELL_PX),
        }
        renderer = renderers.get(variant)
        if renderer is None:
            _log.warning("Unknown map variant: %s", variant)
            return
        self._play_view.set_map_renderer(renderer)
        _log.info("Map variant: %s", variant)

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def switch_to_design(self) -> None:
        self._mode = "design"
        self.show_view(self._design_view)
        _log.info("Switched to design mode")

    def switch_to_play(self) -> None:
        self._mode = "play"
        self.show_view(self._play_view)
        _log.info("Switched to play mode")

    def on_key_press(self, key: int, modifiers: int) -> None:
        import arcade
        if key == arcade.key.O and modifiers & arcade.key.MOD_CTRL:
            self.open_dungeon()
        elif key == arcade.key.N and modifiers & arcade.key.MOD_CTRL:
            self.new_dungeon()

    def launch_test_drive(self, dungeon: object) -> None:
        self._play_view.load_dungeon(dungeon)
        self.switch_to_play()

    def launch_play_session(self, dungeon: object) -> None:
        self._play_view.load_dungeon_session(dungeon)
        self.switch_to_play()

    def switch_mode(self, mode: str) -> None:
        if mode == "design":
            self.switch_to_design()
        elif mode == "play":
            self.switch_to_play()
        else:
            _log.warning("Unknown mode: %s", mode)
