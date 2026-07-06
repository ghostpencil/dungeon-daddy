"""
DungeonDaddyWindow — the application window.

Owns the active view, the loaded Dungeon, and mode-switching logic.
Fonts are loaded once here before any view is shown.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk

    from dungeon_daddy.data.models import Dungeon
    from dungeon_daddy.llm.agents.design_agent import DesignAgent
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.llm.agents.generator_agent import DungeonGeneratorAgent
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent
    from dungeon_daddy.memory.repository import MemoryRepository

import arcade

from dungeon_daddy.config import AppConfig
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.rpg.service import RpgService

_MIGRATIONS_DIR = Path(__file__).parent / "data" / "migrations"


def _run_startup_migration(config: AppConfig) -> None:
    """Migrate legacy campaigns/ into the three new libraries (idempotent)."""
    if not config.campaigns_dir.exists():
        return
    from dungeon_daddy.data.repository import migrate_campaigns_to_libraries
    migrate_campaigns_to_libraries(
        campaigns_dir=config.campaigns_dir,
        dungeons_dir=config.dungeons_dir,
        seeds_dir=config.campaign_seeds_dir,
        saves_dir=config.saves_dir,
    )


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
        self._dungeon_repo = DungeonRepository(config.dungeons_dir)
        self._save_repo = DungeonRepository(config.saves_dir)
        _run_startup_migration(config)

        _load_fonts()

        # Import here to avoid circular dependency at module load
        from dungeon_daddy.campaign.seed_library import CampaignSeedLibrary
        from dungeon_daddy.views.campaign_view import CampaignView
        from dungeon_daddy.views.design_view import DesignView
        from dungeon_daddy.views.library_view import LibraryView
        from dungeon_daddy.views.play_view import PlayView

        self._seed_library = CampaignSeedLibrary(config.campaign_seeds_dir)

        _llm_log = config.user_data_dir / "llm_calls.jsonl"
        wizard_agent, generator_agent, design_agent = _build_agents(_llm_log)
        dm_agent = _build_dm_agent(_llm_log)
        self._design_view = DesignView(
            self._repo,
            wizard_agent=wizard_agent,
            generator_agent=generator_agent,
            design_agent=design_agent,
        )
        rpg_service = RpgService()
        self._play_view = PlayView(self._repo, dm_agent=dm_agent, rpg_service=rpg_service)
        self._campaign_view = CampaignView()
        self._library_view = LibraryView()
        self._library_view.set_sources(
            dungeon_repo=self._dungeon_repo,
            seed_library=self._seed_library,
            save_repo=self._save_repo,
        )
        self._mode = "library"
        self.show_view(self._library_view)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def new_dungeon(self) -> None:
        self._design_view.reset_to_wizard()
        self.switch_mode("design")

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

    def save_dungeon(self) -> None:
        dungeon = self._play_view._dungeon or self._design_view._dungeon
        state = self._play_view._state
        if dungeon is None:
            _log.info("Save: no dungeon loaded")
            return
        name = dungeon.meta.effective_name
        dungeon.meta.save_name = name
        try:
            self._dungeon_repo.save(dungeon, name)
            if state is not None:
                self._repo.save_session(state)
            from dungeon_daddy.llm.context_docs import generate_all_context_docs
            generate_all_context_docs(dungeon, name, self._dungeon_repo)
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

    def switch_to_library(self) -> None:
        self._mode = "library"
        self.show_view(self._library_view)
        _log.info("Switched to library mode")

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

    def _attach_rpg_context(
        self,
        save_name: str | None,
        repo_dir: Path | None = None,
    ) -> None:
        """Open campaign.duckdb for save_name (if it exists) and wire it into PlayView."""
        from dungeon_daddy.memory.repository import MemoryRepository
        base_dir = repo_dir if repo_dir is not None else self._repo._dir
        mem_repo = None
        campaign_id = None
        portraits_dir = None
        if save_name and base_dir is not None:
            campaign_dir = base_dir / save_name
            portraits_dir = campaign_dir / "assets" / "portraits"
            db_path = campaign_dir / "campaign.duckdb"
            if db_path.exists():
                mem_repo = MemoryRepository(db_path)
                mem_repo.initialize_schema(_MIGRATIONS_DIR)
                campaign_id = f"campaign:{_slugify(save_name)}"
                from dungeon_daddy.campaign.backfill import (
                    backfill_exits_if_empty,
                    refresh_exit_labels,
                )
                dungeon_json = campaign_dir / "dungeon.json"
                backfill_exits_if_empty(mem_repo, dungeon_json)
                refresh_exit_labels(mem_repo, dungeon_json)
        self._play_view.set_rpg_context(mem_repo, campaign_id, portraits_dir=portraits_dir)
        if mem_repo is not None and campaign_id is not None:
            voice, knowledge = self._read_dungeon_persona(mem_repo, campaign_id, campaign_dir)
            self._play_view.set_dungeon_persona(voice, knowledge)

    @staticmethod
    def _read_dungeon_persona(
        mem_repo: MemoryRepository, campaign_id: str, campaign_dir: Path
    ) -> tuple[str | None, list[str]]:
        """Resolve the campaign's seed persona Markdown refs into (voice, knowledge).

        The DuckDB ``campaigns`` row holds save-relative path references (P2/P3);
        read the docs via the P1 helpers. Missing refs/files → (None, []).
        """
        from dungeon_daddy.memory.dungeon_persona import (
            read_dungeon_knowledge,
            read_dungeon_voice,
        )

        campaign = mem_repo.get_campaign(campaign_id)
        if campaign is None:
            return None, []
        voice = None
        knowledge: list[str] = []
        voice_ref = campaign.get("dungeon_voice_path")
        if voice_ref:
            voice = read_dungeon_voice(campaign_dir / voice_ref)
        knowledge_ref = campaign.get("dungeon_knowledge_path")
        if knowledge_ref:
            knowledge = read_dungeon_knowledge(campaign_dir / knowledge_ref)
        return voice, knowledge

    def launch_test_drive(self, dungeon: Dungeon) -> None:
        self._play_view.load_dungeon(dungeon)
        self._attach_rpg_context(dungeon.meta.save_name)
        self.switch_to_play()

    def launch_play_session(self, dungeon: Dungeon) -> None:
        self._play_view.load_dungeon_session(dungeon)
        self._attach_rpg_context(dungeon.meta.save_name)
        self.switch_to_play()

    def launch_save_game(self, save_slug: str) -> None:
        dungeon = self._save_repo.load(save_slug)
        self._play_view.set_session_repo(self._save_repo)
        self._play_view.load_dungeon_session(dungeon)
        self._attach_rpg_context(save_slug, repo_dir=self._save_repo._dir)
        self.switch_mode("play")

    def switch_mode(self, mode: str) -> None:
        if mode == "library":
            self.switch_to_library()
        elif mode == "design":
            self.switch_to_design()
        elif mode == "campaign":
            self.switch_to_campaign()
        elif mode == "play":
            self.switch_to_play()
        else:
            _log.warning("Unknown mode: %s", mode)

    # ------------------------------------------------------------------
    # Library action methods
    # ------------------------------------------------------------------

    def open_in_designer(self, slug: str) -> None:
        """Load a dungeon from the library into Design mode."""
        try:
            dungeon = self._dungeon_repo.load(slug)
            if dungeon.meta.save_name is None:
                dungeon.meta.save_name = slug
            self._design_view.load_dungeon(dungeon)
            self._play_view.load_dungeon(dungeon)
            self._attach_rpg_context(slug)
            self.switch_mode("design")
        except Exception as exc:
            _log.error("open_in_designer failed for '%s': %s", slug, exc)

    def new_seed_from_dungeon(self, dungeon_slug: str) -> None:
        """Create a blank campaign seed attached to dungeon_slug and open in Campaign mode."""
        from dungeon_daddy.campaign.manifest import CampaignManifest
        manifest = CampaignManifest(
            slug="new-campaign",
            title="New Campaign",
            dungeon_slug=dungeon_slug,
        )
        self._campaign_view.set_seed_library(self._seed_library)
        self._campaign_view.load_manifest(manifest)
        self._campaign_view.is_dirty = True
        try:
            dungeon = self._dungeon_repo.load(dungeon_slug)
            self._campaign_view.set_dungeon(dungeon)
        except Exception:
            _log.warning("Could not load dungeon '%s' for campaign view", dungeon_slug)
        self.switch_mode("campaign")

    def edit_seed(self, seed_slug: str) -> None:
        """Load an existing campaign seed into Campaign mode for editing."""
        self._campaign_view.set_seed_library(self._seed_library)
        self._campaign_view.load_seed(seed_slug)
        dungeon_slug = self._campaign_view.attached_dungeon_slug
        if dungeon_slug:
            try:
                dungeon = self._dungeon_repo.load(dungeon_slug)
                self._campaign_view.set_dungeon(dungeon)
            except Exception:
                _log.warning("Could not load dungeon '%s' for campaign view", dungeon_slug)
        self.switch_mode("campaign")

    def publish_and_play(self, seed_slug: str) -> None:
        """Publish a campaign seed as a save game, then launch it in Play mode."""
        from dungeon_daddy.campaign.publish import publish_save
        manifest = self._seed_library.load(seed_slug)
        dungeons_dir = self._dungeon_repo._dir
        saves_dir = self._save_repo._dir
        assert dungeons_dir is not None and saves_dir is not None
        publish_save(
            manifest=manifest,
            dungeons_dir=dungeons_dir,
            saves_dir=saves_dir,
            save_slug=seed_slug,
            migrations_dir=_MIGRATIONS_DIR,
        )
        self.launch_save_game(seed_slug)

    def delete_save(self, save_slug: str) -> None:
        """Delete a save game directory from the saves library."""
        import shutil
        if self._save_repo._dir is None:
            return
        save_dir = self._save_repo._dir / save_slug
        if save_dir.exists():
            shutil.rmtree(save_dir)
            _log.info("Deleted save: %s", save_slug)

    def extract_seed(self, save_slug: str) -> None:
        """Extract a save game's campaign manifest back into the seed library."""
        from dungeon_daddy.campaign.manifest import CampaignManifest

        if self._save_repo._dir is None:
            return
        campaign_path = self._save_repo._dir / save_slug / "campaign.json"
        if not campaign_path.exists():
            self._show_info("Extract as Seed", f"No campaign data found for '{save_slug}'.")
            return
        manifest = CampaignManifest.model_validate_json(
            campaign_path.read_text(encoding="utf-8")
        )
        self._seed_library.save(manifest)
        _log.info("Extracted seed from save: %s", save_slug)
        self._show_info("Extract as Seed", f"'{save_slug}' saved as a campaign seed.")
