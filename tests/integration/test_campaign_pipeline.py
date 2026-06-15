"""Integration tests — campaign pipeline: dungeon library → seed → publish → play."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest
from dungeon_daddy.campaign.publish import publish_save
from dungeon_daddy.campaign.seed_library import CampaignSeedLibrary
from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level, Room
from dungeon_daddy.data.repository import DungeonRepository

_MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "dungeon_daddy" / "data" / "migrations"


def _make_dungeon(save_name: str = "tomb-of-the-forgotten") -> Dungeon:
    room = Room(id="R1", num=1, name="Entry", x=0, y=0, w=2, h=2, type="hall", note="")
    level = Level(
        id=1, name="Crypt Level", summary=".", ecology="Undead",
        loop="lock_key", loops=[], width=10, height=5, entries=[],
        rooms=[room], connections=[],
    )
    return Dungeon(
        meta=DungeonMeta(
            title="Tomb of the Forgotten", theme="Undead", setting=".", party="4", quest=".",
            save_name=save_name,
        ),
        levels=[level],
    )


def _make_manifest(slug: str, dungeon_slug: str) -> CampaignManifest:
    """Minimal valid CampaignManifest (passes validator: has player_side actor)."""
    hero = ActorManifest(slug="hero", display_name="Hero", actor_type="pc")
    return CampaignManifest(
        slug=slug,
        title=slug.replace("-", " ").title(),
        dungeon_slug=dungeon_slug,
        world_actors=[hero],
        player_side=["hero"],
    )


def _setup_dirs(tmp_path: Path) -> tuple[Path, Path, Path]:
    dungeons_dir = tmp_path / "dungeons"
    seeds_dir = tmp_path / "campaign_seeds"
    saves_dir = tmp_path / "saves"
    for d in (dungeons_dir, seeds_dir, saves_dir):
        d.mkdir()
    return dungeons_dir, seeds_dir, saves_dir


# ---------------------------------------------------------------------------
# Behavior 1: full pipeline creates all 4 save files (tracer bullet)
# ---------------------------------------------------------------------------

def test_pipeline_publish_creates_all_save_files(tmp_path):
    """Full pipeline: save dungeon → save seed → publish → all 4 save files present."""
    dungeons_dir, seeds_dir, saves_dir = _setup_dirs(tmp_path)

    DungeonRepository(dungeons_dir).save(_make_dungeon(), "tomb-of-the-forgotten")

    manifest = _make_manifest("tomb-run", "tomb-of-the-forgotten")
    CampaignSeedLibrary(seeds_dir).save(manifest)

    publish_save(
        manifest=manifest,
        dungeons_dir=dungeons_dir,
        saves_dir=saves_dir,
        save_slug="tomb-run",
        migrations_dir=_MIGRATIONS_DIR,
    )

    save_dir = saves_dir / "tomb-run"
    assert (save_dir / "dungeon.json").exists()
    assert (save_dir / "campaign.json").exists()
    assert (save_dir / "campaign.duckdb").exists()
    assert (save_dir / "session.json").exists()


# ---------------------------------------------------------------------------
# Behavior 2: snapshot independence
# ---------------------------------------------------------------------------

def test_pipeline_published_save_is_independent_snapshot(tmp_path):
    """Editing the source dungeon after publish does not change the published save."""
    dungeons_dir, seeds_dir, saves_dir = _setup_dirs(tmp_path)

    dungeon = _make_dungeon()
    dungeon_repo = DungeonRepository(dungeons_dir)
    dungeon_repo.save(dungeon, "tomb-of-the-forgotten")

    manifest = _make_manifest("tomb-run", "tomb-of-the-forgotten")
    publish_save(
        manifest=manifest,
        dungeons_dir=dungeons_dir,
        saves_dir=saves_dir,
        save_slug="tomb-run",
        migrations_dir=_MIGRATIONS_DIR,
    )

    dungeon.meta.title = "COMPLETELY DIFFERENT"
    dungeon_repo.save(dungeon, "tomb-of-the-forgotten")

    save_dungeon = DungeonRepository(saves_dir).load("tomb-run")
    assert save_dungeon.meta.title == "Tomb of the Forgotten"


# ---------------------------------------------------------------------------
# Behavior 3: window can launch the published save game
# ---------------------------------------------------------------------------

def test_pipeline_window_launches_published_save(tmp_path):
    """Window.launch_save_game loads the published save's dungeon and switches to play."""
    from dungeon_daddy.window import DungeonDaddyWindow

    dungeons_dir, seeds_dir, saves_dir = _setup_dirs(tmp_path)

    DungeonRepository(dungeons_dir).save(_make_dungeon(), "tomb-of-the-forgotten")
    manifest = _make_manifest("tomb-run", "tomb-of-the-forgotten")
    publish_save(
        manifest=manifest,
        dungeons_dir=dungeons_dir,
        saves_dir=saves_dir,
        save_slug="tomb-run",
        migrations_dir=_MIGRATIONS_DIR,
    )

    win = DungeonDaddyWindow.__new__(DungeonDaddyWindow)
    win._repo = MagicMock()
    win._repo._dir = None
    win._save_repo = DungeonRepository(saves_dir)
    win._play_view = MagicMock()
    win.switch_mode = MagicMock()

    win.launch_save_game("tomb-run")

    win._play_view.load_dungeon_session.assert_called_once()
    loaded = win._play_view.load_dungeon_session.call_args[0][0]
    assert loaded.meta.title == "Tomb of the Forgotten"
    win.switch_mode.assert_called_once_with("play")


# ---------------------------------------------------------------------------
# Behavior 4: startup migration wiring
# ---------------------------------------------------------------------------

def test_run_startup_migration_moves_campaign_to_libraries(tmp_path):
    """_run_startup_migration copies campaigns/* into dungeons/, saves/, and seeds/."""
    from dungeon_daddy.config import AppConfig
    from dungeon_daddy.window import _run_startup_migration

    config = AppConfig(user_data_dir=tmp_path)
    config.ensure_dirs()

    campaign_dir = config.campaigns_dir / "the-crucible"
    campaign_dir.mkdir()
    DungeonRepository(config.campaigns_dir).save(_make_dungeon(), "the-crucible")
    manifest = _make_manifest("the-crucible", "the-crucible")
    (campaign_dir / "campaign.json").write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8",
    )

    _run_startup_migration(config)

    assert (config.dungeons_dir / "the-crucible" / "dungeon.json").exists()
    assert (config.saves_dir / "the-crucible" / "dungeon.json").exists()
    assert (config.campaign_seeds_dir / "the-crucible" / "campaign.json").exists()
    assert not (config.campaigns_dir / "the-crucible").exists()


def test_run_startup_migration_is_idempotent(tmp_path):
    """Running migration twice does not raise and result is unchanged."""
    from dungeon_daddy.config import AppConfig
    from dungeon_daddy.window import _run_startup_migration

    config = AppConfig(user_data_dir=tmp_path)
    config.ensure_dirs()

    campaign_dir = config.campaigns_dir / "keep-of-ruin"
    campaign_dir.mkdir()
    DungeonRepository(config.campaigns_dir).save(_make_dungeon(), "keep-of-ruin")

    _run_startup_migration(config)
    _run_startup_migration(config)  # second call must not raise

    assert (config.dungeons_dir / "keep-of-ruin" / "dungeon.json").exists()


def test_run_startup_migration_skips_when_campaigns_dir_absent(tmp_path):
    """Migration is a no-op when campaigns_dir does not exist yet."""
    from dungeon_daddy.config import AppConfig
    from dungeon_daddy.window import _run_startup_migration

    config = AppConfig(user_data_dir=tmp_path)
    # Do NOT call ensure_dirs — campaigns_dir absent

    _run_startup_migration(config)  # must not raise
