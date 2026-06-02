"""Safe asset loader for Graph map background and room frame textures."""
from __future__ import annotations

import logging
from pathlib import Path

import arcade

_ASSET_ROOT = Path(__file__).resolve().parent.parent / "assets" / "ui" / "map"
_BACKGROUND_PATH = _ASSET_ROOT / "dungeon_daddy_graph_background.png"
_FRAME_DIR = _ASSET_ROOT / "room_frames"
_FRAME_NAMES = ("default", "current", "hover", "locked", "memory", "danger")

_log = logging.getLogger(__name__)


def _safe_load(path: Path) -> arcade.Texture | None:
    if not path.exists():
        _log.warning("Map asset not found: %s", path)
        return None
    return arcade.load_texture(str(path))


class MapArtAssets:
    """Loads background and room frame textures once; falls back to None on missing files."""

    def __init__(
        self,
        background_path: Path | None = None,
        frame_dir: Path | None = None,
    ) -> None:
        bg = background_path if background_path is not None else _BACKGROUND_PATH
        fd = frame_dir if frame_dir is not None else _FRAME_DIR
        self.background: arcade.Texture | None = _safe_load(bg)
        self.frames: dict[str, arcade.Texture | None] = {
            name: _safe_load(fd / f"frame_{name}.png")
            for name in _FRAME_NAMES
        }
