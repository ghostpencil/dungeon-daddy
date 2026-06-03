"""AppConfig — paths, window defaults, and startup directory setup."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_data_path


@dataclass
class AppConfig:
    user_data_dir: Path = field(
        default_factory=lambda: user_data_path("DungeonDaddy", appauthor=False)
    )
    window_width: int = 1400
    window_height: int = 900
    window_title: str = "Dungeon Daddy"
    default_map_variant: str = "grid"

    @property
    def campaigns_dir(self) -> Path:
        return self.user_data_dir / "campaigns"

    def ensure_dirs(self) -> None:
        """Create user data directories if they do not exist."""
        self.campaigns_dir.mkdir(parents=True, exist_ok=True)
