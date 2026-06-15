"""Tests for AppConfig — Phase 45 Slice 0."""
from pathlib import Path

from dungeon_daddy.config import AppConfig


def test_dungeons_dir_under_user_data_dir(tmp_path: Path) -> None:
    cfg = AppConfig(user_data_dir=tmp_path)
    assert cfg.dungeons_dir == tmp_path / "dungeons"


def test_campaign_seeds_dir_under_user_data_dir(tmp_path: Path) -> None:
    cfg = AppConfig(user_data_dir=tmp_path)
    assert cfg.campaign_seeds_dir == tmp_path / "campaign_seeds"


def test_saves_dir_under_user_data_dir(tmp_path: Path) -> None:
    cfg = AppConfig(user_data_dir=tmp_path)
    assert cfg.saves_dir == tmp_path / "saves"


def test_ensure_dirs_creates_all_four_dirs(tmp_path: Path) -> None:
    cfg = AppConfig(user_data_dir=tmp_path)
    cfg.ensure_dirs()
    assert cfg.campaigns_dir.is_dir()
    assert cfg.dungeons_dir.is_dir()
    assert cfg.campaign_seeds_dir.is_dir()
    assert cfg.saves_dir.is_dir()


def test_ensure_dirs_is_idempotent(tmp_path: Path) -> None:
    cfg = AppConfig(user_data_dir=tmp_path)
    cfg.ensure_dirs()
    cfg.ensure_dirs()  # second call must not raise
