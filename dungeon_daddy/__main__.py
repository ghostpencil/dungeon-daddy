"""Entry point: python -m dungeon_daddy"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import arcade

from dungeon_daddy.config import AppConfig
from dungeon_daddy.window import DungeonDaddyWindow

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def _load_dotenv() -> None:
    """Load .env from the project root into os.environ (never overwrites existing vars)."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _add_file_logging(config: AppConfig) -> None:
    log_path = config.user_data_dir / "dungeon_daddy.log"
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger("dungeon_daddy").addHandler(fh)
    logging.getLogger("dungeon_daddy").setLevel(logging.DEBUG)


def main() -> None:
    _load_dotenv()
    config = AppConfig()
    config.ensure_dirs()
    _add_file_logging(config)
    DungeonDaddyWindow(config)
    arcade.run()


if __name__ == "__main__":
    main()
