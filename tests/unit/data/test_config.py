"""Tests for dungeon_daddy/config.py — written before implementation."""

import pytest

# ---------------------------------------------------------------------------
# Behavior 1: AppConfig has correct default field values
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field,expected", [
    ("window_width", 1400),
    ("window_height", 900),
    ("window_title", "Dungeon Daddy"),
    ("default_map_variant", "grid"),
])
def test_appconfig_defaults(field, expected):
    from dungeon_daddy.config import AppConfig
    assert getattr(AppConfig(), field) == expected


# ---------------------------------------------------------------------------
# Behavior 2: AppConfig.campaigns_dir is user_data_dir / "campaigns"
# ---------------------------------------------------------------------------

def test_campaigns_dir_is_under_user_data_dir(tmp_path):
    from dungeon_daddy.config import AppConfig
    cfg = AppConfig(user_data_dir=tmp_path)
    assert cfg.campaigns_dir == tmp_path / "campaigns"


def test_campaigns_dir_is_a_property_not_a_field(tmp_path):
    import dataclasses

    from dungeon_daddy.config import AppConfig
    field_names = {f.name for f in dataclasses.fields(AppConfig)}
    assert "campaigns_dir" not in field_names


# ---------------------------------------------------------------------------
# Behavior 3: AppConfig.ensure_dirs() creates the campaigns directory
# ---------------------------------------------------------------------------

def test_ensure_dirs_creates_campaigns_dir(tmp_path):
    from dungeon_daddy.config import AppConfig
    cfg = AppConfig(user_data_dir=tmp_path)
    assert not cfg.campaigns_dir.exists()
    cfg.ensure_dirs()
    assert cfg.campaigns_dir.exists()
    assert cfg.campaigns_dir.is_dir()


# ---------------------------------------------------------------------------
# Behavior 4: AppConfig.ensure_dirs() is idempotent
# ---------------------------------------------------------------------------

def test_ensure_dirs_idempotent(tmp_path):
    from dungeon_daddy.config import AppConfig
    cfg = AppConfig(user_data_dir=tmp_path)
    cfg.ensure_dirs()
    cfg.ensure_dirs()   # must not raise
    assert cfg.campaigns_dir.is_dir()
