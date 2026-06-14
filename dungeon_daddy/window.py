"""
DungeonDaddyWindow — the application window.

Owns the active view, the loaded Dungeon, and mode-switching logic.
Fonts are loaded once here before any view is shown.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk

    from dungeon_daddy.data.models import Dungeon
    from dungeon_daddy.llm.agents.design_agent import DesignAgent
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

import arcade

from dungeon_daddy.config import AppConfig
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.rpg.service import RpgService
from dungeon_daddy.ui.chrome import MenuAction, MenuBar

_MIGRATIONS_DIR = Path(__file__).parent / "data" / "migrations"


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace(",", "")

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


_DEFAULT_OPENAI_MODEL = "gpt-4o"


def _get_model_id() -> str:
    return os.environ.get("DUNGEON_DADDY_MODEL", _DEFAULT_OPENAI_MODEL)


# ---------------------------------------------------------------------------
# LLM agent factory
# ---------------------------------------------------------------------------

def _build_dm_agent(log_path: Path) -> DungeonMasterAgent | None:
    """Create the DM agent with OpenAI provider. Returns None on failure."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    _log.info("OPENAI_API_KEY present: %s (length=%d)", bool(api_key), len(api_key))
    try:
        from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
        from dungeon_daddy.llm.openai_provider import OpenAIProvider
        from dungeon_daddy.llm.prompts import load_prompt, prompt_hash
        from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter
        inner = OpenAIProvider(model=_get_model_id())
        ptext = load_prompt("dm_system")
        provider = ObservingProvider(
            inner, agent="dm", writer=TelemetryWriter(log_path),
            prompt_name="dm_system", prompt_hash=prompt_hash(ptext),
        )
        agent = DungeonMasterAgent(provider)
        _log.info("DM agent built successfully")
        return agent
    except Exception:
        _log.exception("Failed to build DM agent — Play Mode chat disabled")
        return None


def _build_agents(
    log_path: Path,
) -> tuple[DungeonWizardAgent | None, DungeonGeneratorAgent | None, DesignAgent | None]:
    """Create OpenAI provider + the three design agents. Returns (wizard, generator, design)."""
    try:
        from dungeon_daddy.data.models import LoopPatternCatalog
        from dungeon_daddy.llm.agents.design_agent import DesignAgent
        from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent
        from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent
        from dungeon_daddy.llm.openai_provider import OpenAIProvider
        from dungeon_daddy.llm.prompts import load_prompt, prompt_hash
        from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

        inner = OpenAIProvider(model=_get_model_id())
        writer = TelemetryWriter(log_path)
        catalog = LoopPatternCatalog.load_bundled()

        wiz_text = load_prompt("wizard_phase1_system")
        wizard = DungeonWizardAgent(
            ObservingProvider(
                inner, agent="wizard", writer=writer,
                prompt_name="wizard_phase1_system", prompt_hash=prompt_hash(wiz_text),
            ),
            catalog.patterns,
        )
        gen_text = load_prompt("generator_system")
        generator = DungeonGeneratorAgent(
            ObservingProvider(
                inner, agent="generator", writer=writer,
                prompt_name="generator_system", prompt_hash=prompt_hash(gen_text),
            )
        )
        des_text = load_prompt("design_system")
        design = DesignAgent(
            ObservingProvider(
                inner, agent="design", writer=writer,
                prompt_name="design_system", prompt_hash=prompt_hash(des_text),
            )
        )
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
        self._app_config = config
        self._mode: str = "design"

        # Repository — None-dir is fine for load_sample()
        self._repo = DungeonRepository(config.campaigns_dir)
        self._repo.migrate_legacy_layout()

        _load_fonts()

        # Import here to avoid circular dependency at module load
        from dungeon_daddy.views.campaign_view import CampaignView
        from dungeon_daddy.views.design_view import DesignView
        from dungeon_daddy.views.play_view import PlayView

        self._menu: dict[str, list[MenuAction]] = self._build_menu()
        self._menu_bar = MenuBar(self._menu)

        _llm_log = config.user_data_dir / "llm_calls.jsonl"
        wizard_agent, generator_agent, design_agent = _build_agents(_llm_log)
        dm_agent = _build_dm_agent(_llm_log)
        self._design_view = DesignView(
            self._repo, self._menu_bar,
            wizard_agent=wizard_agent,
            generator_agent=generator_agent,
            design_agent=design_agent,
        )
        rpg_service = RpgService()
        self._play_view = PlayView(self._repo, self._menu_bar, dm_agent=dm_agent, rpg_service=rpg_service)
        self._campaign_view = CampaignView(self._menu_bar)
        self.show_view(self._design_view)

    def _build_menu(self) -> dict[str, list[MenuAction]]:
        self._switch_to_play_action = MenuAction("Switch to Play", self._menu_launch_play)
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
                self._switch_to_play_action,
                MenuAction("Switch to Design", lambda: self.switch_mode("design")),
            ],
            "View": [
                MenuAction("Map: Graph", lambda: self.set_map_variant("graph")),
            ],
            "Window": [
                MenuAction("Minimise", self.minimise),
            ],
            "Help": [
                MenuAction("About", self.about),
            ],
        }

    def _menu_launch_play(self) -> None:
        dungeon = self._design_view._dungeon
        if dungeon and dungeon.levels and dungeon.meta.save_name:
            self.launch_play_session(dungeon)

    # ------------------------------------------------------------------
    # Menu actions
    # ------------------------------------------------------------------

    def _nyi(self) -> None:
        _log.info("Menu action not yet implemented")

    def new_dungeon(self) -> None:
        self._design_view.reset_to_wizard()
        self.switch_mode("design")

    def open_dungeon(
        self,
        _pick_fn: Callable[[], str | None] | None = None,
        _error_fn: Callable[[str], None] | None = None,
    ) -> None:
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
            self._attach_rpg_context(name)
            self.switch_mode("design")
        except FileNotFoundError:
            msg = f"No dungeon file found in '{name}'.\nThe folder exists but contains no dungeon data."
            _log.error("Failed to open dungeon '%s': dungeon.json missing", name)
            _error_fn(msg)
        except Exception as exc:
            msg = f"Could not open '{name}':\n{exc}"
            _log.error("Failed to open dungeon '%s': %s", name, exc)
            _error_fn(msg)

    def _make_tk_root(self) -> tk.Tk:
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
            initialdir=str(self._repo._dir or Path.home()),
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
            self._attach_rpg_context(None)  # sample dungeon has no campaign folder
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

        _CELL_PX = 48
        if variant != "graph":
            _log.warning("Unknown map variant: %s", variant)
            return
        self._play_view.set_map_renderer(GraphRenderer(cell_px=_CELL_PX))
        _log.info("Map variant: %s", variant)

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def switch_to_design(self) -> None:
        self._mode = "design"
        self.show_view(self._design_view)
        _log.info("Switched to design mode")

    def switch_to_campaign(self) -> None:
        self._mode = "campaign"
        self.show_view(self._campaign_view)
        _log.info("Switched to campaign mode")

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

    def _attach_rpg_context(self, save_name: str | None) -> None:
        """Open campaign.duckdb for save_name (if it exists) and wire it into PlayView."""
        from dungeon_daddy.memory.repository import MemoryRepository
        mem_repo = None
        campaign_id = None
        if save_name and self._repo._dir is not None:
            db_path = self._repo._dir / save_name / "campaign.duckdb"
            if db_path.exists():
                mem_repo = MemoryRepository(db_path)
                mem_repo.initialize_schema(_MIGRATIONS_DIR)
                campaign_id = f"campaign:{_slugify(save_name)}"
        self._play_view.set_rpg_context(mem_repo, campaign_id)

    def launch_test_drive(self, dungeon: Dungeon) -> None:
        self._play_view.load_dungeon(dungeon)
        self._attach_rpg_context(dungeon.meta.save_name)
        self.switch_to_play()

    def launch_play_session(self, dungeon: Dungeon) -> None:
        self._play_view.load_dungeon_session(dungeon)
        self._attach_rpg_context(dungeon.meta.save_name)
        self.switch_to_play()

    def set_switch_to_play_enabled(self, enabled: bool) -> None:
        self._switch_to_play_action.enabled = enabled

    def switch_mode(self, mode: str) -> None:
        if mode == "design":
            self.switch_to_design()
        elif mode == "campaign":
            self.switch_to_campaign()
        elif mode == "play":
            self.switch_to_play()
        else:
            _log.warning("Unknown mode: %s", mode)
