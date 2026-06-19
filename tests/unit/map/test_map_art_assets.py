"""Tests for dungeon_daddy.map.map_art_assets.MapArtAssets."""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dungeon_daddy.map.map_art_assets import MapArtAssets


# ---------------------------------------------------------------------------
# Cycle 1 — background loads when file exists
# ---------------------------------------------------------------------------

def test_background_loads_when_file_exists(tmp_path: Path) -> None:
    bg = tmp_path / "bg.png"
    bg.write_bytes(b"fake")
    fake_tex = MagicMock()
    with patch("dungeon_daddy.map.map_art_assets.arcade") as mock_arcade:
        mock_arcade.load_texture.return_value = fake_tex
        assets = MapArtAssets(background_path=bg, frame_dir=tmp_path)
    assert assets.background is fake_tex


# ---------------------------------------------------------------------------
# Cycle 2 — background is None when file missing, no crash, warning logged
# ---------------------------------------------------------------------------

def test_background_none_when_file_missing(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    missing = tmp_path / "no_bg.png"
    with patch("dungeon_daddy.map.map_art_assets.arcade"):
        with caplog.at_level(logging.WARNING, logger="dungeon_daddy.map.map_art_assets"):
            assets = MapArtAssets(background_path=missing, frame_dir=tmp_path)
    assert assets.background is None
    assert any("no_bg.png" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Cycle 3 — frame loads when file exists
# ---------------------------------------------------------------------------

def test_frame_loads_when_file_exists(tmp_path: Path) -> None:
    (tmp_path / "frame_default.png").write_bytes(b"fake")
    missing_bg = tmp_path / "no_bg.png"
    fake_tex = MagicMock()
    with patch("dungeon_daddy.map.map_art_assets.arcade") as mock_arcade:
        mock_arcade.load_texture.return_value = fake_tex
        assets = MapArtAssets(background_path=missing_bg, frame_dir=tmp_path)
    assert assets.frames["default"] is fake_tex


# ---------------------------------------------------------------------------
# Cycle 4 — frame is None when file missing, no crash, warning logged
# ---------------------------------------------------------------------------

def test_frame_none_when_file_missing(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    missing_bg = tmp_path / "no_bg.png"
    with patch("dungeon_daddy.map.map_art_assets.arcade"):
        with caplog.at_level(logging.WARNING, logger="dungeon_daddy.map.map_art_assets"):
            assets = MapArtAssets(background_path=missing_bg, frame_dir=tmp_path)
    assert assets.frames["default"] is None
    assert any("frame_default.png" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Cycle 5 — warning logged exactly once per missing file per instance
# ---------------------------------------------------------------------------

def test_warning_logged_exactly_once_per_missing_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing_bg = tmp_path / "no_bg.png"
    with patch("dungeon_daddy.map.map_art_assets.arcade"):
        with caplog.at_level(logging.WARNING, logger="dungeon_daddy.map.map_art_assets"):
            MapArtAssets(background_path=missing_bg, frame_dir=tmp_path)
    bg_warnings = [r for r in caplog.records if "no_bg.png" in r.message]
    assert len(bg_warnings) == 1


# ---------------------------------------------------------------------------
# Cycle 6 — party-marker icon loads when file exists
# ---------------------------------------------------------------------------

def test_party_marker_loads_when_file_exists(tmp_path: Path) -> None:
    icon = tmp_path / "position-marker.png"
    icon.write_bytes(b"fake")
    fake_tex = MagicMock()
    with patch("dungeon_daddy.map.map_art_assets.arcade") as mock_arcade:
        mock_arcade.load_texture.return_value = fake_tex
        assets = MapArtAssets(
            background_path=tmp_path / "no_bg.png", frame_dir=tmp_path, icon_path=icon
        )
    assert assets.party_marker is fake_tex


# ---------------------------------------------------------------------------
# Cycle 7 — party-marker is None when file missing (no crash)
# ---------------------------------------------------------------------------

def test_party_marker_none_when_file_missing(tmp_path: Path) -> None:
    with patch("dungeon_daddy.map.map_art_assets.arcade"):
        assets = MapArtAssets(
            background_path=tmp_path / "no_bg.png",
            frame_dir=tmp_path,
            icon_path=tmp_path / "missing.png",
        )
    assert assets.party_marker is None
